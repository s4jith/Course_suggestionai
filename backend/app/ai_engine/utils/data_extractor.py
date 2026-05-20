"""
Data Extractor – transforms raw MongoDB documents into a structured
`PlanContext` snapshot that both the rule engine and LLM prompt builder
can consume.

The key output is `PlanContext` — a flat, analytics-friendly view of a
lesson plan's current delivery state, derived from a `LessonPlanDocument`
and its associated `TopicProgressDocument` records.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models.lesson_plan import (
    LessonPlanDocument,
    TeachingMethod,
    TopicProgressDocument,
    TopicStatus,
    UnderstandingLevel,
)


# ---------------------------------------------------------------------------
# Understanding level → numeric score mapping
# ---------------------------------------------------------------------------

_UNDERSTANDING_SCORE: Dict[UnderstandingLevel, int] = {
    UnderstandingLevel.POOR: 0,
    UnderstandingLevel.AVERAGE: 1,
    UnderstandingLevel.GOOD: 2,
    UnderstandingLevel.EXCELLENT: 3,
}


# ---------------------------------------------------------------------------
# TopicSnapshot – flat view of a single topic
# ---------------------------------------------------------------------------

@dataclass
class TopicSnapshot:
    """Flat view of one topic and its current progress state."""

    lesson_plan_id: str
    chapter_id: str
    chapter_title: str
    topic_id: str
    topic_title: str
    topic_order: int
    planned_hours: float
    planned_date: Optional[datetime]

    # Progress fields — None means the topic has not been started yet
    progress_id: Optional[str] = None
    status: TopicStatus = TopicStatus.PENDING
    completion_percentage: float = 0.0
    teaching_method: Optional[TeachingMethod] = None
    actual_date: Optional[datetime] = None
    duration_taken: Optional[float] = None
    understanding_level: Optional[UnderstandingLevel] = None
    remarks: Optional[str] = None
    issues: Optional[str] = None

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def is_delayed(self) -> bool:
        """True if the planned date has passed but the topic is not completed."""
        if self.planned_date is None or self.status == TopicStatus.COMPLETED:
            return False
        now = datetime.now(tz=timezone.utc)
        planned = self.planned_date
        if planned.tzinfo is None:
            planned = planned.replace(tzinfo=timezone.utc)
        return planned < now

    @property
    def days_overdue(self) -> int:
        """Positive integer: how many days past the planned date this topic is."""
        if not self.is_delayed or self.planned_date is None:
            return 0
        now = datetime.now(tz=timezone.utc)
        planned = self.planned_date
        if planned.tzinfo is None:
            planned = planned.replace(tzinfo=timezone.utc)
        return max(0, (now - planned).days)

    @property
    def understanding_score(self) -> int:
        """
        Numeric score for comprehension level.
        Returns -1 if no understanding level has been recorded.
        """
        if self.understanding_level is None:
            return -1
        return _UNDERSTANDING_SCORE.get(self.understanding_level, -1)


# ---------------------------------------------------------------------------
# PlanContext – full analytical context for one lesson plan
# ---------------------------------------------------------------------------

@dataclass
class PlanContext:
    """
    Complete analytical context for one lesson plan.

    Consumed by the rule engine, risk analyzer, and prompt templates.
    Built by `build_plan_context()` — never constructed manually.
    """

    plan_id: str
    subject_name: str
    teacher_id: str
    academic_year: str
    semester: int
    total_topics: int
    total_planned_hours: float

    topics: List[TopicSnapshot] = field(default_factory=list)

    # --- Derived aggregates ---
    completed_topics: int = 0
    in_progress_topics: int = 0
    pending_topics: int = 0
    skipped_topics: int = 0
    delayed_topics: int = 0
    total_hours_delivered: float = 0.0
    completion_percentage: float = 0.0
    avg_understanding_score: float = 0.0

    # method str → average understanding score (0–3)
    method_effectiveness: Dict[str, float] = field(default_factory=dict)
    # method str → number of uses
    method_usage_count: Dict[str, int] = field(default_factory=dict)

    # First and last recorded teaching activity
    first_activity_date: Optional[datetime] = None
    last_activity_date: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Builder function
# ---------------------------------------------------------------------------

def build_plan_context(
    plan: LessonPlanDocument,
    subject_name: str,
    progress_records: List[TopicProgressDocument],
) -> PlanContext:
    """
    Build a `PlanContext` from a lesson plan document and its progress records.

    Args:
        plan:             The LessonPlanDocument from MongoDB.
        subject_name:     Human-readable subject name.
        progress_records: All TopicProgressDocument records for this plan.

    Returns:
        A fully populated PlanContext ready for rule / LLM processing.
    """
    # Index progress records by topic_id for O(1) lookup
    progress_index: Dict[str, TopicProgressDocument] = {
        p.topic_id: p for p in progress_records
    }

    topic_snapshots: List[TopicSnapshot] = []
    total_planned_hours = 0.0

    for chapter in plan.chapters:
        for topic in chapter.topics:
            p = progress_index.get(topic.topic_id)

            snap = TopicSnapshot(
                lesson_plan_id=str(plan.id),
                chapter_id=chapter.chapter_id,
                chapter_title=chapter.title,
                topic_id=topic.topic_id,
                topic_title=topic.title,
                topic_order=topic.order,
                planned_hours=topic.planned_hours,
                planned_date=topic.planned_date,
            )

            if p is not None:
                snap.progress_id = str(p.id)
                snap.status = p.status
                snap.completion_percentage = p.completion_percentage
                snap.teaching_method = p.teaching_method
                snap.actual_date = p.actual_date
                snap.duration_taken = p.duration_taken
                snap.understanding_level = p.student_understanding_level
                snap.remarks = p.remarks
                snap.issues = p.issues

            total_planned_hours += topic.planned_hours
            topic_snapshots.append(snap)

    # --- Status counts ---
    completed = [t for t in topic_snapshots if t.status == TopicStatus.COMPLETED]
    in_progress = [t for t in topic_snapshots if t.status == TopicStatus.IN_PROGRESS]
    pending = [t for t in topic_snapshots if t.status == TopicStatus.PENDING]
    skipped = [t for t in topic_snapshots if t.status == TopicStatus.SKIPPED]
    delayed = [t for t in topic_snapshots if t.is_delayed]

    # --- Hours delivered ---
    hours_delivered = sum(
        t.duration_taken for t in topic_snapshots if t.duration_taken is not None
    )

    # --- Average understanding ---
    scored = [t.understanding_score for t in topic_snapshots if t.understanding_score >= 0]
    avg_understanding = sum(scored) / len(scored) if scored else 0.0

    # --- Method effectiveness ---
    method_scores: Dict[str, List[int]] = {}
    method_counts: Dict[str, int] = {}
    for t in topic_snapshots:
        if t.teaching_method is not None and t.understanding_score >= 0:
            key = (
                t.teaching_method.value
                if hasattr(t.teaching_method, "value")
                else str(t.teaching_method)
            )
            method_scores.setdefault(key, []).append(t.understanding_score)
            method_counts[key] = method_counts.get(key, 0) + 1

    method_effectiveness = {
        k: round(sum(v) / len(v), 3) for k, v in method_scores.items()
    }

    # --- Activity date range ---
    activity_dates = [t.actual_date for t in topic_snapshots if t.actual_date is not None]
    first_activity = min(activity_dates) if activity_dates else None
    last_activity = max(activity_dates) if activity_dates else None

    total = len(topic_snapshots) or 1
    completion_pct = round(len(completed) / total * 100, 1)

    return PlanContext(
        plan_id=str(plan.id),
        subject_name=subject_name,
        teacher_id=plan.teacher_id,
        academic_year=plan.academic_year,
        semester=plan.semester,
        total_topics=len(topic_snapshots),
        total_planned_hours=total_planned_hours,
        topics=topic_snapshots,
        completed_topics=len(completed),
        in_progress_topics=len(in_progress),
        pending_topics=len(pending),
        skipped_topics=len(skipped),
        delayed_topics=len(delayed),
        total_hours_delivered=hours_delivered,
        completion_percentage=completion_pct,
        avg_understanding_score=round(avg_understanding, 3),
        method_effectiveness=method_effectiveness,
        method_usage_count=method_counts,
        first_activity_date=first_activity,
        last_activity_date=last_activity,
    )

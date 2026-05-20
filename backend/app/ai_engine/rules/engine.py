"""
Rule-Based Recommendation Engine.

Implements deterministic logic to generate actionable recommendations
from a `PlanContext` without any LLM involvement.

All logic is expressed as pure functions so it is:
  - Testable in isolation (no I/O side effects)
  - Fast (no network calls)
  - Auditable (each recommendation carries an explanation)
  - Used as fallback when Ollama is unavailable

Algorithms:
  - Syllabus delay detection     : planned_date < today and status != COMPLETED
  - Pending topic prioritization : weighted scoring (delay + understanding + order)
  - Teaching method recommendation: historical effectiveness + keyword heuristic
  - Completion forecasting       : linear velocity extrapolation
  - Timetable generation         : greedy day-by-day slot assignment
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.ai_engine.utils.data_extractor import PlanContext, TopicSnapshot
from app.models.lesson_plan import TeachingMethod, TopicStatus, UnderstandingLevel


# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

# Priority score weights
_DELAY_WEIGHT = 40.0        # bonus score per overdue day
_UNDERSTANDING_WEIGHT = 20.0  # penalty / boost for low-comprehension topics
_ORDER_WEIGHT = 1.0          # ordering influence (earlier topic = slightly higher)

# Method suitability: keyword fragments found in topic titles → method name
_METHOD_SUITABILITY: Dict[str, List[str]] = {
    "theoretical":  ["introduction", "concept", "theory", "overview", "principle", "basics", "fundamentals"],
    "ppt":          ["overview", "summary", "revision", "review", "concepts", "unit"],
    "practical":    ["implementation", "exercise", "coding", "practice", "hands-on", "program"],
    "lab":          ["experiment", "simulation", "algorithm", "coding", "lab", "sorting", "searching"],
    "seminar":      ["discussion", "case", "analysis", "advanced", "research", "seminar"],
    "assignment":   ["assignment", "homework", "self-study", "project", "problem"],
    "discussion":   ["scenario", "group", "debate", "problem-solving"],
    "case_study":   ["real-world", "application", "case study", "industry"],
    "video_based":  ["visual", "demo", "animation", "diagram", "video"],
}


# ---------------------------------------------------------------------------
# 1. Topic prioritization — what to teach next
# ---------------------------------------------------------------------------

def _priority_score(topic: TopicSnapshot) -> float:
    """
    Compute a priority score for a single pending topic.

    Higher score = higher priority.

    Components:
      + days_overdue * 40      — heavily favors catching up on delayed topics
      + 20                     — if last understanding level was poor/average
      + 1/topic_order          — earlier topics in the chapter get slight boost
    """
    score = topic.days_overdue * _DELAY_WEIGHT
    if topic.understanding_level in (UnderstandingLevel.POOR, UnderstandingLevel.AVERAGE):
        score += _UNDERSTANDING_WEIGHT
    score += (1.0 / max(topic.topic_order, 1)) * _ORDER_WEIGHT
    return round(score, 2)


def get_next_topic(ctx: PlanContext) -> Optional[TopicSnapshot]:
    """
    Select the highest-priority topic from pending / in-progress topics.

    Returns None if no pending topics remain.
    """
    candidates = [
        t for t in ctx.topics
        if t.status in (TopicStatus.PENDING, TopicStatus.IN_PROGRESS)
    ]
    if not candidates:
        return None
    return max(candidates, key=_priority_score)


def get_priority_score(topic: TopicSnapshot) -> float:
    """Public wrapper: return the priority score for a topic snapshot."""
    return _priority_score(topic)


def get_all_pending_prioritized(ctx: PlanContext) -> List[TopicSnapshot]:
    """Return all pending/in-progress topics sorted by priority (highest first)."""
    candidates = [
        t for t in ctx.topics
        if t.status in (TopicStatus.PENDING, TopicStatus.IN_PROGRESS)
    ]
    return sorted(candidates, key=_priority_score, reverse=True)


# ---------------------------------------------------------------------------
# 2. Teaching method recommendation
# ---------------------------------------------------------------------------

def recommend_teaching_method(
    topic_title: str,
    ctx: PlanContext,
) -> TeachingMethod:
    """
    Recommend the most effective teaching method for a topic.

    Strategy:
      1. If the teacher has a method with avg understanding >= 2.0 (good),
         prefer that method based on historical performance.
      2. Fall back to keyword matching against _METHOD_SUITABILITY map.
      3. Default to THEORETICAL if no match found.
    """
    # Strategy 1: best historical method
    if ctx.method_effectiveness:
        best_method_key = max(ctx.method_effectiveness, key=ctx.method_effectiveness.get)
        if ctx.method_effectiveness[best_method_key] >= 2.0:
            try:
                return TeachingMethod(best_method_key)
            except ValueError:
                pass  # unknown method string — fall through

    # Strategy 2: keyword heuristic on topic title
    title_lower = topic_title.lower()
    for method_name, keywords in _METHOD_SUITABILITY.items():
        if any(kw in title_lower for kw in keywords):
            try:
                return TeachingMethod(method_name)
            except ValueError:
                continue

    return TeachingMethod.THEORETICAL


# ---------------------------------------------------------------------------
# 3. Weak area detection — topics needing revision
# ---------------------------------------------------------------------------

def get_weak_areas(ctx: PlanContext) -> List[TopicSnapshot]:
    """
    Return completed topics where student understanding was poor or average.

    Sorted worst-first so the most urgent revision need appears at position 0.
    """
    weak = [
        t for t in ctx.topics
        if t.status == TopicStatus.COMPLETED
        and t.understanding_level in (UnderstandingLevel.POOR, UnderstandingLevel.AVERAGE)
    ]
    return sorted(weak, key=lambda t: t.understanding_score)


# ---------------------------------------------------------------------------
# 4. Delayed topic detection
# ---------------------------------------------------------------------------

def get_delayed_topics(ctx: PlanContext) -> List[TopicSnapshot]:
    """Return all topics that are past their planned date and not completed."""
    return sorted(
        [t for t in ctx.topics if t.is_delayed],
        key=lambda t: t.days_overdue,
        reverse=True,
    )


# ---------------------------------------------------------------------------
# 5. Completion forecasting
# ---------------------------------------------------------------------------

def forecast_completion(ctx: PlanContext) -> dict:
    """
    Forecast the lesson plan completion date based on current teaching velocity.

    Velocity = completed_topics / weeks_active

    Returns a dict:
        topics_per_week          : float
        weeks_remaining          : float | None
        estimated_completion_date: ISO date string | None
        is_on_track              : bool
    """
    if (
        ctx.completed_topics == 0
        or ctx.first_activity_date is None
    ):
        return {
            "topics_per_week": 0.0,
            "weeks_remaining": None,
            "estimated_completion_date": None,
            "is_on_track": False,
        }

    now = datetime.now(tz=timezone.utc)
    first = ctx.first_activity_date
    if first.tzinfo is None:
        first = first.replace(tzinfo=timezone.utc)

    weeks_active = max((now - first).days / 7.0, 0.5)
    topics_per_week = ctx.completed_topics / weeks_active

    remaining = ctx.pending_topics + ctx.in_progress_topics

    if topics_per_week > 0:
        weeks_remaining = remaining / topics_per_week
        estimated_date = now + timedelta(weeks=weeks_remaining)
        estimated_date_str = estimated_date.strftime("%Y-%m-%d")
    else:
        weeks_remaining = None
        estimated_date_str = None

    # "On track" = no delayed topics and projected to finish within 20 weeks
    is_on_track = (
        ctx.delayed_topics == 0
        and weeks_remaining is not None
        and weeks_remaining <= 20
    )

    return {
        "topics_per_week": round(topics_per_week, 2),
        "weeks_remaining": round(weeks_remaining, 1) if weeks_remaining is not None else None,
        "estimated_completion_date": estimated_date_str,
        "is_on_track": is_on_track,
    }


# ---------------------------------------------------------------------------
# 6. Smart timetable generation
# ---------------------------------------------------------------------------

def suggest_timetable(
    ctx: PlanContext,
    teaching_days_per_week: int = 5,
) -> List[dict]:
    """
    Generate a day-by-day timetable for all remaining pending topics.

    Prioritization:
      - Overdue topics first (by days_overdue descending)
      - Then by chapter/topic order

    Args:
        ctx:                    PlanContext for the lesson plan.
        teaching_days_per_week: Number of working teaching days per week (1-7).

    Returns:
        List of slot dicts, each with:
            slot, date, day_of_week, topic_id, topic_title,
            chapter_title, suggested_hours, teaching_method
    """
    pending = [
        t for t in ctx.topics
        if t.status in (TopicStatus.PENDING, TopicStatus.IN_PROGRESS)
    ]

    # Sort: overdue first, then by chapter/topic order
    pending.sort(key=lambda t: (-t.days_overdue, t.topic_order))

    schedule: List[dict] = []
    current_date = datetime.now(tz=timezone.utc).replace(
        hour=9, minute=0, second=0, microsecond=0
    )

    # Advance to the next weekday within the teaching window
    max_weekday = teaching_days_per_week - 1  # 0=Mon … 4=Fri for 5-day week
    while current_date.weekday() > max_weekday:
        current_date += timedelta(days=1)

    for idx, topic in enumerate(pending[:20]):  # cap at 20 for readability
        method = recommend_teaching_method(topic.topic_title, ctx)
        schedule.append({
            "slot": idx + 1,
            "date": current_date.strftime("%Y-%m-%d"),
            "day_of_week": current_date.strftime("%A"),
            "topic_id": topic.topic_id,
            "topic_title": topic.topic_title,
            "chapter_title": topic.chapter_title,
            "suggested_hours": topic.planned_hours,
            "teaching_method": method.value,
        })

        # Advance to the next teaching day
        current_date += timedelta(days=1)
        while current_date.weekday() > max_weekday:
            current_date += timedelta(days=1)

    return schedule

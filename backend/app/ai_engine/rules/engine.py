
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.ai_engine.utils.data_extractor import PlanContext, TopicSnapshot
from app.models.lesson_plan import TeachingMethod, TopicStatus, UnderstandingLevel

_DELAY_WEIGHT = 40.0
_UNDERSTANDING_WEIGHT = 20.0
_ORDER_WEIGHT = 1.0

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

def _priority_score(topic: TopicSnapshot) -> float:
    score = topic.days_overdue * _DELAY_WEIGHT
    if topic.understanding_level in (UnderstandingLevel.POOR, UnderstandingLevel.AVERAGE):
        score += _UNDERSTANDING_WEIGHT
    score += (1.0 / max(topic.topic_order, 1)) * _ORDER_WEIGHT
    return round(score, 2)

def get_next_topic(ctx: PlanContext) -> Optional[TopicSnapshot]:
    candidates = [
        t for t in ctx.topics
        if t.status in (TopicStatus.PENDING, TopicStatus.IN_PROGRESS)
    ]
    if not candidates:
        return None
    return max(candidates, key=_priority_score)

def get_priority_score(topic: TopicSnapshot) -> float:
    return _priority_score(topic)

def get_all_pending_prioritized(ctx: PlanContext) -> List[TopicSnapshot]:
    candidates = [
        t for t in ctx.topics
        if t.status in (TopicStatus.PENDING, TopicStatus.IN_PROGRESS)
    ]
    return sorted(candidates, key=_priority_score, reverse=True)

def recommend_teaching_method(
    topic_title: str,
    ctx: PlanContext,
) -> TeachingMethod:
    if ctx.method_effectiveness:
        best_method_key = max(ctx.method_effectiveness, key=ctx.method_effectiveness.get)
        if ctx.method_effectiveness[best_method_key] >= 2.0:
            try:
                return TeachingMethod(best_method_key)
            except ValueError:
                pass

    title_lower = topic_title.lower()
    for method_name, keywords in _METHOD_SUITABILITY.items():
        if any(kw in title_lower for kw in keywords):
            try:
                return TeachingMethod(method_name)
            except ValueError:
                continue

    return TeachingMethod.THEORETICAL

def get_weak_areas(ctx: PlanContext) -> List[TopicSnapshot]:
    weak = [
        t for t in ctx.topics
        if t.status == TopicStatus.COMPLETED
        and t.understanding_level in (UnderstandingLevel.POOR, UnderstandingLevel.AVERAGE)
    ]
    return sorted(weak, key=lambda t: t.understanding_score)

def get_delayed_topics(ctx: PlanContext) -> List[TopicSnapshot]:
    return sorted(
        [t for t in ctx.topics if t.is_delayed],
        key=lambda t: t.days_overdue,
        reverse=True,
    )

def forecast_completion(ctx: PlanContext) -> dict:
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

def suggest_timetable(
    ctx: PlanContext,
    teaching_days_per_week: int = 5,
) -> List[dict]:
    pending = [
        t for t in ctx.topics
        if t.status in (TopicStatus.PENDING, TopicStatus.IN_PROGRESS)
    ]

    pending.sort(key=lambda t: (-t.days_overdue, t.topic_order))

    schedule: List[dict] = []
    current_date = datetime.now(tz=timezone.utc).replace(
        hour=9, minute=0, second=0, microsecond=0
    )

    max_weekday = teaching_days_per_week - 1
    while current_date.weekday() > max_weekday:
        current_date += timedelta(days=1)

    for idx, topic in enumerate(pending[:20]):
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

        current_date += timedelta(days=1)
        while current_date.weekday() > max_weekday:
            current_date += timedelta(days=1)

    return schedule

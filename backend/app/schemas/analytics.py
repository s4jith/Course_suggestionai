"""
Analytics Pydantic schemas – request/response models for the Analytics module.

All schemas are read-only (response-only) aggregated views derived from
`lesson_plans`, `topic_progress`, and `subjects` collections.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ===========================================================================
# Overview / KPI
# ===========================================================================

class OverviewKPI(BaseModel):
    """Top-level KPIs for the analytics dashboard."""

    total_lesson_plans: int = 0
    active_lesson_plans: int = 0
    total_topics: int = 0
    completed_topics: int = 0
    in_progress_topics: int = 0
    pending_topics: int = 0
    skipped_topics: int = 0
    overall_completion_pct: float = 0.0
    total_hours_planned: float = 0.0
    total_hours_delivered: float = 0.0
    hours_delivery_pct: float = 0.0
    at_risk_plans: int = 0
    delayed_topics: int = 0
    avg_understanding_score: Optional[float] = None


# ===========================================================================
# Syllabus completion
# ===========================================================================

class SyllabusCompletionItem(BaseModel):
    """Per-lesson-plan completion percentage for bar/line charts."""

    lesson_plan_id: str
    title: str
    subject_name: str
    academic_year: str
    semester: int
    status: str
    total_topics: int
    completed_topics: int
    completion_pct: float
    hours_planned: float
    hours_delivered: float
    risk_score: float


class SyllabusCompletionResponse(BaseModel):
    items: List[SyllabusCompletionItem]
    avg_completion_pct: float


# ===========================================================================
# Faculty progress
# ===========================================================================

class FacultyAnalyticsItem(BaseModel):
    """Per-faculty aggregated progress."""

    teacher_id: str
    teacher_name: str
    email: str
    total_topics_assigned: int
    completed_topics: int
    in_progress_topics: int
    pending_topics: int
    skipped_topics: int
    completion_pct: float
    total_hours_delivered: float
    avg_understanding_score: Optional[float] = None
    lesson_plans_count: int


class FacultyAnalyticsResponse(BaseModel):
    items: List[FacultyAnalyticsItem]


# ===========================================================================
# Subject progress
# ===========================================================================

class SubjectAnalyticsItem(BaseModel):
    """Per-subject aggregated completion metrics."""

    subject_id: str
    subject_name: str
    subject_code: str
    department: str
    semester: int
    total_lesson_plans: int
    avg_completion_pct: float
    total_topics: int
    completed_topics: int
    pending_topics: int
    total_hours_planned: float
    total_hours_delivered: float


class SubjectAnalyticsResponse(BaseModel):
    items: List[SubjectAnalyticsItem]


# ===========================================================================
# Delayed topics
# ===========================================================================

class DelayedTopicItem(BaseModel):
    """Topic that is past its planned date but not completed."""

    topic_id: str
    topic_title: str
    chapter_title: str
    lesson_plan_id: str
    lesson_plan_title: str
    subject_name: str
    teacher_name: str
    planned_date: Optional[datetime]
    days_overdue: int
    status: str
    completion_pct: float


class DelayedTopicsResponse(BaseModel):
    items: List[DelayedTopicItem]
    total_delayed: int


# ===========================================================================
# Risk scores
# ===========================================================================

class RiskScoreItem(BaseModel):
    """Per-lesson-plan completion risk assessment."""

    lesson_plan_id: str
    title: str
    subject_name: str
    teacher_name: str
    risk_score: float                # 0-100, higher = more risk
    risk_level: str                  # low | medium | high | critical
    completion_pct: float
    pending_topics: int
    delayed_topics: int
    days_remaining: Optional[int]
    recommendation: str


class RiskScoresResponse(BaseModel):
    items: List[RiskScoreItem]
    avg_risk_score: float


# ===========================================================================
# Teaching method effectiveness
# ===========================================================================

class TeachingMethodItem(BaseModel):
    """Effectiveness metrics per teaching method."""

    method: str
    label: str
    total_uses: int
    avg_completion_pct: float
    avg_understanding_score: float
    excellent_count: int
    good_count: int
    average_count: int
    poor_count: int
    avg_duration_hours: Optional[float]
    effectiveness_score: float       # 0-100 composite score


class TeachingMethodResponse(BaseModel):
    items: List[TeachingMethodItem]


# ===========================================================================
# Student understanding analytics
# ===========================================================================

class UnderstandingBreakdown(BaseModel):
    """Distribution of student understanding levels."""

    excellent: int = 0
    good: int = 0
    average: int = 0
    poor: int = 0
    total: int = 0
    excellent_pct: float = 0.0
    good_pct: float = 0.0
    average_pct: float = 0.0
    poor_pct: float = 0.0
    avg_score: float = 0.0           # Weighted 1-4 score


class UnderstandingBySubject(BaseModel):
    subject_name: str
    subject_code: str
    breakdown: UnderstandingBreakdown


class UnderstandingAnalyticsResponse(BaseModel):
    overall: UnderstandingBreakdown
    by_subject: List[UnderstandingBySubject]


# ===========================================================================
# Completion trend (time-series)
# ===========================================================================

class CompletionTrendPoint(BaseModel):
    """Daily completion count for line chart."""

    date: str                        # ISO date string YYYY-MM-DD
    completed_count: int
    cumulative_completed: int


class CompletionTrendResponse(BaseModel):
    points: List[CompletionTrendPoint]
    period_days: int


# ===========================================================================
# Heatmap data
# ===========================================================================

class HeatmapCell(BaseModel):
    """Single cell in the topic-completion calendar heatmap."""

    date: str                        # YYYY-MM-DD
    count: int                       # topics completed that day
    intensity: int                   # 0-4 bucketed level for colour


class HeatmapResponse(BaseModel):
    cells: List[HeatmapCell]
    max_count: int


# ===========================================================================
# Analytics filters (query params schema)
# ===========================================================================

class AnalyticsFilters(BaseModel):
    """Shared filters applied to most analytics queries."""

    academic_year: Optional[str] = None
    semester: Optional[int] = Field(None, ge=1, le=10)
    department: Optional[str] = None
    teacher_id: Optional[str] = None
    subject_id: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None

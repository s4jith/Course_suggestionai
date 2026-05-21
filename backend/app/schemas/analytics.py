
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

class OverviewKPI(BaseModel):

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

class SyllabusCompletionItem(BaseModel):

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

class FacultyAnalyticsItem(BaseModel):

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

class SubjectAnalyticsItem(BaseModel):

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

class DelayedTopicItem(BaseModel):

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

class RiskScoreItem(BaseModel):

    lesson_plan_id: str
    title: str
    subject_name: str
    teacher_name: str
    risk_score: float
    risk_level: str
    completion_pct: float
    pending_topics: int
    delayed_topics: int
    days_remaining: Optional[int]
    recommendation: str

class RiskScoresResponse(BaseModel):
    items: List[RiskScoreItem]
    avg_risk_score: float

class TeachingMethodItem(BaseModel):

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
    effectiveness_score: float

class TeachingMethodResponse(BaseModel):
    items: List[TeachingMethodItem]

class UnderstandingBreakdown(BaseModel):

    excellent: int = 0
    good: int = 0
    average: int = 0
    poor: int = 0
    total: int = 0
    excellent_pct: float = 0.0
    good_pct: float = 0.0
    average_pct: float = 0.0
    poor_pct: float = 0.0
    avg_score: float = 0.0

class UnderstandingBySubject(BaseModel):
    subject_name: str
    subject_code: str
    breakdown: UnderstandingBreakdown

class UnderstandingAnalyticsResponse(BaseModel):
    overall: UnderstandingBreakdown
    by_subject: List[UnderstandingBySubject]

class CompletionTrendPoint(BaseModel):

    date: str
    completed_count: int
    cumulative_completed: int

class CompletionTrendResponse(BaseModel):
    points: List[CompletionTrendPoint]
    period_days: int

class HeatmapCell(BaseModel):

    date: str
    count: int
    intensity: int

class HeatmapResponse(BaseModel):
    cells: List[HeatmapCell]
    max_count: int

class AnalyticsFilters(BaseModel):

    academic_year: Optional[str] = None
    semester: Optional[int] = Field(None, ge=1, le=10)
    department: Optional[str] = None
    teacher_id: Optional[str] = None
    subject_id: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None

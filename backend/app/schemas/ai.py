
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.lesson_plan import TeachingMethod, UnderstandingLevel

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class NextTopicRecommendation(BaseModel):

    topic_id: str
    topic_title: str
    chapter_title: str
    priority_score: float = Field(..., description="Higher = more urgent")
    reason: str = Field(..., description="Explanation of why this topic is prioritized")
    suggested_method: TeachingMethod
    estimated_hours: float
    is_delayed: bool = Field(..., description="True if the topic is past its planned date")
    days_overdue: int = Field(..., description="0 if not overdue, else days since planned date")

    class Config:
        from_attributes = True

class WeakAreaAlert(BaseModel):

    topic_id: str
    topic_title: str
    chapter_title: str
    understanding_level: Optional[UnderstandingLevel]
    last_taught: Optional[datetime]
    revision_recommended: bool
    suggested_approach: str
    issues: Optional[str] = None

    class Config:
        from_attributes = True

class TimetableEntry(BaseModel):

    slot: int = Field(..., description="Sequential slot number starting from 1")
    date: str = Field(..., description="ISO date string: YYYY-MM-DD")
    day_of_week: str = Field(..., description="e.g. Monday")
    topic_id: str
    topic_title: str
    chapter_title: str
    suggested_hours: float
    teaching_method: TeachingMethod

    class Config:
        from_attributes = True

class RiskAssessment(BaseModel):

    risk_score: float = Field(
        ..., ge=0, le=100,
        description="Composite risk score: 0 = no risk, 100 = critical"
    )
    risk_level: RiskLevel
    completion_percentage: float
    delayed_topics_count: int
    hours_behind: float = Field(..., description="Teaching hours not yet delivered vs plan")
    predicted_completion_date: Optional[str] = Field(
        None, description="Estimated completion date (YYYY-MM-DD)"
    )
    delay_days: int = Field(..., description="Predicted extra days beyond 20-week baseline")
    is_on_track: bool
    topics_per_week: float
    weeks_remaining: Optional[float]
    risk_factors: List[str]
    mitigation_suggestions: List[str]

    class Config:
        from_attributes = True

class MethodEffectivenessItem(BaseModel):

    method: TeachingMethod
    avg_understanding_score: float = Field(
        ..., description="Average student understanding: 0=poor … 3=excellent"
    )
    usage_count: int = Field(..., description="Number of topics taught using this method")
    effectiveness_label: str = Field(
        ..., description="Human-readable label: Highly Effective / Effective / etc."
    )

    class Config:
        from_attributes = True

class AIRecommendationResponse(BaseModel):

    lesson_plan_id: str
    generated_at: datetime
    next_topic: Optional[NextTopicRecommendation] = None
    weak_areas: List[WeakAreaAlert] = []
    risk_assessment: RiskAssessment
    timetable_suggestions: List[TimetableEntry] = []
    method_effectiveness: List[MethodEffectivenessItem] = []
    llm_insights: Optional[Dict[str, Any]] = Field(
        None,
        description="Raw structured JSON from Ollama, keyed by analysis type"
    )
    ai_summary: Optional[str] = Field(
        None,
        description="LLM-generated narrative progress summary"
    )
    fallback_mode: bool = Field(
        ...,
        description="True when Ollama was unavailable and rules-only mode was used"
    )

    class Config:
        from_attributes = True

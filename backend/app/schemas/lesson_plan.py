"""
Pydantic request/response schemas for the Lesson Plan Management module.

Schemas are grouped by domain:
  - Subject   (SubjectCreate, SubjectUpdate, SubjectResponse)
  - Chapter   (ChapterCreate, ChapterResponse)
  - Topic     (TopicCreate, TopicResponse)
  - Subtopic  (SubtopicCreate, SubtopicResponse)
  - LessonPlan (LessonPlanCreate, LessonPlanUpdate, LessonPlanResponse)
  - TopicProgress (TopicProgressCreate, TopicProgressUpdate, TopicProgressResponse)
  - Aggregated views (CompletionStats, FacultyProgress)
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.lesson_plan import (
    LessonPlanStatus,
    TeachingMethod,
    TopicStatus,
    UnderstandingLevel,
)


# ===========================================================================
# Subject schemas
# ===========================================================================

class SubjectCreate(BaseModel):
    """Payload for creating a new subject."""

    name: str = Field(..., min_length=2, max_length=200)
    code: str = Field(..., min_length=2, max_length=20)
    description: Optional[str] = Field(None, max_length=1000)
    department: str = Field(..., min_length=2, max_length=100)
    semester: int = Field(..., ge=1, le=10)
    total_hours: int = Field(default=0, ge=0)

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()


class SubjectUpdate(BaseModel):
    """Partial update payload for a subject."""

    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    department: Optional[str] = Field(None, min_length=2, max_length=100)
    semester: Optional[int] = Field(None, ge=1, le=10)
    total_hours: Optional[int] = Field(None, ge=0)


class SubjectResponse(BaseModel):
    """Public representation of a subject."""

    id: str
    name: str
    code: str
    description: Optional[str]
    department: str
    semester: int
    total_hours: int
    is_active: bool
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# Chapter schemas
# ===========================================================================

class SubtopicCreate(BaseModel):
    """Payload for adding a subtopic to a topic."""

    title: str = Field(..., min_length=2, max_length=300)
    order: int = Field(default=1, ge=1)


class SubtopicResponse(BaseModel):
    subtopic_id: str
    title: str
    order: int


class TopicCreate(BaseModel):
    """Payload for adding a topic to a chapter."""

    title: str = Field(..., min_length=2, max_length=300)
    description: Optional[str] = Field(None, max_length=1000)
    order: int = Field(default=1, ge=1)
    planned_date: Optional[datetime] = None
    planned_hours: float = Field(default=1.0, gt=0, le=10)
    subtopics: List[SubtopicCreate] = []


class TopicResponse(BaseModel):
    topic_id: str
    title: str
    description: Optional[str]
    order: int
    planned_date: Optional[datetime]
    planned_hours: float
    subtopics: List[SubtopicResponse]


class ChapterCreate(BaseModel):
    """Payload for adding a chapter to a lesson plan."""

    title: str = Field(..., min_length=2, max_length=300)
    description: Optional[str] = Field(None, max_length=1000)
    order: int = Field(default=1, ge=1)
    topics: List[TopicCreate] = []


class ChapterResponse(BaseModel):
    chapter_id: str
    title: str
    description: Optional[str]
    order: int
    topics: List[TopicResponse]


# ===========================================================================
# Lesson Plan schemas
# ===========================================================================

class LessonPlanCreate(BaseModel):
    """Payload for creating a new lesson plan."""

    subject_id: str = Field(..., description="MongoDB ObjectId string of the subject")
    academic_year: str = Field(..., min_length=4, max_length=10, example="2025-26")
    semester: int = Field(..., ge=1, le=10)
    title: str = Field(..., min_length=2, max_length=300)
    description: Optional[str] = Field(None, max_length=1000)
    chapters: List[ChapterCreate] = []


class LessonPlanUpdate(BaseModel):
    """Partial update for lesson plan metadata."""

    title: Optional[str] = Field(None, min_length=2, max_length=300)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[LessonPlanStatus] = None


class LessonPlanResponse(BaseModel):
    """Full lesson plan with nested chapters → topics → subtopics."""

    id: str
    subject_id: str
    teacher_id: str
    academic_year: str
    semester: int
    title: str
    description: Optional[str]
    status: LessonPlanStatus
    chapters: List[ChapterResponse]
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LessonPlanSummary(BaseModel):
    """Lightweight lesson plan for list endpoints (without full chapter tree)."""

    id: str
    subject_id: str
    teacher_id: str
    academic_year: str
    semester: int
    title: str
    status: LessonPlanStatus
    chapter_count: int
    created_at: datetime
    updated_at: datetime


# ===========================================================================
# Topic Progress schemas
# ===========================================================================

class TopicProgressCreate(BaseModel):
    """
    Payload for recording (or upserting) topic completion progress.
    If a record already exists for the same lesson_plan_id + topic_id
    (+ optional subtopic_id), the service will update it.
    """

    lesson_plan_id: str
    chapter_id: str
    topic_id: str
    subtopic_id: Optional[str] = None
    subject_id: str

    status: TopicStatus = TopicStatus.IN_PROGRESS
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    teaching_method: Optional[TeachingMethod] = None
    actual_date: Optional[datetime] = None
    duration_taken: Optional[float] = Field(None, gt=0, description="Hours spent")
    student_understanding_level: Optional[UnderstandingLevel] = None
    remarks: Optional[str] = Field(None, max_length=1000)
    issues: Optional[str] = Field(None, max_length=1000)

    @field_validator("completion_percentage")
    @classmethod
    def sync_status_percentage(cls, v: float, info) -> float:
        """Auto-correct: 100% completion must set status = completed."""
        return v


class TopicProgressUpdate(BaseModel):
    """Partial update for an existing progress record."""

    status: Optional[TopicStatus] = None
    completion_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    teaching_method: Optional[TeachingMethod] = None
    actual_date: Optional[datetime] = None
    duration_taken: Optional[float] = Field(None, gt=0)
    student_understanding_level: Optional[UnderstandingLevel] = None
    remarks: Optional[str] = Field(None, max_length=1000)
    issues: Optional[str] = Field(None, max_length=1000)


class TopicProgressResponse(BaseModel):
    """Public representation of a topic progress record."""

    id: str
    lesson_plan_id: str
    chapter_id: str
    topic_id: str
    subtopic_id: Optional[str]
    teacher_id: str
    subject_id: str
    status: TopicStatus
    completion_percentage: float
    teaching_method: Optional[TeachingMethod]
    actual_date: Optional[datetime]
    duration_taken: Optional[float]
    student_understanding_level: Optional[UnderstandingLevel]
    remarks: Optional[str]
    issues: Optional[str]
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# Aggregated / analytics schemas
# ===========================================================================

class CompletionStats(BaseModel):
    """
    Per-lesson-plan completion overview returned by
    GET /topic-progress/completion/{lesson_plan_id}
    """

    lesson_plan_id: str
    total_topics: int
    completed_topics: int
    in_progress_topics: int
    pending_topics: int
    skipped_topics: int
    overall_completion_percentage: float
    total_hours_planned: float
    total_hours_delivered: float


class PendingTopicItem(BaseModel):
    """A single pending topic row in the pending-topics response."""

    lesson_plan_id: str
    chapter_id: str
    chapter_title: str
    topic_id: str
    topic_title: str
    planned_date: Optional[datetime]
    planned_hours: float


class FacultyProgressItem(BaseModel):
    """Summary row for a single lesson plan in the faculty progress view."""

    lesson_plan_id: str
    subject_id: str
    title: str
    academic_year: str
    semester: int
    status: LessonPlanStatus
    total_topics: int
    completed_topics: int
    completion_percentage: float

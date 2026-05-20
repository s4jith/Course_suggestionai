"""
Lesson Plan domain models – MongoDB document structures for:
  - SubjectDocument         → `subjects` collection
  - LessonPlanDocument      → `lesson_plans` collection  (embeds chapters → topics → subtopics)
  - TopicProgressDocument   → `topic_progress` collection

Embedded sub-documents (Chapter, Topic, Subtopic) are NOT stored as separate
collections; they live inside the lesson plan document for efficient retrieval
of the full plan in a single query.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

# Reuse the shared PyObjectId helper from the user model
from app.models.user import PyObjectId


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class LessonPlanStatus(str, Enum):
    """Lifecycle states for a lesson plan."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TeachingMethod(str, Enum):
    """Supported teaching methods for topic delivery."""
    THEORETICAL = "theoretical"
    PRACTICAL = "practical"
    PPT = "ppt"
    SEMINAR = "seminar"
    LAB = "lab"
    ASSIGNMENT = "assignment"
    DISCUSSION = "discussion"
    CASE_STUDY = "case_study"
    VIDEO_BASED = "video_based"


class TopicStatus(str, Enum):
    """Completion states for an individual topic / subtopic."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class UnderstandingLevel(str, Enum):
    """Student comprehension rating recorded after delivery."""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"


# ---------------------------------------------------------------------------
# Embedded sub-document models (stored inside LessonPlanDocument)
# ---------------------------------------------------------------------------

class SubtopicDocument(BaseModel):
    """A fine-grained subtopic nested inside a topic."""

    subtopic_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    order: int = 1

    class Config:
        populate_by_name = True


class TopicDocument(BaseModel):
    """A topic nested inside a chapter, containing optional subtopics."""

    topic_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    order: int = 1
    planned_date: Optional[datetime] = None
    planned_hours: float = Field(default=1.0, gt=0)
    subtopics: List[SubtopicDocument] = []

    class Config:
        populate_by_name = True


class ChapterDocument(BaseModel):
    """A chapter nested inside a lesson plan, containing topics."""

    chapter_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    order: int = 1
    topics: List[TopicDocument] = []

    class Config:
        populate_by_name = True


# ---------------------------------------------------------------------------
# Top-level collection document models
# ---------------------------------------------------------------------------

class SubjectDocument(BaseModel):
    """
    Represents a `subjects` collection document.
    A subject is the academic course (e.g., "Data Structures", "Physics Lab").
    """

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str
    code: str                         # Unique short code, e.g. "CS301"
    description: Optional[str] = None
    department: str
    semester: int = Field(ge=1, le=10)
    total_hours: int = Field(default=0, ge=0)
    is_active: bool = True

    # Audit fields
    created_by: str                   # User ObjectId string
    updated_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Collection:
        name = "subjects"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class LessonPlanDocument(BaseModel):
    """
    Represents a `lesson_plans` collection document.
    Contains the full hierarchical plan: chapters → topics → subtopics.
    """

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    subject_id: str                   # References a SubjectDocument._id
    teacher_id: str                   # References a UserDocument._id
    academic_year: str                # e.g. "2025-26"
    semester: int = Field(ge=1, le=10)
    title: str
    description: Optional[str] = None
    status: LessonPlanStatus = LessonPlanStatus.DRAFT
    chapters: List[ChapterDocument] = []

    # Audit fields
    created_by: str
    updated_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Collection:
        name = "lesson_plans"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class TopicProgressDocument(BaseModel):
    """
    Represents a `topic_progress` collection document.
    One record per teacher × topic (or subtopic) session.
    Multiple progress records can exist for the same topic (e.g. split sessions).
    """

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    lesson_plan_id: str
    chapter_id: str
    topic_id: str
    subtopic_id: Optional[str] = None   # None → progress is at the topic level
    teacher_id: str
    subject_id: str

    # Completion tracking
    status: TopicStatus = TopicStatus.PENDING
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0)

    # Teaching session details
    teaching_method: Optional[TeachingMethod] = None
    actual_date: Optional[datetime] = None
    duration_taken: Optional[float] = Field(default=None, gt=0)  # hours

    # Quality metrics
    student_understanding_level: Optional[UnderstandingLevel] = None
    remarks: Optional[str] = None
    issues: Optional[str] = None

    # Audit fields
    created_by: str
    updated_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Collection:
        name = "topic_progress"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

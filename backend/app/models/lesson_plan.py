
import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from app.models.user import PyObjectId

class LessonPlanStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class TeachingMethod(str, Enum):
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
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"

class UnderstandingLevel(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"

class SubtopicDocument(BaseModel):

    subtopic_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    order: int = 1

    class Config:
        populate_by_name = True

class TopicDocument(BaseModel):

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

    chapter_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    order: int = 1
    topics: List[TopicDocument] = []

    class Config:
        populate_by_name = True

class SubjectDocument(BaseModel):

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str
    code: str
    description: Optional[str] = None
    department: str
    semester: int = Field(ge=1, le=10)
    total_hours: int = Field(default=0, ge=0)
    is_active: bool = True

    created_by: str
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

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    subject_id: str
    teacher_id: str
    academic_year: str
    semester: int = Field(ge=1, le=10)
    title: str
    description: Optional[str] = None
    status: LessonPlanStatus = LessonPlanStatus.DRAFT
    chapters: List[ChapterDocument] = []

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

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    lesson_plan_id: str
    chapter_id: str
    topic_id: str
    subtopic_id: Optional[str] = None
    teacher_id: str
    subject_id: str

    status: TopicStatus = TopicStatus.PENDING
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0)

    teaching_method: Optional[TeachingMethod] = None
    actual_date: Optional[datetime] = None
    duration_taken: Optional[float] = Field(default=None, gt=0)

    student_understanding_level: Optional[UnderstandingLevel] = None
    remarks: Optional[str] = None
    issues: Optional[str] = None

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

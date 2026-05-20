"""
Lesson Plan Service – orchestrates all business logic for the module.

Covers:
  - Subject CRUD
  - Lesson Plan CRUD + nested chapter / topic / subtopic management
  - Topic progress recording and analytics
"""

from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import AlreadyExistsException, NotFoundException, ValidationException
from app.models.lesson_plan import (
    ChapterDocument,
    LessonPlanDocument,
    LessonPlanStatus,
    SubjectDocument,
    SubtopicDocument,
    TopicDocument,
    TopicProgressDocument,
    TopicStatus,
)
from app.models.user import UserDocument, UserRole
from app.repositories.lesson_plan_repository import LessonPlanRepository
from app.repositories.subject_repository import SubjectRepository
from app.repositories.topic_progress_repository import TopicProgressRepository
from app.schemas.lesson_plan import (
    ChapterCreate,
    CompletionStats,
    FacultyProgressItem,
    LessonPlanCreate,
    LessonPlanResponse,
    LessonPlanSummary,
    LessonPlanUpdate,
    PendingTopicItem,
    SubjectCreate,
    SubjectResponse,
    SubjectUpdate,
    SubtopicCreate,
    SubtopicResponse,
    TopicCreate,
    TopicProgressCreate,
    TopicProgressResponse,
    TopicProgressUpdate,
    TopicResponse,
)


# ---------------------------------------------------------------------------
# Internal helpers – model → response schema conversions
# ---------------------------------------------------------------------------

def _subject_to_response(s: SubjectDocument) -> SubjectResponse:
    return SubjectResponse(
        id=str(s.id),
        name=s.name,
        code=s.code,
        description=s.description,
        department=s.department,
        semester=s.semester,
        total_hours=s.total_hours,
        is_active=s.is_active,
        created_by=s.created_by,
        updated_by=s.updated_by,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _progress_to_response(p: TopicProgressDocument) -> TopicProgressResponse:
    return TopicProgressResponse(
        id=str(p.id),
        lesson_plan_id=p.lesson_plan_id,
        chapter_id=p.chapter_id,
        topic_id=p.topic_id,
        subtopic_id=p.subtopic_id,
        teacher_id=p.teacher_id,
        subject_id=p.subject_id,
        status=p.status,
        completion_percentage=p.completion_percentage,
        teaching_method=p.teaching_method,
        actual_date=p.actual_date,
        duration_taken=p.duration_taken,
        student_understanding_level=p.student_understanding_level,
        remarks=p.remarks,
        issues=p.issues,
        created_by=p.created_by,
        updated_by=p.updated_by,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _plan_to_response(plan: LessonPlanDocument) -> LessonPlanResponse:
    return LessonPlanResponse(
        id=str(plan.id),
        subject_id=plan.subject_id,
        teacher_id=plan.teacher_id,
        academic_year=plan.academic_year,
        semester=plan.semester,
        title=plan.title,
        description=plan.description,
        status=plan.status,
        chapters=[
            {
                "chapter_id": ch.chapter_id,
                "title": ch.title,
                "description": ch.description,
                "order": ch.order,
                "topics": [
                    {
                        "topic_id": tp.topic_id,
                        "title": tp.title,
                        "description": tp.description,
                        "order": tp.order,
                        "planned_date": tp.planned_date,
                        "planned_hours": tp.planned_hours,
                        "subtopics": [
                            {"subtopic_id": st.subtopic_id, "title": st.title, "order": st.order}
                            for st in tp.subtopics
                        ],
                    }
                    for tp in ch.topics
                ],
            }
            for ch in plan.chapters
        ],
        created_by=plan.created_by,
        updated_by=plan.updated_by,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def _plan_to_summary(plan: LessonPlanDocument) -> LessonPlanSummary:
    total_topics = sum(len(ch.topics) for ch in plan.chapters)
    return LessonPlanSummary(
        id=str(plan.id),
        subject_id=plan.subject_id,
        teacher_id=plan.teacher_id,
        academic_year=plan.academic_year,
        semester=plan.semester,
        title=plan.title,
        status=plan.status,
        chapter_count=len(plan.chapters),
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class LessonPlanService:
    """
    Central service for Subjects, Lesson Plans, and Topic Progress.
    All public methods are async and raise typed AppExceptions on errors.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._subjects = SubjectRepository(db)
        self._plans = LessonPlanRepository(db)
        self._progress = TopicProgressRepository(db)

    # =======================================================================
    # Subject operations
    # =======================================================================

    async def create_subject(
        self, payload: SubjectCreate, current_user: UserDocument
    ) -> SubjectResponse:
        """Create a new subject. Subject codes must be globally unique."""
        if await self._subjects.code_exists(payload.code):
            raise AlreadyExistsException(f"Subject with code '{payload.code.upper()}'")

        doc = SubjectDocument(
            name=payload.name,
            code=payload.code.upper(),
            description=payload.description,
            department=payload.department,
            semester=payload.semester,
            total_hours=payload.total_hours,
            created_by=str(current_user.id),
            updated_by=str(current_user.id),
        )
        created = await self._subjects.create(doc)
        return _subject_to_response(created)

    async def get_subject(self, subject_id: str) -> SubjectResponse:
        subject = await self._subjects.find_by_id(subject_id)
        if not subject:
            raise NotFoundException("Subject")
        return _subject_to_response(subject)

    async def list_subjects(
        self,
        department: Optional[str],
        semester: Optional[int],
        is_active: Optional[bool],
        skip: int,
        limit: int,
    ) -> tuple[list[SubjectResponse], int]:
        subjects = await self._subjects.list_subjects(department, semester, is_active, skip, limit)
        total = await self._subjects.count_subjects(department, semester, is_active)
        return [_subject_to_response(s) for s in subjects], total

    async def update_subject(
        self, subject_id: str, payload: SubjectUpdate, current_user: UserDocument
    ) -> SubjectResponse:
        subject = await self._subjects.find_by_id(subject_id)
        if not subject:
            raise NotFoundException("Subject")

        updates = payload.model_dump(exclude_none=True)
        updates["updated_by"] = str(current_user.id)

        updated = await self._subjects.update(subject_id, updates)
        return _subject_to_response(updated)

    async def deactivate_subject(self, subject_id: str) -> None:
        subject = await self._subjects.find_by_id(subject_id)
        if not subject:
            raise NotFoundException("Subject")
        await self._subjects.deactivate(subject_id)

    # =======================================================================
    # Lesson Plan operations
    # =======================================================================

    async def create_lesson_plan(
        self, payload: LessonPlanCreate, current_user: UserDocument
    ) -> LessonPlanResponse:
        """Create a lesson plan, optionally pre-populated with chapters and topics."""
        # Verify the subject exists
        subject = await self._subjects.find_by_id(payload.subject_id)
        if not subject:
            raise NotFoundException("Subject")

        chapters = [
            ChapterDocument(
                title=ch.title,
                description=ch.description,
                order=ch.order,
                topics=[
                    TopicDocument(
                        title=tp.title,
                        description=tp.description,
                        order=tp.order,
                        planned_date=tp.planned_date,
                        planned_hours=tp.planned_hours,
                        subtopics=[
                            SubtopicDocument(title=st.title, order=st.order)
                            for st in tp.subtopics
                        ],
                    )
                    for tp in ch.topics
                ],
            )
            for ch in payload.chapters
        ]

        doc = LessonPlanDocument(
            subject_id=payload.subject_id,
            teacher_id=str(current_user.id),
            academic_year=payload.academic_year,
            semester=payload.semester,
            title=payload.title,
            description=payload.description,
            chapters=chapters,
            created_by=str(current_user.id),
            updated_by=str(current_user.id),
        )
        created = await self._plans.create(doc)
        return _plan_to_response(created)

    async def get_lesson_plan(self, plan_id: str) -> LessonPlanResponse:
        plan = await self._plans.find_by_id(plan_id)
        if not plan:
            raise NotFoundException("Lesson plan")
        return _plan_to_response(plan)

    async def list_lesson_plans(
        self,
        teacher_id: Optional[str],
        subject_id: Optional[str],
        academic_year: Optional[str],
        status: Optional[LessonPlanStatus],
        semester: Optional[int],
        skip: int,
        limit: int,
    ) -> tuple[list[LessonPlanSummary], int]:
        plans = await self._plans.list_plans(
            teacher_id, subject_id, academic_year, status, semester, skip, limit
        )
        total = await self._plans.count_plans(
            teacher_id, subject_id, academic_year, status, semester
        )
        return [_plan_to_summary(p) for p in plans], total

    async def update_lesson_plan(
        self, plan_id: str, payload: LessonPlanUpdate, current_user: UserDocument
    ) -> LessonPlanResponse:
        plan = await self._plans.find_by_id(plan_id)
        if not plan:
            raise NotFoundException("Lesson plan")

        # Teachers can only update their own plans; admins can update any
        if current_user.role == UserRole.TEACHER and plan.teacher_id != str(current_user.id):
            from app.core.exceptions import InsufficientPermissionsException
            raise InsufficientPermissionsException("admin")

        updates = payload.model_dump(exclude_none=True)
        if "status" in updates:
            updates["status"] = updates["status"].value
        updates["updated_by"] = str(current_user.id)

        updated = await self._plans.update_plan(plan_id, updates)
        return _plan_to_response(updated)

    # ------------------------------------------------------------------
    # Chapter operations
    # ------------------------------------------------------------------

    async def add_chapter(
        self, plan_id: str, payload: ChapterCreate, current_user: UserDocument
    ) -> LessonPlanResponse:
        plan = await self._plans.find_by_id(plan_id)
        if not plan:
            raise NotFoundException("Lesson plan")

        chapter = ChapterDocument(
            title=payload.title,
            description=payload.description,
            order=payload.order,
            topics=[
                TopicDocument(
                    title=tp.title,
                    description=tp.description,
                    order=tp.order,
                    planned_date=tp.planned_date,
                    planned_hours=tp.planned_hours,
                    subtopics=[
                        SubtopicDocument(title=st.title, order=st.order)
                        for st in tp.subtopics
                    ],
                )
                for tp in payload.topics
            ],
        )
        updated = await self._plans.add_chapter(plan_id, chapter, str(current_user.id))
        return _plan_to_response(updated)

    # ------------------------------------------------------------------
    # Topic operations
    # ------------------------------------------------------------------

    async def add_topic(
        self,
        plan_id: str,
        chapter_id: str,
        payload: TopicCreate,
        current_user: UserDocument,
    ) -> LessonPlanResponse:
        plan = await self._plans.find_by_id(plan_id)
        if not plan:
            raise NotFoundException("Lesson plan")

        # Validate the chapter_id actually exists in this plan
        chapter_ids = [ch.chapter_id for ch in plan.chapters]
        if chapter_id not in chapter_ids:
            raise NotFoundException("Chapter")

        topic = TopicDocument(
            title=payload.title,
            description=payload.description,
            order=payload.order,
            planned_date=payload.planned_date,
            planned_hours=payload.planned_hours,
            subtopics=[
                SubtopicDocument(title=st.title, order=st.order)
                for st in payload.subtopics
            ],
        )
        updated = await self._plans.add_topic(plan_id, chapter_id, topic, str(current_user.id))
        return _plan_to_response(updated)

    # ------------------------------------------------------------------
    # Subtopic operations
    # ------------------------------------------------------------------

    async def add_subtopic(
        self,
        plan_id: str,
        chapter_id: str,
        topic_id: str,
        payload: SubtopicCreate,
        current_user: UserDocument,
    ) -> LessonPlanResponse:
        plan = await self._plans.find_by_id(plan_id)
        if not plan:
            raise NotFoundException("Lesson plan")

        # Validate chapter and topic exist in this plan
        chapter = next((ch for ch in plan.chapters if ch.chapter_id == chapter_id), None)
        if not chapter:
            raise NotFoundException("Chapter")
        topic = next((tp for tp in chapter.topics if tp.topic_id == topic_id), None)
        if not topic:
            raise NotFoundException("Topic")

        subtopic = SubtopicDocument(title=payload.title, order=payload.order)
        updated = await self._plans.add_subtopic(
            plan_id, chapter_id, topic_id, subtopic, str(current_user.id)
        )
        return _plan_to_response(updated)

    # =======================================================================
    # Topic Progress operations
    # =======================================================================

    async def record_progress(
        self, payload: TopicProgressCreate, current_user: UserDocument
    ) -> TopicProgressResponse:
        """
        Upsert a progress record.
        Auto-sets status to COMPLETED when completion_percentage == 100.
        """
        # Validate lesson plan exists
        plan = await self._plans.find_by_id(payload.lesson_plan_id)
        if not plan:
            raise NotFoundException("Lesson plan")

        # Sync status when fully complete
        status = payload.status
        if payload.completion_percentage == 100.0:
            status = TopicStatus.COMPLETED

        doc = TopicProgressDocument(
            lesson_plan_id=payload.lesson_plan_id,
            chapter_id=payload.chapter_id,
            topic_id=payload.topic_id,
            subtopic_id=payload.subtopic_id,
            teacher_id=str(current_user.id),
            subject_id=payload.subject_id,
            status=status,
            completion_percentage=payload.completion_percentage,
            teaching_method=payload.teaching_method,
            actual_date=payload.actual_date,
            duration_taken=payload.duration_taken,
            student_understanding_level=payload.student_understanding_level,
            remarks=payload.remarks,
            issues=payload.issues,
            created_by=str(current_user.id),
            updated_by=str(current_user.id),
        )
        result = await self._progress.upsert(doc)
        return _progress_to_response(result)

    async def update_progress(
        self, progress_id: str, payload: TopicProgressUpdate, current_user: UserDocument
    ) -> TopicProgressResponse:
        updates = payload.model_dump(exclude_none=True)
        if not updates:
            raise ValidationException("No update fields provided.")

        # Sync status when explicitly set to 100%
        if updates.get("completion_percentage") == 100.0 and "status" not in updates:
            updates["status"] = TopicStatus.COMPLETED.value
        elif "status" in updates:
            updates["status"] = updates["status"].value
        if "teaching_method" in updates and updates["teaching_method"]:
            updates["teaching_method"] = updates["teaching_method"].value
        if "student_understanding_level" in updates and updates["student_understanding_level"]:
            updates["student_understanding_level"] = updates["student_understanding_level"].value

        updates["updated_by"] = str(current_user.id)
        result = await self._progress.update_progress(progress_id, updates)
        if not result:
            raise NotFoundException("Progress record")
        return _progress_to_response(result)

    async def get_pending_topics(
        self, lesson_plan_id: str, current_user: UserDocument
    ) -> list[PendingTopicItem]:
        """
        Return all topics not yet completed for a lesson plan.
        Pending topics are derived from the plan's chapter/topic tree minus
        completed progress records.
        """
        plan = await self._plans.find_by_id(lesson_plan_id)
        if not plan:
            raise NotFoundException("Lesson plan")

        # Fetch all completed topic IDs for this plan + teacher
        completed_docs = await self._progress.list_for_plan(
            lesson_plan_id, status=TopicStatus.COMPLETED, limit=1000
        )
        completed_topic_ids = {d.topic_id for d in completed_docs}

        pending: list[PendingTopicItem] = []
        for chapter in plan.chapters:
            for topic in chapter.topics:
                if topic.topic_id not in completed_topic_ids:
                    pending.append(
                        PendingTopicItem(
                            lesson_plan_id=lesson_plan_id,
                            chapter_id=chapter.chapter_id,
                            chapter_title=chapter.title,
                            topic_id=topic.topic_id,
                            topic_title=topic.title,
                            planned_date=topic.planned_date,
                            planned_hours=topic.planned_hours,
                        )
                    )
        return pending

    async def get_completion_stats(self, lesson_plan_id: str) -> CompletionStats:
        """
        Return a completion summary for a lesson plan including percentage,
        status breakdown, and hours delivered.
        """
        plan = await self._plans.find_by_id(lesson_plan_id)
        if not plan:
            raise NotFoundException("Lesson plan")

        total_topics = sum(len(ch.topics) for ch in plan.chapters)
        total_hours_planned = sum(
            tp.planned_hours for ch in plan.chapters for tp in ch.topics
        )

        status_counts = await self._progress.count_by_status(lesson_plan_id)
        hours_delivered = await self._progress.sum_hours_delivered(lesson_plan_id)

        completed = status_counts.get("completed", 0)
        skipped = status_counts.get("skipped", 0)
        overall_pct = round((completed / total_topics * 100), 2) if total_topics > 0 else 0.0

        return CompletionStats(
            lesson_plan_id=lesson_plan_id,
            total_topics=total_topics,
            completed_topics=completed,
            in_progress_topics=status_counts.get("in_progress", 0),
            pending_topics=status_counts.get("pending", 0),
            skipped_topics=skipped,
            overall_completion_percentage=overall_pct,
            total_hours_planned=total_hours_planned,
            total_hours_delivered=hours_delivered,
        )

    async def get_faculty_progress(
        self, teacher_id: str, academic_year: Optional[str] = None
    ) -> list[FacultyProgressItem]:
        """
        Return a progress summary row for every lesson plan belonging to a teacher.
        """
        plans = await self._plans.list_plans(
            teacher_id=teacher_id, academic_year=academic_year, limit=100
        )

        items: list[FacultyProgressItem] = []
        for plan in plans:
            total_topics = sum(len(ch.topics) for ch in plan.chapters)
            status_counts = await self._progress.count_by_status(str(plan.id))
            completed = status_counts.get("completed", 0)
            pct = round((completed / total_topics * 100), 2) if total_topics > 0 else 0.0

            items.append(
                FacultyProgressItem(
                    lesson_plan_id=str(plan.id),
                    subject_id=plan.subject_id,
                    title=plan.title,
                    academic_year=plan.academic_year,
                    semester=plan.semester,
                    status=plan.status,
                    total_topics=total_topics,
                    completed_topics=completed,
                    completion_percentage=pct,
                )
            )
        return items

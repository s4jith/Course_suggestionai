"""
Topic Progress routes – record, update, and query topic completion.

All routes live under the /api/v1/topic-progress prefix (configured in main.py).

IMPORTANT: Literal path segments (/pending, /completion, /faculty) are defined
BEFORE parameterised segments (/{progress_id}) so FastAPI routes them correctly.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_active_user, require_teacher
from app.core.responses import SuccessResponse, success_response
from app.database.mongodb import get_database
from app.models.user import UserDocument
from app.schemas.lesson_plan import (
    CompletionStats,
    FacultyProgressItem,
    PendingTopicItem,
    TopicProgressCreate,
    TopicProgressResponse,
    TopicProgressUpdate,
)
from app.services.lesson_plan_service import LessonPlanService

router = APIRouter(prefix="/topic-progress", tags=["Topic Progress"])


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_service(db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]) -> LessonPlanService:
    return LessonPlanService(db)


# ===========================================================================
# Record / update progress
# ===========================================================================

@router.post(
    "/",
    response_model=SuccessResponse[TopicProgressResponse],
    status_code=status.HTTP_200_OK,
    summary="Record or update topic completion progress",
)
async def record_progress(
    payload: TopicProgressCreate,
    current_user: Annotated[UserDocument, Depends(require_teacher)],
    service: Annotated[LessonPlanService, Depends(get_service)],
):
    """
    Create or update a progress record for a topic (or subtopic).
    Uses upsert semantics: one record per teacher × lesson plan × topic.

    Setting `completion_percentage` to **100** automatically sets `status` to `completed`.

    **Example request:**
    ```json
    {
      "lesson_plan_id": "683abc123def456789012345",
      "chapter_id": "chap-uuid-here",
      "topic_id": "topic-uuid-here",
      "subject_id": "683abc111def456789011111",
      "status": "completed",
      "completion_percentage": 100,
      "teaching_method": "ppt",
      "actual_date": "2026-05-20T10:00:00",
      "duration_taken": 1.5,
      "student_understanding_level": "good",
      "remarks": "Students engaged well. Covered all subtopics.",
      "issues": null
    }
    ```

    **Example response:**
    ```json
    {
      "success": true,
      "message": "Progress recorded successfully.",
      "data": {
        "id": "683def456abc789012345678",
        "lesson_plan_id": "683abc123def456789012345",
        "chapter_id": "chap-uuid-here",
        "topic_id": "topic-uuid-here",
        "subtopic_id": null,
        "teacher_id": "683abc000def000000000001",
        "subject_id": "683abc111def456789011111",
        "status": "completed",
        "completion_percentage": 100.0,
        "teaching_method": "ppt",
        "actual_date": "2026-05-20T10:00:00",
        "duration_taken": 1.5,
        "student_understanding_level": "good",
        "remarks": "Students engaged well. Covered all subtopics.",
        "issues": null,
        "created_by": "683abc000def000000000001",
        "updated_by": "683abc000def000000000001",
        "created_at": "2026-05-20T10:05:00",
        "updated_at": "2026-05-20T10:05:00"
      }
    }
    ```
    """
    result = await service.record_progress(payload, current_user)
    return success_response(data=result, message="Progress recorded successfully.")


@router.patch(
    "/{progress_id}",
    response_model=SuccessResponse[TopicProgressResponse],
    status_code=status.HTTP_200_OK,
    summary="Update an existing progress record",
)
async def update_progress(
    progress_id: str,
    payload: TopicProgressUpdate,
    current_user: Annotated[UserDocument, Depends(require_teacher)],
    service: Annotated[LessonPlanService, Depends(get_service)],
):
    """
    Partially update a progress record by its ID.
    Only provided fields are updated; others are left unchanged.
    """
    result = await service.update_progress(progress_id, payload, current_user)
    return success_response(data=result, message="Progress updated successfully.")


# ===========================================================================
# Analytics – IMPORTANT: literal routes before /{progress_id}
# ===========================================================================

@router.get(
    "/pending",
    response_model=SuccessResponse[list[PendingTopicItem]],
    status_code=status.HTTP_200_OK,
    summary="Get all pending topics for a lesson plan",
)
async def get_pending_topics(
    lesson_plan_id: str = Query(..., description="Lesson plan ObjectId"),
    current_user: Annotated[UserDocument, Depends(get_current_active_user)] = None,
    service: Annotated[LessonPlanService, Depends(get_service)] = None,
):
    """
    Return topics in a lesson plan that have not yet been marked as completed.
    Useful for scheduling upcoming classes.

    **Example response:**
    ```json
    {
      "success": true,
      "message": "Pending topics retrieved.",
      "data": [
        {
          "lesson_plan_id": "683abc123def456789012345",
          "chapter_id": "chap-uuid",
          "chapter_title": "Linked Lists",
          "topic_id": "topic-uuid",
          "topic_title": "Doubly Linked List",
          "planned_date": "2026-06-15T09:00:00",
          "planned_hours": 2.0
        }
      ]
    }
    ```
    """
    items = await service.get_pending_topics(lesson_plan_id, current_user)
    return success_response(data=items, message="Pending topics retrieved.")


@router.get(
    "/completion/{lesson_plan_id}",
    response_model=SuccessResponse[CompletionStats],
    status_code=status.HTTP_200_OK,
    summary="Get completion statistics for a lesson plan",
)
async def get_completion_stats(
    lesson_plan_id: str,
    _: Annotated[UserDocument, Depends(get_current_active_user)] = None,
    service: Annotated[LessonPlanService, Depends(get_service)] = None,
):
    """
    Return a completion breakdown for a lesson plan:
    - total / completed / in-progress / pending / skipped topics
    - overall completion percentage
    - planned vs delivered hours

    **Example response:**
    ```json
    {
      "success": true,
      "message": "Completion stats retrieved.",
      "data": {
        "lesson_plan_id": "683abc123def456789012345",
        "total_topics": 20,
        "completed_topics": 12,
        "in_progress_topics": 2,
        "pending_topics": 5,
        "skipped_topics": 1,
        "overall_completion_percentage": 60.0,
        "total_hours_planned": 40.0,
        "total_hours_delivered": 24.5
      }
    }
    ```
    """
    stats = await service.get_completion_stats(lesson_plan_id)
    return success_response(data=stats, message="Completion stats retrieved.")


@router.get(
    "/faculty/{teacher_id}",
    response_model=SuccessResponse[list[FacultyProgressItem]],
    status_code=status.HTTP_200_OK,
    summary="Get progress summary across all lesson plans for a faculty member",
)
async def get_faculty_progress(
    teacher_id: str,
    academic_year: Optional[str] = Query(None, description="Filter by academic year, e.g. 2025-26"),
    _: Annotated[UserDocument, Depends(get_current_active_user)] = None,
    service: Annotated[LessonPlanService, Depends(get_service)] = None,
):
    """
    Return a per-plan progress summary for a faculty member.
    Admins can query any teacher; teachers typically query themselves.

    **Example response:**
    ```json
    {
      "success": true,
      "message": "Faculty progress retrieved.",
      "data": [
        {
          "lesson_plan_id": "683abc123def456789012345",
          "subject_id": "683abc111def456789011111",
          "title": "DS Full Semester Plan",
          "academic_year": "2025-26",
          "semester": 3,
          "status": "active",
          "total_topics": 20,
          "completed_topics": 12,
          "completion_percentage": 60.0
        }
      ]
    }
    ```
    """
    items = await service.get_faculty_progress(teacher_id, academic_year)
    return success_response(data=items, message="Faculty progress retrieved.")

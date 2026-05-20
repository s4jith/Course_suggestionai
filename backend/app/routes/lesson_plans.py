"""
Lesson Plan routes – full CRUD plus nested chapter / topic / subtopic management.

All routes live under the /api/v1/lesson-plans prefix (configured in main.py).

Permissions:
  - GET  endpoints: any authenticated active user
  - POST / PATCH: teacher or admin
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_active_user, require_teacher
from app.core.responses import PaginatedResponse, SuccessResponse, success_response
from app.database.mongodb import get_database
from app.models.lesson_plan import LessonPlanStatus
from app.models.user import UserDocument
from app.schemas.lesson_plan import (
    ChapterCreate,
    LessonPlanCreate,
    LessonPlanResponse,
    LessonPlanSummary,
    LessonPlanUpdate,
    SubtopicCreate,
    TopicCreate,
)
from app.services.lesson_plan_service import LessonPlanService

router = APIRouter(prefix="/lesson-plans", tags=["Lesson Plans"])


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_service(db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]) -> LessonPlanService:
    return LessonPlanService(db)


# ===========================================================================
# Lesson Plan CRUD
# ===========================================================================

@router.post(
    "/",
    response_model=SuccessResponse[LessonPlanResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new lesson plan",
)
async def create_lesson_plan(
    payload: LessonPlanCreate,
    current_user: Annotated[UserDocument, Depends(require_teacher)],
    service: Annotated[LessonPlanService, Depends(get_service)],
):
    """
    Create a lesson plan for a subject. Chapters, topics, and subtopics
    can be included inline or added later via nested endpoints.

    **Example request:**
    ```json
    {
      "subject_id": "683abc123def456789012345",
      "academic_year": "2025-26",
      "semester": 3,
      "title": "DS Full Semester Plan",
      "description": "Complete lesson plan for Data Structures",
      "chapters": [
        {
          "title": "Arrays and Strings",
          "order": 1,
          "topics": [
            {
              "title": "Introduction to Arrays",
              "planned_hours": 2,
              "order": 1
            }
          ]
        }
      ]
    }
    ```
    """
    plan = await service.create_lesson_plan(payload, current_user)
    return success_response(data=plan, message="Lesson plan created successfully.")


@router.get(
    "/",
    response_model=PaginatedResponse[LessonPlanSummary],
    status_code=status.HTTP_200_OK,
    summary="List lesson plans",
)
async def list_lesson_plans(
    teacher_id: Optional[str] = Query(None, description="Filter by teacher ID"),
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    academic_year: Optional[str] = Query(None, description="e.g. 2025-26"),
    semester: Optional[int] = Query(None, ge=1, le=10),
    plan_status: Optional[LessonPlanStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    _: Annotated[UserDocument, Depends(get_current_active_user)] = None,
    service: Annotated[LessonPlanService, Depends(get_service)] = None,
):
    """
    Return a paginated list of lesson plan summaries.
    Use `teacher_id=me` pattern by passing your own ID, or let admins query any teacher.
    """
    skip = (page - 1) * page_size
    plans, total = await service.list_lesson_plans(
        teacher_id, subject_id, academic_year, plan_status, semester, skip, page_size
    )
    return PaginatedResponse(
        data=plans,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=-(-total // page_size),
    )


@router.get(
    "/{plan_id}",
    response_model=SuccessResponse[LessonPlanResponse],
    status_code=status.HTTP_200_OK,
    summary="Get a full lesson plan with chapter tree",
)
async def get_lesson_plan(
    plan_id: str,
    _: Annotated[UserDocument, Depends(get_current_active_user)] = None,
    service: Annotated[LessonPlanService, Depends(get_service)] = None,
):
    """Return the full lesson plan including all chapters → topics → subtopics."""
    plan = await service.get_lesson_plan(plan_id)
    return success_response(data=plan, message="Lesson plan retrieved successfully.")


@router.patch(
    "/{plan_id}",
    response_model=SuccessResponse[LessonPlanResponse],
    status_code=status.HTTP_200_OK,
    summary="Update lesson plan metadata or status",
)
async def update_lesson_plan(
    plan_id: str,
    payload: LessonPlanUpdate,
    current_user: Annotated[UserDocument, Depends(require_teacher)],
    service: Annotated[LessonPlanService, Depends(get_service)],
):
    """
    Update title, description, or status of a lesson plan.
    Teachers can only update their own plans; admins can update any.

    **Status transitions:** draft → active → completed → archived
    """
    updated = await service.update_lesson_plan(plan_id, payload, current_user)
    return success_response(data=updated, message="Lesson plan updated successfully.")


# ===========================================================================
# Chapter management
# ===========================================================================

@router.post(
    "/{plan_id}/chapters",
    response_model=SuccessResponse[LessonPlanResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add a chapter to a lesson plan",
)
async def add_chapter(
    plan_id: str,
    payload: ChapterCreate,
    current_user: Annotated[UserDocument, Depends(require_teacher)],
    service: Annotated[LessonPlanService, Depends(get_service)],
):
    """
    Append a new chapter (with optional topics) to an existing lesson plan.

    **Example request:**
    ```json
    {
      "title": "Linked Lists",
      "order": 2,
      "topics": [
        {"title": "Singly Linked List", "planned_hours": 2, "order": 1},
        {"title": "Doubly Linked List", "planned_hours": 2, "order": 2}
      ]
    }
    ```
    """
    updated = await service.add_chapter(plan_id, payload, current_user)
    return success_response(data=updated, message="Chapter added successfully.")


# ===========================================================================
# Topic management
# ===========================================================================

@router.post(
    "/{plan_id}/chapters/{chapter_id}/topics",
    response_model=SuccessResponse[LessonPlanResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add a topic to a chapter",
)
async def add_topic(
    plan_id: str,
    chapter_id: str,
    payload: TopicCreate,
    current_user: Annotated[UserDocument, Depends(require_teacher)],
    service: Annotated[LessonPlanService, Depends(get_service)],
):
    """
    Append a new topic (with optional subtopics) to a chapter.

    **Example request:**
    ```json
    {
      "title": "Circular Linked List",
      "planned_hours": 1.5,
      "planned_date": "2026-06-10T09:00:00",
      "order": 3,
      "subtopics": [
        {"title": "Insertion in circular LL", "order": 1},
        {"title": "Deletion in circular LL", "order": 2}
      ]
    }
    ```
    """
    updated = await service.add_topic(plan_id, chapter_id, payload, current_user)
    return success_response(data=updated, message="Topic added successfully.")


# ===========================================================================
# Subtopic management
# ===========================================================================

@router.post(
    "/{plan_id}/chapters/{chapter_id}/topics/{topic_id}/subtopics",
    response_model=SuccessResponse[LessonPlanResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add a subtopic to a topic",
)
async def add_subtopic(
    plan_id: str,
    chapter_id: str,
    topic_id: str,
    payload: SubtopicCreate,
    current_user: Annotated[UserDocument, Depends(require_teacher)],
    service: Annotated[LessonPlanService, Depends(get_service)],
):
    """
    Append a subtopic to a topic.

    **Example request:**
    ```json
    {
      "title": "Time complexity of circular LL operations",
      "order": 3
    }
    ```
    """
    updated = await service.add_subtopic(plan_id, chapter_id, topic_id, payload, current_user)
    return success_response(data=updated, message="Subtopic added successfully.")

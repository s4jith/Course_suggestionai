
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

def get_service(db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]) -> LessonPlanService:
    return LessonPlanService(db)

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
    updated = await service.update_lesson_plan(plan_id, payload, current_user)
    return success_response(data=updated, message="Lesson plan updated successfully.")

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
    updated = await service.add_chapter(plan_id, payload, current_user)
    return success_response(data=updated, message="Chapter added successfully.")

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
    updated = await service.add_topic(plan_id, chapter_id, payload, current_user)
    return success_response(data=updated, message="Topic added successfully.")

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
    updated = await service.add_subtopic(plan_id, chapter_id, topic_id, payload, current_user)
    return success_response(data=updated, message="Subtopic added successfully.")

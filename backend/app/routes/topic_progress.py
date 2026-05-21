
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

def get_service(db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]) -> LessonPlanService:
    return LessonPlanService(db)

@router.get(
    "/",
    response_model=SuccessResponse[list[TopicProgressResponse]],
    status_code=status.HTTP_200_OK,
    summary="List all progress records for a lesson plan",
)
async def list_progress(
    lesson_plan_id: str = Query(..., description="Lesson plan ObjectId"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _: Annotated[UserDocument, Depends(get_current_active_user)] = None,
    service: Annotated[LessonPlanService, Depends(get_service)] = None,
):
    records = await service.list_progress_for_plan(lesson_plan_id, skip, limit)
    return success_response(data=records, message="Progress records retrieved.")

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
    result = await service.update_progress(progress_id, payload, current_user)
    return success_response(data=result, message="Progress updated successfully.")

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
    items = await service.get_faculty_progress(teacher_id, academic_year)
    return success_response(data=items, message="Faculty progress retrieved.")


from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_active_user, require_admin
from app.core.responses import SuccessResponse, success_response
from app.database.mongodb import get_database
from app.models.user import UserDocument
from app.schemas.analytics import (
    CompletionTrendResponse,
    DelayedTopicsResponse,
    FacultyAnalyticsResponse,
    HeatmapResponse,
    OverviewKPI,
    RiskScoresResponse,
    SubjectAnalyticsResponse,
    SyllabusCompletionResponse,
    TeachingMethodResponse,
    UnderstandingAnalyticsResponse,
)
from app.services.analytics_service import AnalyticsService, invalidate_cache

router = APIRouter(prefix="/analytics", tags=["Analytics"])

def get_service(db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]) -> AnalyticsService:
    return AnalyticsService(db)

@router.get(
    "/overview",
    response_model=SuccessResponse[OverviewKPI],
    summary="Overall analytics KPIs",
    description="Returns high-level metrics: completion %, at-risk plans, delayed topics, hours delivery rate.",
)
async def get_overview(
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[AnalyticsService, Depends(get_service)],
    academic_year: Optional[str] = Query(None, description="Filter by academic year e.g. 2025-2026"),
    semester: Optional[int] = Query(None, ge=1, le=10),
    department: Optional[str] = Query(None),
    teacher_id: Optional[str] = Query(None),
):
    data = await service.get_overview(
        academic_year=academic_year,
        semester=semester,
        department=department,
        teacher_id=teacher_id,
    )
    return success_response(data)

@router.get(
    "/syllabus-completion",
    response_model=SuccessResponse[SyllabusCompletionResponse],
    summary="Per lesson-plan syllabus completion",
    description="Returns completion % for each lesson plan — suitable for bar/line charts.",
)
async def get_syllabus_completion(
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[AnalyticsService, Depends(get_service)],
    academic_year: Optional[str] = Query(None),
    semester: Optional[int] = Query(None, ge=1, le=10),
    teacher_id: Optional[str] = Query(None),
    subject_id: Optional[str] = Query(None),
):
    data = await service.get_syllabus_completion(
        academic_year=academic_year,
        semester=semester,
        teacher_id=teacher_id,
        subject_id=subject_id,
    )
    return success_response(data)

@router.get(
    "/faculty",
    response_model=SuccessResponse[FacultyAnalyticsResponse],
    summary="Faculty-wise progress comparison",
    description="Returns aggregated progress per faculty member.",
)
async def get_faculty_analytics(
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[AnalyticsService, Depends(get_service)],
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
):
    data = await service.get_faculty_analytics(
        academic_year=academic_year,
        department=department,
    )
    return success_response(data)

@router.get(
    "/subjects",
    response_model=SuccessResponse[SubjectAnalyticsResponse],
    summary="Subject-wise completion breakdown",
    description="Returns completion metrics grouped by subject.",
)
async def get_subject_analytics(
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[AnalyticsService, Depends(get_service)],
    academic_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    semester: Optional[int] = Query(None, ge=1, le=10),
):
    data = await service.get_subject_analytics(
        academic_year=academic_year,
        department=department,
        semester=semester,
    )
    return success_response(data)

@router.get(
    "/delayed-topics",
    response_model=SuccessResponse[DelayedTopicsResponse],
    summary="Delayed / overdue topics",
    description="Topics past their planned date that are not yet completed or skipped.",
)
async def get_delayed_topics(
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[AnalyticsService, Depends(get_service)],
    academic_year: Optional[str] = Query(None),
    teacher_id: Optional[str] = Query(None),
):
    data = await service.get_delayed_topics(
        academic_year=academic_year,
        teacher_id=teacher_id,
    )
    return success_response(data)

@router.get(
    "/risk-scores",
    response_model=SuccessResponse[RiskScoresResponse],
    summary="Completion risk scores per lesson plan",
    description="Returns a risk score (0-100) and risk level for each lesson plan.",
)
async def get_risk_scores(
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[AnalyticsService, Depends(get_service)],
    academic_year: Optional[str] = Query(None),
    semester: Optional[int] = Query(None, ge=1, le=10),
    teacher_id: Optional[str] = Query(None),
):
    data = await service.get_risk_scores(
        academic_year=academic_year,
        semester=semester,
        teacher_id=teacher_id,
    )
    return success_response(data)

@router.get(
    "/teaching-methods",
    response_model=SuccessResponse[TeachingMethodResponse],
    summary="Teaching method effectiveness analysis",
    description="Returns effectiveness metrics per teaching method: completion %, understanding scores, usage count.",
)
async def get_teaching_method_effectiveness(
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[AnalyticsService, Depends(get_service)],
    academic_year: Optional[str] = Query(None),
    teacher_id: Optional[str] = Query(None),
):
    data = await service.get_teaching_method_effectiveness(
        academic_year=academic_year,
        teacher_id=teacher_id,
    )
    return success_response(data)

@router.get(
    "/understanding",
    response_model=SuccessResponse[UnderstandingAnalyticsResponse],
    summary="Student understanding level analytics",
    description="Returns distribution of understanding levels (excellent/good/average/poor) overall and per subject.",
)
async def get_understanding_analytics(
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[AnalyticsService, Depends(get_service)],
    academic_year: Optional[str] = Query(None),
    teacher_id: Optional[str] = Query(None),
):
    data = await service.get_understanding_analytics(
        academic_year=academic_year,
        teacher_id=teacher_id,
    )
    return success_response(data)

@router.get(
    "/completion-trend",
    response_model=SuccessResponse[CompletionTrendResponse],
    summary="Completion trend over time",
    description="Daily topic completion count for line/area charts. Default: last 30 days.",
)
async def get_completion_trend(
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[AnalyticsService, Depends(get_service)],
    days: int = Query(default=30, ge=7, le=365, description="Number of days to look back"),
    teacher_id: Optional[str] = Query(None),
):
    data = await service.get_completion_trend(days=days, teacher_id=teacher_id)
    return success_response(data)

@router.get(
    "/heatmap",
    response_model=SuccessResponse[HeatmapResponse],
    summary="Topic completion calendar heatmap",
    description="Returns daily completion counts with intensity buckets (0-4) for a calendar heatmap.",
)
async def get_heatmap(
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[AnalyticsService, Depends(get_service)],
    days: int = Query(default=90, ge=30, le=365),
    teacher_id: Optional[str] = Query(None),
):
    data = await service.get_heatmap(days=days, teacher_id=teacher_id)
    return success_response(data)

@router.post(
    "/invalidate-cache",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Invalidate analytics cache",
)
async def invalidate_analytics_cache(
    current_user: Annotated[UserDocument, Depends(require_admin)],
):
    invalidate_cache()
    return success_response({"message": "Analytics cache cleared"})

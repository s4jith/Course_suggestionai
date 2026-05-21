
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.ai_engine.services.ollama_service import ollama_service
from app.ai_engine.services.recommendation_service import RecommendationService
from app.auth.dependencies import get_current_active_user
from app.core.responses import success_response
from app.database.mongodb import get_database
from app.models.user import UserDocument

router = APIRouter(prefix="/ai", tags=["AI Recommendations"])

def get_recommendation_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> RecommendationService:
    return RecommendationService(db)

@router.get(
    "/health",
    summary="AI service health check",
    response_description="Ollama server status and configured model availability",
)
async def ai_health():
    status = await ollama_service.health_check()
    if status.get("model_loaded"):
        message = "AI service is ready."
    elif status.get("available"):
        message = f"Ollama is running but model '{status.get('model')}' is not loaded. Run: ollama pull {status.get('model')}"
    else:
        message = "Ollama is unavailable — recommendation endpoints will use rule-based fallback."
    return success_response(data=status, message=message)

@router.get(
    "/recommendations/{lesson_plan_id}",
    summary="Full AI recommendation report",
    response_description=(
        "Next topic, weak areas, risk score, timetable, method effectiveness, "
        "and LLM-generated insights"
    ),
)
async def get_full_recommendations(
    lesson_plan_id: str,
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[RecommendationService, Depends(get_recommendation_service)],
    teacher_id: Optional[str] = Query(
        None,
        description="Filter progress records by a specific teacher ID"
    ),
    include_llm: bool = Query(
        True,
        description="Set to false to skip Ollama and use deterministic rules only"
    ),
):
    result = await service.get_full_recommendations(
        lesson_plan_id=lesson_plan_id,
        teacher_id=teacher_id,
        include_llm=include_llm,
    )
    return success_response(
        data=result.model_dump(),
        message="AI recommendations generated successfully.",
    )

@router.get(
    "/risk/{lesson_plan_id}",
    summary="Lesson plan risk assessment",
    response_description="Risk score (0-100), factors, and LLM-generated narrative",
)
async def get_risk_assessment(
    lesson_plan_id: str,
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[RecommendationService, Depends(get_recommendation_service)],
    teacher_id: Optional[str] = Query(None),
    include_llm: bool = Query(True),
):
    result = await service.get_risk_assessment(
        lesson_plan_id=lesson_plan_id,
        teacher_id=teacher_id,
        include_llm=include_llm,
    )
    return success_response(data=result, message="Risk assessment completed.")

@router.get(
    "/next-topic/{lesson_plan_id}",
    summary="Recommended next topic to teach",
    response_description="Highest-priority pending topic with teaching guidance",
)
async def get_next_topic(
    lesson_plan_id: str,
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[RecommendationService, Depends(get_recommendation_service)],
    teacher_id: Optional[str] = Query(None),
    include_llm: bool = Query(True),
):
    result = await service.get_next_topic_recommendation(
        lesson_plan_id=lesson_plan_id,
        teacher_id=teacher_id,
        include_llm=include_llm,
    )
    return success_response(data=result, message="Next topic recommendation ready.")

@router.get(
    "/timetable/{lesson_plan_id}",
    summary="Smart timetable for remaining topics",
    response_description="Day-by-day schedule with teaching method for each pending topic",
)
async def get_timetable(
    lesson_plan_id: str,
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[RecommendationService, Depends(get_recommendation_service)],
    teacher_id: Optional[str] = Query(None),
    teaching_days_per_week: int = Query(
        5, ge=1, le=7,
        description="Number of teaching days per week (Mon-Fri = 5)"
    ),
    include_llm: bool = Query(True),
):
    result = await service.get_timetable_suggestions(
        lesson_plan_id=lesson_plan_id,
        teacher_id=teacher_id,
        teaching_days_per_week=teaching_days_per_week,
        include_llm=include_llm,
    )
    return success_response(data=result, message="Timetable generated successfully.")

@router.get(
    "/weak-areas/{lesson_plan_id}",
    summary="Topics needing revision",
    response_description="Completed topics with low student understanding + revision strategies",
)
async def get_weak_areas(
    lesson_plan_id: str,
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[RecommendationService, Depends(get_recommendation_service)],
    teacher_id: Optional[str] = Query(None),
    include_llm: bool = Query(True),
):
    result = await service.get_weak_areas(
        lesson_plan_id=lesson_plan_id,
        teacher_id=teacher_id,
        include_llm=include_llm,
    )
    return success_response(
        data=result,
        message=f"{result['total_weak_topics']} topic(s) flagged for revision.",
    )

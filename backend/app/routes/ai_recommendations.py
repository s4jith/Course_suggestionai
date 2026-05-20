"""
AI Recommendations API Routes.

All endpoints live under /api/v1/ai/.

Endpoint summary:
  GET  /api/v1/ai/health                       Ollama server health check
  GET  /api/v1/ai/recommendations/{plan_id}    Full AI recommendation report
  GET  /api/v1/ai/risk/{plan_id}               Risk assessment + LLM narrative
  GET  /api/v1/ai/next-topic/{plan_id}         Next topic recommendation + guidance
  GET  /api/v1/ai/timetable/{plan_id}          Smart timetable for pending topics
  GET  /api/v1/ai/weak-areas/{plan_id}         Topics needing revision + strategies
"""

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


# ---------------------------------------------------------------------------
# Dependency factory
# ---------------------------------------------------------------------------

def get_recommendation_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> RecommendationService:
    return RecommendationService(db)


# ---------------------------------------------------------------------------
# Health check (no auth required — useful for infra probes)
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    summary="AI service health check",
    response_description="Ollama server status and configured model availability",
)
async def ai_health():
    """
    Check whether the Ollama server is reachable and the configured model
    (mistral:7b by default) is available.

    Returns availability status, model list, and any error message.
    Use this endpoint to verify the AI integration before running recommendations.

    If the model is not loaded, set `include_llm=false` on recommendation endpoints
    to use the rule-based fallback until Ollama is ready.
    """
    status = await ollama_service.health_check()
    if status.get("model_loaded"):
        message = "AI service is ready."
    elif status.get("available"):
        message = f"Ollama is running but model '{status.get('model')}' is not loaded. Run: ollama pull {status.get('model')}"
    else:
        message = "Ollama is unavailable — recommendation endpoints will use rule-based fallback."
    return success_response(data=status, message=message)


# ---------------------------------------------------------------------------
# Full recommendation report
# ---------------------------------------------------------------------------

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
    """
    Generate a comprehensive AI-powered recommendation report for a lesson plan.

    **Analysis inputs:**
    - Remaining syllabus (pending and in-progress topics)
    - Teaching velocity (completed topics per week)
    - Teaching method effectiveness (avg student understanding per method)
    - Planned dates vs actual progress (delay detection)
    - Student comprehension history (understanding level per completed topic)

    **Report outputs:**
    - `next_topic`: highest-priority topic to teach with suggested method
    - `weak_areas`: completed topics with poor/average understanding needing revision
    - `risk_assessment`: composite risk score (0-100) with factors and mitigations
    - `timetable_suggestions`: day-by-day schedule for remaining topics
    - `method_effectiveness`: ranked effectiveness of each teaching method used
    - `llm_insights`: structured JSON output from Ollama for each analysis area
    - `ai_summary`: LLM-generated narrative progress summary
    - `fallback_mode`: true when Ollama was unavailable (rules-only output)
    """
    result = await service.get_full_recommendations(
        lesson_plan_id=lesson_plan_id,
        teacher_id=teacher_id,
        include_llm=include_llm,
    )
    return success_response(
        data=result.model_dump(),
        message="AI recommendations generated successfully.",
    )


# ---------------------------------------------------------------------------
# Risk assessment
# ---------------------------------------------------------------------------

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
    """
    Compute a risk score (0–100) and generate a risk narrative for the lesson plan.

    **Risk score composition:**
    - 40% — Delay factor: proportion of topics past their planned date
    - 35% — Incompletion factor: proportion of topics still pending
    - 25% — Hours deficit: fraction of planned hours not yet delivered

    **Risk levels:**
    - LOW (0–25): Plan is progressing well
    - MEDIUM (26–50): Some delays, monitor closely
    - HIGH (51–75): Significant backlog, intervention needed
    - CRITICAL (76–100): Plan is severely behind, escalate to department

    When `include_llm=true`, Ollama generates an executive summary, key concerns,
    immediate actions, and a long-term strategy recommendation.
    """
    result = await service.get_risk_assessment(
        lesson_plan_id=lesson_plan_id,
        teacher_id=teacher_id,
        include_llm=include_llm,
    )
    return success_response(data=result, message="Risk assessment completed.")


# ---------------------------------------------------------------------------
# Next topic recommendation
# ---------------------------------------------------------------------------

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
    """
    Identify the highest-priority pending topic and recommend how to teach it.

    **Priority scoring:**
    - Overdue topics are heavily favoured (40 points per overdue day)
    - Topics previously taught with low comprehension get a 20-point boost
    - Earlier topics in chapter sequence get a slight ordering bonus

    **LLM output (when `include_llm=true`):**
    - `recommendation_reason`: why this topic is the top priority
    - `teaching_guidance`: step-by-step delivery instructions
    - `preparation_tips`: what to prepare before the session
    - `estimated_duration_note`: time allocation advice
    - `student_engagement_tips`: strategies to improve participation
    """
    result = await service.get_next_topic_recommendation(
        lesson_plan_id=lesson_plan_id,
        teacher_id=teacher_id,
        include_llm=include_llm,
    )
    return success_response(data=result, message="Next topic recommendation ready.")


# ---------------------------------------------------------------------------
# Smart timetable
# ---------------------------------------------------------------------------

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
    """
    Generate a day-by-day timetable for all remaining pending topics.

    Scheduling logic:
    - Overdue topics appear first (sorted by days overdue descending)
    - Topics within the same urgency tier follow chapter/topic order
    - Each slot is assigned to the next available teaching day
    - Teaching method is selected using historical effectiveness data

    Returns up to 20 scheduled slots.

    When `include_llm=true`, Ollama provides schedule quality insights,
    optimisation suggestions, a weekly goal, and the main scheduling risk to watch.
    """
    result = await service.get_timetable_suggestions(
        lesson_plan_id=lesson_plan_id,
        teacher_id=teacher_id,
        teaching_days_per_week=teaching_days_per_week,
        include_llm=include_llm,
    )
    return success_response(data=result, message="Timetable generated successfully.")


# ---------------------------------------------------------------------------
# Weak areas
# ---------------------------------------------------------------------------

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
    """
    Identify completed topics where student understanding was rated Poor or Average.

    Returns a sorted list (worst-first) of topics that need revision, with
    rule-based suggested revision approaches for each.

    When `include_llm=true`, Ollama generates:
    - `overall_diagnosis`: why these topics are challenging
    - `revision_plan`: topic-specific revision strategies
    - `general_improvement_tips`: classroom-level improvement suggestions
    """
    result = await service.get_weak_areas(
        lesson_plan_id=lesson_plan_id,
        teacher_id=teacher_id,
        include_llm=include_llm,
    )
    return success_response(
        data=result,
        message=f"{result['total_weak_topics']} topic(s) flagged for revision.",
    )

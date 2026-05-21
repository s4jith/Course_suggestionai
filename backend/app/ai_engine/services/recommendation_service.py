
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.ai_engine.inference.risk_analyzer import RiskReport, compute_risk
from app.ai_engine.prompts.templates import (
    next_topic_prompt,
    risk_explanation_prompt,
    summary_insights_prompt,
    timetable_prompt,
    weak_areas_prompt,
)
from app.ai_engine.rules.engine import (
    forecast_completion,
    get_next_topic,
    get_priority_score,
    get_weak_areas,
    recommend_teaching_method,
    suggest_timetable,
)
from app.ai_engine.services.ollama_service import ollama_service
from app.ai_engine.utils.data_extractor import PlanContext, TopicSnapshot, build_plan_context
from app.core.exceptions import NotFoundException
from app.models.lesson_plan import TeachingMethod, UnderstandingLevel
from app.repositories.lesson_plan_repository import LessonPlanRepository
from app.repositories.subject_repository import SubjectRepository
from app.repositories.topic_progress_repository import TopicProgressRepository
from app.schemas.ai import (
    AIRecommendationResponse,
    MethodEffectivenessItem,
    NextTopicRecommendation,
    RiskAssessment,
    RiskLevel,
    TimetableEntry,
    WeakAreaAlert,
)

logger = logging.getLogger(__name__)

_RISK_LEVEL_MAP = {
    "low": RiskLevel.LOW,
    "medium": RiskLevel.MEDIUM,
    "high": RiskLevel.HIGH,
    "critical": RiskLevel.CRITICAL,
}

class RecommendationService:

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._plan_repo = LessonPlanRepository(db)
        self._subject_repo = SubjectRepository(db)
        self._progress_repo = TopicProgressRepository(db)

    async def get_full_recommendations(
        self,
        lesson_plan_id: str,
        teacher_id: Optional[str] = None,
        include_llm: bool = True,
    ) -> AIRecommendationResponse:
        ctx = await self._build_context(lesson_plan_id, teacher_id)

        next_snap = get_next_topic(ctx)
        weak_snaps = get_weak_areas(ctx)
        risk_report = compute_risk(ctx)
        timetable_raw = suggest_timetable(ctx)
        forecast = forecast_completion(ctx)

        next_topic_rec = self._build_next_topic_rec(ctx, next_snap)
        weak_alerts = self._build_weak_alerts(weak_snaps)
        risk_assessment = self._build_risk_assessment(risk_report, forecast)
        timetable = self._build_timetable(timetable_raw)
        method_eff = self._build_method_effectiveness(ctx)

        llm_insights: Optional[dict] = None
        ai_summary: Optional[str] = None
        fallback_mode = not include_llm

        if include_llm:
            llm_insights, ai_summary, had_failures = await self._enrich_with_llm(
                ctx=ctx,
                next_snap=next_snap,
                next_topic_rec=next_topic_rec,
                risk_report=risk_report,
                timetable_raw=timetable_raw,
                forecast=forecast,
                weak_snaps=weak_snaps,
            )
            fallback_mode = had_failures and llm_insights is None

        return AIRecommendationResponse(
            lesson_plan_id=lesson_plan_id,
            generated_at=datetime.now(tz=timezone.utc),
            next_topic=next_topic_rec,
            weak_areas=weak_alerts,
            risk_assessment=risk_assessment,
            timetable_suggestions=timetable,
            method_effectiveness=method_eff,
            llm_insights=llm_insights,
            ai_summary=ai_summary,
            fallback_mode=fallback_mode,
        )

    async def get_risk_assessment(
        self,
        lesson_plan_id: str,
        teacher_id: Optional[str] = None,
        include_llm: bool = True,
    ) -> dict:
        ctx = await self._build_context(lesson_plan_id, teacher_id)
        risk_report = compute_risk(ctx)
        forecast = forecast_completion(ctx)
        assessment = self._build_risk_assessment(risk_report, forecast)

        llm_narrative = None
        if include_llm:
            prompt = risk_explanation_prompt(ctx, risk_report)
            llm_narrative = await ollama_service.generate(prompt)

        return {
            "risk_assessment": assessment.model_dump(),
            "forecast": forecast,
            "llm_narrative": llm_narrative,
            "fallback_mode": llm_narrative is None,
        }

    async def get_next_topic_recommendation(
        self,
        lesson_plan_id: str,
        teacher_id: Optional[str] = None,
        include_llm: bool = True,
    ) -> dict:
        ctx = await self._build_context(lesson_plan_id, teacher_id)
        snap = get_next_topic(ctx)
        rec = self._build_next_topic_rec(ctx, snap)

        llm_guidance = None
        if include_llm and snap is not None:
            method = recommend_teaching_method(snap.topic_title, ctx)
            score = get_priority_score(snap)
            prompt = next_topic_prompt(
                ctx=ctx,
                next_topic_title=snap.topic_title,
                chapter_title=snap.chapter_title,
                suggested_method=method.value,
                priority_score=score,
            )
            llm_guidance = await ollama_service.generate(prompt)

        return {
            "next_topic": rec.model_dump() if rec else None,
            "llm_guidance": llm_guidance,
            "fallback_mode": llm_guidance is None,
        }

    async def get_timetable_suggestions(
        self,
        lesson_plan_id: str,
        teacher_id: Optional[str] = None,
        teaching_days_per_week: int = 5,
        include_llm: bool = True,
    ) -> dict:
        ctx = await self._build_context(lesson_plan_id, teacher_id)
        timetable_raw = suggest_timetable(ctx, teaching_days_per_week)
        timetable = self._build_timetable(timetable_raw)

        llm_analysis = None
        if include_llm:
            prompt = timetable_prompt(ctx, timetable_raw)
            llm_analysis = await ollama_service.generate(prompt)

        return {
            "timetable": [t.model_dump() for t in timetable],
            "llm_analysis": llm_analysis,
            "total_slots": len(timetable),
            "pending_topics": ctx.pending_topics + ctx.in_progress_topics,
            "fallback_mode": llm_analysis is None,
        }

    async def get_weak_areas(
        self,
        lesson_plan_id: str,
        teacher_id: Optional[str] = None,
        include_llm: bool = True,
    ) -> dict:
        ctx = await self._build_context(lesson_plan_id, teacher_id)
        weak_snaps = get_weak_areas(ctx)
        alerts = self._build_weak_alerts(weak_snaps)

        llm_strategies = None
        if include_llm and weak_snaps:
            prompt = weak_areas_prompt(ctx, [s.topic_title for s in weak_snaps])
            llm_strategies = await ollama_service.generate(prompt)

        return {
            "weak_areas": [a.model_dump() for a in alerts],
            "total_weak_topics": len(alerts),
            "llm_strategies": llm_strategies,
            "fallback_mode": llm_strategies is None,
        }

    async def _build_context(
        self,
        lesson_plan_id: str,
        teacher_id: Optional[str],
    ) -> PlanContext:
        plan = await self._plan_repo.find_by_id(lesson_plan_id)
        if plan is None:
            raise NotFoundException("LessonPlan")

        subject = await self._subject_repo.find_by_id(plan.subject_id)
        subject_name = subject.name if subject else "Unknown Subject"

        progress_records = await self._progress_repo.list_for_plan(
            lesson_plan_id=lesson_plan_id,
            limit=500,
        )
        if teacher_id:
            progress_records = [p for p in progress_records if p.teacher_id == teacher_id]

        return build_plan_context(plan, subject_name, progress_records)

    def _build_next_topic_rec(
        self,
        ctx: PlanContext,
        snap: Optional[TopicSnapshot],
    ) -> Optional[NextTopicRecommendation]:
        if snap is None:
            return None

        method = recommend_teaching_method(snap.topic_title, ctx)
        score = get_priority_score(snap)

        if snap.is_delayed:
            reason = (
                f"This topic is overdue by {snap.days_overdue} day(s) and is the "
                f"highest-priority pending item in chapter '{snap.chapter_title}'."
            )
        else:
            reason = (
                f"This is the next topic in sequence for chapter '{snap.chapter_title}' "
                f"and has no blockers."
            )

        return NextTopicRecommendation(
            topic_id=snap.topic_id,
            topic_title=snap.topic_title,
            chapter_title=snap.chapter_title,
            priority_score=score,
            reason=reason,
            suggested_method=method,
            estimated_hours=snap.planned_hours,
            is_delayed=snap.is_delayed,
            days_overdue=snap.days_overdue,
        )

    def _build_weak_alerts(self, snaps: List[TopicSnapshot]) -> List[WeakAreaAlert]:
        alerts = []
        for snap in snaps:
            if snap.understanding_level == UnderstandingLevel.POOR:
                approach = (
                    "Re-teach using a practical or video-based method to reinforce "
                    "understanding from the ground up."
                )
            else:
                approach = (
                    "Schedule a focused 30-minute revision session with targeted Q&A "
                    "to consolidate partial understanding."
                )
            alerts.append(WeakAreaAlert(
                topic_id=snap.topic_id,
                topic_title=snap.topic_title,
                chapter_title=snap.chapter_title,
                understanding_level=snap.understanding_level,
                last_taught=snap.actual_date,
                revision_recommended=True,
                suggested_approach=approach,
                issues=snap.issues,
            ))
        return alerts

    def _build_risk_assessment(
        self,
        risk: RiskReport,
        forecast: dict,
    ) -> RiskAssessment:
        return RiskAssessment(
            risk_score=risk.risk_score,
            risk_level=_RISK_LEVEL_MAP.get(risk.risk_level, RiskLevel.MEDIUM),
            completion_percentage=risk.completion_percentage,
            delayed_topics_count=risk.delayed_topics_count,
            hours_behind=risk.hours_behind,
            predicted_completion_date=risk.predicted_completion_date,
            delay_days=risk.delay_days,
            is_on_track=risk.is_on_track,
            topics_per_week=forecast.get("topics_per_week", 0.0),
            weeks_remaining=forecast.get("weeks_remaining"),
            risk_factors=risk.risk_factors,
            mitigation_suggestions=risk.mitigation_suggestions,
        )

    def _build_timetable(self, raw: List[dict]) -> List[TimetableEntry]:
        entries = []
        for slot in raw:
            try:
                method = TeachingMethod(slot["teaching_method"])
            except ValueError:
                method = TeachingMethod.THEORETICAL
            entries.append(TimetableEntry(
                slot=slot["slot"],
                date=slot["date"],
                day_of_week=slot["day_of_week"],
                topic_id=slot["topic_id"],
                topic_title=slot["topic_title"],
                chapter_title=slot["chapter_title"],
                suggested_hours=slot["suggested_hours"],
                teaching_method=method,
            ))
        return entries

    def _build_method_effectiveness(self, ctx: PlanContext) -> List[MethodEffectivenessItem]:
        items = []
        for method_str, avg_score in ctx.method_effectiveness.items():
            try:
                method = TeachingMethod(method_str)
            except ValueError:
                continue
            usage = ctx.method_usage_count.get(method_str, 0)
            if avg_score >= 2.5:
                label = "Highly Effective"
            elif avg_score >= 1.5:
                label = "Effective"
            elif avg_score >= 0.5:
                label = "Moderately Effective"
            else:
                label = "Low Effectiveness"
            items.append(MethodEffectivenessItem(
                method=method,
                avg_understanding_score=round(avg_score, 2),
                usage_count=usage,
                effectiveness_label=label,
            ))
        return sorted(items, key=lambda x: x.avg_understanding_score, reverse=True)

    async def _enrich_with_llm(
        self,
        ctx: PlanContext,
        next_snap: Optional[TopicSnapshot],
        next_topic_rec: Optional[NextTopicRecommendation],
        risk_report: RiskReport,
        timetable_raw: List[dict],
        forecast: dict,
        weak_snaps: List[TopicSnapshot],
    ) -> Tuple[Optional[dict], Optional[str], bool]:
        llm_insights: dict = {}
        had_failures = False

        summary_data = await ollama_service.generate(
            summary_insights_prompt(ctx, risk_report, forecast)
        )
        ai_summary: Optional[str] = None
        if summary_data:
            llm_insights["summary"] = summary_data
            ai_summary = summary_data.get("progress_narrative")
        else:
            had_failures = True
            logger.debug("LLM: summary insights call returned None for plan %s", ctx.plan_id)

        if next_snap is not None and next_topic_rec is not None:
            method = recommend_teaching_method(next_snap.topic_title, ctx)
            nt_data = await ollama_service.generate(
                next_topic_prompt(
                    ctx=ctx,
                    next_topic_title=next_snap.topic_title,
                    chapter_title=next_snap.chapter_title,
                    suggested_method=method.value,
                    priority_score=get_priority_score(next_snap),
                )
            )
            if nt_data:
                llm_insights["next_topic"] = nt_data
                if nt_data.get("recommendation_reason"):
                    next_topic_rec.reason = nt_data["recommendation_reason"]
            else:
                had_failures = True

        if weak_snaps:
            wa_data = await ollama_service.generate(
                weak_areas_prompt(ctx, [s.topic_title for s in weak_snaps])
            )
            if wa_data:
                llm_insights["weak_areas"] = wa_data
            else:
                had_failures = True

        tt_data = await ollama_service.generate(timetable_prompt(ctx, timetable_raw))
        if tt_data:
            llm_insights["timetable"] = tt_data
        else:
            had_failures = True

        risk_data = await ollama_service.generate(risk_explanation_prompt(ctx, risk_report))
        if risk_data:
            llm_insights["risk"] = risk_data
        else:
            had_failures = True

        return (llm_insights or None), ai_summary, had_failures

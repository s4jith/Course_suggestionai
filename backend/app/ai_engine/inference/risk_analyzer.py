"""
Risk Analyzer – deterministic completion-risk scoring for a lesson plan.

The risk score (0–100) is a weighted composite of three independent factors:

  Factor 1 — Delay factor (weight 40%):
      Proportion of all topics that are past their planned date and
      not yet completed.

  Factor 2 — Incompletion factor (weight 35%):
      Proportion of topics still pending or in-progress relative to
      total topics.

  Factor 3 — Hours-deficit factor (weight 25%):
      Fraction of planned teaching hours that have not yet been delivered.

Risk levels:
  0 – 25   → LOW
  26 – 50  → MEDIUM
  51 – 75  → HIGH
  76 – 100 → CRITICAL
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.ai_engine.utils.data_extractor import PlanContext
from app.ai_engine.rules.engine import forecast_completion
from app.models.lesson_plan import UnderstandingLevel


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RiskReport:
    """Full risk assessment for a single lesson plan."""

    plan_id: str
    risk_score: float           # 0–100 (higher = worse)
    risk_level: str             # "low" | "medium" | "high" | "critical"
    completion_percentage: float
    delayed_topics_count: int
    hours_behind: float
    predicted_completion_date: Optional[str]
    delay_days: int             # estimated extra days beyond a 20-week semester
    is_on_track: bool
    risk_factors: List[str]          # human-readable causes
    mitigation_suggestions: List[str]  # actionable fixes


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _risk_level(score: float) -> str:
    if score <= 25.0:
        return "low"
    if score <= 50.0:
        return "medium"
    if score <= 75.0:
        return "high"
    return "critical"


def _delay_days(forecast: dict) -> int:
    """Estimate extra days beyond a 20-week semester baseline."""
    weeks_remaining = forecast.get("weeks_remaining")
    if weeks_remaining is None:
        return 0
    excess_weeks = max(0.0, weeks_remaining - 20.0)
    return int(excess_weeks * 7)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_risk(ctx: PlanContext) -> RiskReport:
    """
    Compute a comprehensive risk report for a lesson plan.

    Args:
        ctx: A `PlanContext` built by `data_extractor.build_plan_context()`.

    Returns:
        `RiskReport` with score, level, risk factors, and mitigation suggestions.
    """
    total = ctx.total_topics or 1  # guard against empty plans

    # -----------------------------------------------------------------------
    # Factor 1: Delay factor — proportion of topics past their planned date
    # -----------------------------------------------------------------------
    delay_factor = ctx.delayed_topics / total

    # -----------------------------------------------------------------------
    # Factor 2: Incompletion factor — proportion of topics not yet done
    # -----------------------------------------------------------------------
    incomplete = ctx.pending_topics + ctx.in_progress_topics
    incompletion_factor = incomplete / total

    # -----------------------------------------------------------------------
    # Factor 3: Hours-deficit factor — fraction of hours not yet delivered
    # -----------------------------------------------------------------------
    hours_planned = ctx.total_planned_hours or 1.0
    hours_behind = max(0.0, hours_planned - ctx.total_hours_delivered)
    hours_deficit_factor = min(1.0, hours_behind / hours_planned)

    # -----------------------------------------------------------------------
    # Weighted composite (weights sum to 1.0)
    # -----------------------------------------------------------------------
    raw_score = (
        0.40 * delay_factor
        + 0.35 * incompletion_factor
        + 0.25 * hours_deficit_factor
    )
    risk_score = round(min(100.0, raw_score * 100), 1)
    level = _risk_level(risk_score)

    # -----------------------------------------------------------------------
    # Completion forecast
    # -----------------------------------------------------------------------
    forecast = forecast_completion(ctx)
    predicted_date = forecast.get("estimated_completion_date")
    extra_days = _delay_days(forecast)

    # -----------------------------------------------------------------------
    # Build human-readable risk factor descriptions
    # -----------------------------------------------------------------------
    factors: List[str] = []

    if delay_factor >= 0.5:
        factors.append(
            f"{ctx.delayed_topics} of {total} topics are past their planned date — critical backlog."
        )
    elif delay_factor > 0:
        factors.append(
            f"{ctx.delayed_topics} topic(s) have passed their planned date without completion."
        )

    if incompletion_factor >= 0.75:
        factors.append(
            f"Only {ctx.completed_topics}/{total} topics completed — significant syllabus remaining."
        )
    elif incompletion_factor > 0:
        factors.append(
            f"{incomplete} topic(s) still pending or in progress."
        )

    if hours_deficit_factor >= 0.5:
        factors.append(
            f"Hours delivered ({ctx.total_hours_delivered:.1f}h) is far below planned "
            f"({ctx.total_planned_hours:.1f}h) — {hours_behind:.1f}h deficit."
        )
    elif hours_deficit_factor > 0.1:
        factors.append(
            f"{hours_behind:.1f} teaching hours behind schedule."
        )

    poor_topics = [
        t for t in ctx.topics
        if t.understanding_level == UnderstandingLevel.POOR
    ]
    if poor_topics:
        factors.append(
            f"{len(poor_topics)} topic(s) have 'Poor' student understanding — revision required."
        )

    if ctx.avg_understanding_score < 1.5 and ctx.completed_topics > 0:
        factors.append(
            "Average student understanding is below 'Average' — teaching approach may need adjustment."
        )

    if not factors:
        factors.append("No significant risk factors detected — plan is progressing well.")

    # -----------------------------------------------------------------------
    # Build mitigation suggestions
    # -----------------------------------------------------------------------
    mitigations: List[str] = []

    if delay_factor > 0:
        mitigations.append(
            "Schedule catch-up sessions for delayed topics; consider combining related concepts in one session."
        )
    if ctx.avg_understanding_score < 1.5 and ctx.completed_topics > 0:
        mitigations.append(
            "Switch to practical or visual teaching methods for topics with low comprehension rates."
        )
    if hours_deficit_factor > 0.25:
        mitigations.append(
            "Extend class duration or add extra sessions this week to recover lost teaching hours."
        )
    if poor_topics:
        mitigations.append(
            "Re-teach poorly understood topics using a different method before advancing to new material."
        )
    if level in ("high", "critical"):
        mitigations.append(
            "Discuss timeline with the department — adjust lesson plan deadlines to reflect current pace."
        )
    if not mitigations:
        mitigations.append("Continue the current pace — the lesson plan is on track.")

    return RiskReport(
        plan_id=ctx.plan_id,
        risk_score=risk_score,
        risk_level=level,
        completion_percentage=round(ctx.completion_percentage, 1),
        delayed_topics_count=ctx.delayed_topics,
        hours_behind=round(hours_behind, 1),
        predicted_completion_date=predicted_date,
        delay_days=extra_days,
        is_on_track=forecast.get("is_on_track", False),
        risk_factors=factors,
        mitigation_suggestions=mitigations,
    )

"""
Prompt Templates – structured prompt builders for all Ollama interactions.

Design principles:
  - Each builder is a plain function returning a str (no Jinja2 dependency).
  - Every prompt embeds a JSON schema spec so Ollama knows the exact output shape.
  - Prompts include the SYSTEM_HEADER for consistent academic context.
  - Temperature 0.15 is recommended for deterministic structured output.
  - All prompts instruct the model NOT to use markdown fencing.

Each prompt corresponds to one analytical task:
  next_topic_prompt       → teaching guidance for the recommended next topic
  weak_areas_prompt       → revision strategies for low-comprehension topics
  timetable_prompt        → schedule quality analysis and optimisation tips
  risk_explanation_prompt → narrative risk report with immediate actions
  summary_insights_prompt → holistic semester progress analysis
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.ai_engine.inference.risk_analyzer import RiskReport
from app.ai_engine.utils.data_extractor import PlanContext


# ---------------------------------------------------------------------------
# Shared system header
# ---------------------------------------------------------------------------

_SYSTEM_HEADER = (
    "You are an expert academic teaching assistant AI integrated into a college "
    "lesson plan management system. Your role is to analyze teaching progress data "
    "and provide structured, actionable recommendations to help faculty improve "
    "student outcomes.\n\n"
    "IMPORTANT: Respond with valid JSON only. Do NOT include markdown fences, "
    "backticks, or any prose outside the JSON object. "
    "All string values must be concise, specific, and grounded in the data provided.\n\n"
)


# ---------------------------------------------------------------------------
# Helper: understanding score → label
# ---------------------------------------------------------------------------

def _understanding_label(score: float) -> str:
    if score >= 2.5:
        return "Excellent"
    if score >= 1.5:
        return "Good"
    if score >= 0.5:
        return "Average"
    return "Poor"


# ---------------------------------------------------------------------------
# 1. Next topic recommendation prompt
# ---------------------------------------------------------------------------

def next_topic_prompt(
    ctx: PlanContext,
    next_topic_title: str,
    chapter_title: str,
    suggested_method: str,
    priority_score: float,
) -> str:
    """
    Build a prompt for the LLM to explain and enrich the next-topic recommendation.

    Expected JSON response shape:
    {
      "recommendation_reason": "string",
      "teaching_guidance": "string",
      "preparation_tips": ["string", ...],
      "estimated_duration_note": "string",
      "student_engagement_tips": ["string", ...]
    }
    """
    pending_count = ctx.pending_topics + ctx.in_progress_topics
    understanding_label = _understanding_label(ctx.avg_understanding_score)

    return (
        f"{_SYSTEM_HEADER}"
        f"LESSON PLAN CONTEXT:\n"
        f"- Subject: {ctx.subject_name}\n"
        f"- Academic Year: {ctx.academic_year}, Semester: {ctx.semester}\n"
        f"- Total Topics: {ctx.total_topics} | Completed: {ctx.completed_topics} "
        f"({ctx.completion_percentage:.1f}%) | Pending: {pending_count}\n"
        f"- Delayed Topics: {ctx.delayed_topics}\n"
        f"- Average Student Understanding: {understanding_label}\n"
        f"- Hours Delivered / Planned: {ctx.total_hours_delivered:.1f}h / "
        f"{ctx.total_planned_hours:.1f}h\n"
        f"- Current Date: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}\n\n"
        f"RECOMMENDED NEXT TOPIC:\n"
        f"- Chapter: {chapter_title}\n"
        f"- Topic: {next_topic_title}\n"
        f"- Suggested Teaching Method: {suggested_method}\n"
        f"- Priority Score: {priority_score:.1f}\n\n"
        f"Based on this data, respond with exactly this JSON structure:\n"
        f'{{\n'
        f'  "recommendation_reason": "<1-2 sentences explaining why this topic is the top priority now>",\n'
        f'  "teaching_guidance": "<concrete step-by-step instructions for delivering this topic effectively>",\n'
        f'  "preparation_tips": ["<tip 1>", "<tip 2>", "<tip 3>"],\n'
        f'  "estimated_duration_note": "<comment on appropriate time allocation for this topic>",\n'
        f'  "student_engagement_tips": ["<engagement strategy 1>", "<engagement strategy 2>"]\n'
        f'}}'
    )


# ---------------------------------------------------------------------------
# 2. Weak areas revision prompt
# ---------------------------------------------------------------------------

def weak_areas_prompt(
    ctx: PlanContext,
    weak_topic_titles: List[str],
) -> str:
    """
    Build a prompt for the LLM to suggest revision strategies for poorly
    understood topics.

    Expected JSON response shape:
    {
      "overall_diagnosis": "string",
      "revision_plan": [
        {"topic": "string", "strategy": "string", "suggested_method": "string"}
      ],
      "general_improvement_tips": ["string", ...]
    }
    """
    if weak_topic_titles:
        weak_list = "\n".join(f"  - {t}" for t in weak_topic_titles)
    else:
        weak_list = "  None identified."

    understanding_label = _understanding_label(ctx.avg_understanding_score)

    return (
        f"{_SYSTEM_HEADER}"
        f"LESSON PLAN CONTEXT:\n"
        f"- Subject: {ctx.subject_name}\n"
        f"- Completion: {ctx.completed_topics}/{ctx.total_topics} topics "
        f"({ctx.completion_percentage:.1f}%)\n"
        f"- Average Student Understanding: {understanding_label} "
        f"({ctx.avg_understanding_score:.2f}/3)\n\n"
        f"TOPICS WITH LOW STUDENT UNDERSTANDING:\n"
        f"{weak_list}\n\n"
        f"Provide revision strategies in exactly this JSON structure:\n"
        f'{{\n'
        f'  "overall_diagnosis": "<brief assessment of why these topics are challenging for students>",\n'
        f'  "revision_plan": [\n'
        f'    {{\n'
        f'      "topic": "<topic name>",\n'
        f'      "strategy": "<specific, actionable revision approach for this exact topic>",\n'
        f'      "suggested_method": "<one of: theoretical/practical/ppt/seminar/lab/assignment/discussion/case_study/video_based>"\n'
        f'    }}\n'
        f'  ],\n'
        f'  "general_improvement_tips": ["<classroom improvement tip 1>", "<tip 2>", "<tip 3>"]\n'
        f'}}'
    )


# ---------------------------------------------------------------------------
# 3. Timetable analysis prompt
# ---------------------------------------------------------------------------

def timetable_prompt(
    ctx: PlanContext,
    rule_timetable: List[Dict[str, Any]],
) -> str:
    """
    Build a prompt for the LLM to evaluate and optimise the rule-generated timetable.

    Expected JSON response shape:
    {
      "schedule_insights": "string",
      "optimizations": ["string", ...],
      "weekly_goal": "string",
      "risk_note": "string"
    }
    """
    if rule_timetable:
        # Show first 7 slots for context, serialise dates as strings
        preview_slots = rule_timetable[:7]
        schedule_preview = json.dumps(preview_slots, indent=2, default=str)
    else:
        schedule_preview = "No topics scheduled (no pending topics)."

    return (
        f"{_SYSTEM_HEADER}"
        f"LESSON PLAN CONTEXT:\n"
        f"- Subject: {ctx.subject_name}\n"
        f"- Pending / In-Progress Topics: {ctx.pending_topics + ctx.in_progress_topics}\n"
        f"- Delayed Topics: {ctx.delayed_topics}\n"
        f"- Completion: {ctx.completion_percentage:.1f}%\n"
        f"- Topics Completed So Far: {ctx.completed_topics}\n\n"
        f"PROPOSED SCHEDULE (first 7 slots, generated by rule engine):\n"
        f"{schedule_preview}\n\n"
        f"Analyze this timetable and respond with exactly this JSON:\n"
        f'{{\n'
        f'  "schedule_insights": "<overall assessment of the proposed schedule quality and feasibility>",\n'
        f'  "optimizations": ["<specific optimisation 1>", "<optimisation 2>", "<optimisation 3>"],\n'
        f'  "weekly_goal": "<recommended number of topics to target per week to complete on time>",\n'
        f'  "risk_note": "<the single most important scheduling risk to monitor>"\n'
        f'}}'
    )


# ---------------------------------------------------------------------------
# 4. Risk explanation prompt
# ---------------------------------------------------------------------------

def risk_explanation_prompt(
    ctx: PlanContext,
    risk: RiskReport,
) -> str:
    """
    Build a prompt for the LLM to generate a narrative risk report.

    Expected JSON response shape:
    {
      "executive_summary": "string",
      "key_concerns": ["string", ...],
      "immediate_actions": ["string", ...],
      "long_term_strategy": "string"
    }
    """
    factors_list = "\n".join(f"  - {f}" for f in risk.risk_factors)
    mitigations_list = "\n".join(f"  - {m}" for m in risk.mitigation_suggestions)

    return (
        f"{_SYSTEM_HEADER}"
        f"RISK ASSESSMENT FOR: {ctx.subject_name}\n"
        f"- Risk Score: {risk.risk_score}/100  |  Level: {risk.risk_level.upper()}\n"
        f"- Completion: {risk.completion_percentage}%\n"
        f"- Delayed Topics: {risk.delayed_topics_count}\n"
        f"- Teaching Hours Behind: {risk.hours_behind}h\n"
        f"- Predicted Completion Date: {risk.predicted_completion_date or 'Unknown'}\n"
        f"- Estimated Extra Delay: {risk.delay_days} days\n\n"
        f"IDENTIFIED RISK FACTORS:\n{factors_list}\n\n"
        f"RULE-BASED MITIGATIONS:\n{mitigations_list}\n\n"
        f"Generate a narrative risk report in exactly this JSON:\n"
        f'{{\n'
        f'  "executive_summary": "<2-3 sentences summarising the plan\'s current health for department heads>",\n'
        f'  "key_concerns": ["<specific concern 1>", "<concern 2>", "<concern 3>"],\n'
        f'  "immediate_actions": ["<action to take this week 1>", "<action 2>", "<action 3>"],\n'
        f'  "long_term_strategy": "<strategic recommendation for the remainder of the semester>"\n'
        f'}}'
    )


# ---------------------------------------------------------------------------
# 5. Holistic summary insights prompt
# ---------------------------------------------------------------------------

def summary_insights_prompt(
    ctx: PlanContext,
    risk: RiskReport,
    forecast: dict,
) -> str:
    """
    Build a prompt for a full holistic analysis of the lesson plan's progress.

    Expected JSON response shape:
    {
      "progress_narrative": "string",
      "teaching_style_analysis": "string",
      "student_performance_insight": "string",
      "recommendations": ["string", ...],
      "motivational_note": "string"
    }
    """
    understanding_label = _understanding_label(ctx.avg_understanding_score)

    if ctx.method_effectiveness:
        best_method = max(ctx.method_effectiveness, key=ctx.method_effectiveness.get)
        best_score = ctx.method_effectiveness[best_method]
        method_summary = f"Best method: {best_method} (avg understanding score: {best_score:.2f}/3)"
    else:
        method_summary = "No method effectiveness data recorded yet."

    return (
        f"{_SYSTEM_HEADER}"
        f"HOLISTIC LESSON PLAN ANALYSIS:\n"
        f"- Subject: {ctx.subject_name}\n"
        f"- Academic Year: {ctx.academic_year}, Semester: {ctx.semester}\n"
        f"- Progress: {ctx.completed_topics}/{ctx.total_topics} topics "
        f"({ctx.completion_percentage:.1f}%)\n"
        f"- Teaching Hours: {ctx.total_hours_delivered:.1f}h delivered of "
        f"{ctx.total_planned_hours:.1f}h planned\n"
        f"- Risk Level: {risk.risk_level.upper()} (score: {risk.risk_score}/100)\n"
        f"- Average Student Understanding: {understanding_label} "
        f"({ctx.avg_understanding_score:.2f}/3)\n"
        f"- {method_summary}\n"
        f"- Estimated Completion: {forecast.get('estimated_completion_date', 'Unknown')}\n"
        f"- Teaching Velocity: {forecast.get('topics_per_week', 0):.1f} topics/week\n\n"
        f"Generate a comprehensive analysis in exactly this JSON:\n"
        f'{{\n'
        f'  "progress_narrative": "<detailed narrative of the current state of this lesson plan>",\n'
        f'  "teaching_style_analysis": "<analysis of teaching methods used and their observed effectiveness>",\n'
        f'  "student_performance_insight": "<insight into student comprehension trends and patterns>",\n'
        f'  "recommendations": [\n'
        f'    "<top actionable recommendation 1>",\n'
        f'    "<recommendation 2>",\n'
        f'    "<recommendation 3>",\n'
        f'    "<recommendation 4>"\n'
        f'  ],\n'
        f'  "motivational_note": "<brief, genuine encouraging message for the teacher>"\n'
        f'}}'
    )

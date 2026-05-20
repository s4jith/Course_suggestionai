"""
Analytics Service – MongoDB aggregation pipelines for the Analytics Dashboard.

Design decisions:
- All heavy aggregations run directly in MongoDB via Motor (async).
- Results are cached in-process using a simple TTL dict cache (no Redis dep).
- Cache TTL defaults to 5 minutes; individual endpoints may override.
- Every pipeline targets the canonical collections:
    lesson_plans, topic_progress, subjects, users
"""

import asyncio
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.analytics import (
    CompletionTrendPoint,
    CompletionTrendResponse,
    DelayedTopicItem,
    DelayedTopicsResponse,
    FacultyAnalyticsItem,
    FacultyAnalyticsResponse,
    HeatmapCell,
    HeatmapResponse,
    OverviewKPI,
    RiskScoreItem,
    RiskScoresResponse,
    SubjectAnalyticsItem,
    SubjectAnalyticsResponse,
    SyllabusCompletionItem,
    SyllabusCompletionResponse,
    TeachingMethodItem,
    TeachingMethodResponse,
    UnderstandingAnalyticsResponse,
    UnderstandingBreakdown,
    UnderstandingBySubject,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Simple in-process TTL cache
# ---------------------------------------------------------------------------

_CACHE: Dict[str, Tuple[float, Any]] = {}
DEFAULT_TTL = 300  # 5 minutes


def _cache_get(key: str) -> Optional[Any]:
    if key in _CACHE:
        ts, value = _CACHE[key]
        if time.monotonic() - ts < DEFAULT_TTL:
            return value
        del _CACHE[key]
    return None


def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = (time.monotonic(), value)


def invalidate_cache() -> None:
    """Clear all cached analytics results (call after data mutation)."""
    _CACHE.clear()


# ---------------------------------------------------------------------------
# Understanding level → numeric score mapping
# ---------------------------------------------------------------------------
_UNDERSTANDING_SCORE = {"excellent": 4, "good": 3, "average": 2, "poor": 1}

_METHOD_LABELS = {
    "theoretical": "Theoretical",
    "practical": "Practical",
    "ppt": "PPT Presentation",
    "seminar": "Seminar",
    "lab": "Lab Session",
    "assignment": "Assignment",
    "discussion": "Group Discussion",
    "case_study": "Case Study",
    "video_based": "Video Based",
}


# ===========================================================================
# AnalyticsService
# ===========================================================================

class AnalyticsService:
    """
    All analytics aggregation logic.
    Inject with `db` from `get_database()` FastAPI dependency.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.lp_col = db["lesson_plans"]
        self.tp_col = db["topic_progress"]
        self.subj_col = db["subjects"]
        self.user_col = db["users"]

    # -----------------------------------------------------------------------
    # Helper – build a MongoDB $match stage from optional filters
    # -----------------------------------------------------------------------
    def _tp_match(
        self,
        academic_year: Optional[str] = None,
        department: Optional[str] = None,
        teacher_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        match: Dict[str, Any] = {}
        if teacher_id:
            match["teacher_id"] = teacher_id
        if subject_id:
            match["subject_id"] = subject_id
        if from_date or to_date:
            date_filter: Dict[str, Any] = {}
            if from_date:
                date_filter["$gte"] = from_date
            if to_date:
                date_filter["$lte"] = to_date
            match["actual_date"] = date_filter
        return match

    def _lp_match(
        self,
        academic_year: Optional[str] = None,
        teacher_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        semester: Optional[int] = None,
    ) -> Dict[str, Any]:
        match: Dict[str, Any] = {}
        if academic_year:
            match["academic_year"] = academic_year
        if teacher_id:
            match["teacher_id"] = teacher_id
        if subject_id:
            match["subject_id"] = subject_id
        if semester:
            match["semester"] = semester
        return match

    # -----------------------------------------------------------------------
    # 1. Overview KPIs
    # -----------------------------------------------------------------------
    async def get_overview(
        self,
        academic_year: Optional[str] = None,
        semester: Optional[int] = None,
        department: Optional[str] = None,
        teacher_id: Optional[str] = None,
    ) -> OverviewKPI:
        cache_key = f"overview:{academic_year}:{semester}:{department}:{teacher_id}"
        if cached := _cache_get(cache_key):
            return cached

        # Lesson plan stats
        lp_match = self._lp_match(academic_year, teacher_id, semester=semester)
        lp_pipeline = [
            {"$match": lp_match},
            {"$unwind": {"path": "$chapters", "preserveNullAndEmpty": True}},
            {"$unwind": {"path": "$chapters.topics", "preserveNullAndEmpty": True}},
            {
                "$group": {
                    "_id": None,
                    "total_plans": {"$addToSet": "$_id"},
                    "active_plans": {
                        "$addToSet": {
                            "$cond": [{"$eq": ["$status", "active"]}, "$_id", "$$REMOVE"]
                        }
                    },
                    "total_topics": {"$sum": 1},
                    "total_hours_planned": {"$sum": "$chapters.topics.planned_hours"},
                }
            },
        ]

        # Topic progress stats
        tp_match = self._tp_match(academic_year, department, teacher_id)
        tp_pipeline = [
            {"$match": tp_match},
            {
                "$group": {
                    "_id": None,
                    "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
                    "in_progress": {"$sum": {"$cond": [{"$eq": ["$status", "in_progress"]}, 1, 0]}},
                    "pending": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}},
                    "skipped": {"$sum": {"$cond": [{"$eq": ["$status", "skipped"]}, 1, 0]}},
                    "total_hours_delivered": {"$sum": {"$ifNull": ["$duration_taken", 0]}},
                    "understanding_scores": {
                        "$push": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$eq": ["$student_understanding_level", "excellent"]}, "then": 4},
                                    {"case": {"$eq": ["$student_understanding_level", "good"]}, "then": 3},
                                    {"case": {"$eq": ["$student_understanding_level", "average"]}, "then": 2},
                                    {"case": {"$eq": ["$student_understanding_level", "poor"]}, "then": 1},
                                ],
                                "default": None,
                            }
                        }
                    },
                }
            },
        ]

        lp_results, tp_results = await asyncio.gather(
            self.lp_col.aggregate(lp_pipeline).to_list(1),
            self.tp_col.aggregate(tp_pipeline).to_list(1),
        )

        lp = lp_results[0] if lp_results else {}
        tp = tp_results[0] if tp_results else {}

        total_plans = len(lp.get("total_plans") or [])
        active_plans = len([x for x in (lp.get("active_plans") or []) if x is not None])
        total_topics = lp.get("total_topics", 0) or 0
        completed = tp.get("completed", 0) or 0
        in_progress = tp.get("in_progress", 0) or 0
        pending = tp.get("pending", 0) or 0
        skipped = tp.get("skipped", 0) or 0
        hours_planned = float(lp.get("total_hours_planned") or 0)
        hours_delivered = float(tp.get("total_hours_delivered") or 0)

        # Understanding avg (filter None values)
        scores = [s for s in (tp.get("understanding_scores") or []) if s is not None]
        avg_understanding = round(sum(scores) / len(scores), 2) if scores else None

        completion_pct = round((completed / total_topics * 100) if total_topics else 0, 1)
        hours_pct = round((hours_delivered / hours_planned * 100) if hours_planned else 0, 1)

        # Count at-risk lesson plans (risk_score >= 60)
        risk_resp = await self.get_risk_scores(academic_year=academic_year, semester=semester)
        at_risk = sum(1 for r in risk_resp.items if r.risk_score >= 60)
        delayed = await self._count_delayed(lp_match)

        result = OverviewKPI(
            total_lesson_plans=total_plans,
            active_lesson_plans=active_plans,
            total_topics=total_topics,
            completed_topics=completed,
            in_progress_topics=in_progress,
            pending_topics=pending,
            skipped_topics=skipped,
            overall_completion_pct=completion_pct,
            total_hours_planned=round(hours_planned, 1),
            total_hours_delivered=round(hours_delivered, 1),
            hours_delivery_pct=hours_pct,
            at_risk_plans=at_risk,
            delayed_topics=delayed,
            avg_understanding_score=avg_understanding,
        )
        _cache_set(cache_key, result)
        return result

    async def _count_delayed(self, lp_match: Dict[str, Any]) -> int:
        now = datetime.now(timezone.utc)
        pipeline = [
            {"$match": lp_match},
            {"$unwind": "$chapters"},
            {"$unwind": "$chapters.topics"},
            {
                "$match": {
                    "chapters.topics.planned_date": {"$lt": now},
                    "chapters.topics.topic_id": {"$exists": True},
                }
            },
            {"$count": "total"},
        ]
        res = await self.lp_col.aggregate(pipeline).to_list(1)
        if not res:
            return 0
        topic_ids_with_planned_dates = res[0].get("total", 0)

        # Cross-check against completed in topic_progress
        pipeline2 = [
            {"$match": lp_match},
            {"$unwind": "$chapters"},
            {"$unwind": "$chapters.topics"},
            {
                "$match": {
                    "chapters.topics.planned_date": {"$lt": now},
                }
            },
            {
                "$lookup": {
                    "from": "topic_progress",
                    "localField": "chapters.topics.topic_id",
                    "foreignField": "topic_id",
                    "as": "progress",
                }
            },
            {
                "$match": {
                    "$or": [
                        {"progress": {"$size": 0}},
                        {"progress.status": {"$nin": ["completed", "skipped"]}},
                    ]
                }
            },
            {"$count": "total"},
        ]
        res2 = await self.lp_col.aggregate(pipeline2).to_list(1)
        return res2[0].get("total", 0) if res2 else 0

    # -----------------------------------------------------------------------
    # 2. Syllabus completion
    # -----------------------------------------------------------------------
    async def get_syllabus_completion(
        self,
        academic_year: Optional[str] = None,
        semester: Optional[int] = None,
        teacher_id: Optional[str] = None,
        subject_id: Optional[str] = None,
    ) -> SyllabusCompletionResponse:
        cache_key = f"syllabus:{academic_year}:{semester}:{teacher_id}:{subject_id}"
        if cached := _cache_get(cache_key):
            return cached

        lp_match = self._lp_match(academic_year, teacher_id, subject_id, semester)
        pipeline = [
            {"$match": lp_match},
            # Lookup subject name
            {
                "$lookup": {
                    "from": "subjects",
                    "let": {"sid": "$subject_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$sid"]}}},
                        {"$project": {"name": 1}},
                    ],
                    "as": "subject_doc",
                }
            },
            # Unwind chapters & topics to count
            {"$addFields": {
                "all_topics": {
                    "$reduce": {
                        "input": "$chapters",
                        "initialValue": [],
                        "in": {"$concatArrays": ["$$value", "$$this.topics"]}
                    }
                },
                "subject_name": {"$ifNull": [{"$arrayElemAt": ["$subject_doc.name", 0]}, "Unknown"]},
            }},
            {
                "$addFields": {
                    "total_topics": {"$size": "$all_topics"},
                    "total_hours_planned": {
                        "$sum": {"$map": {"input": "$all_topics", "as": "t", "in": "$$t.planned_hours"}}
                    },
                    "topic_ids": {
                        "$map": {"input": "$all_topics", "as": "t", "in": "$$t.topic_id"}
                    },
                }
            },
            # Lookup progress records for this lesson plan
            {
                "$lookup": {
                    "from": "topic_progress",
                    "localField": "_id",
                    "foreignField": "lesson_plan_id",
                    "as": "progress_records",
                }
            },
            {
                "$addFields": {
                    "completed_topics": {
                        "$size": {
                            "$filter": {
                                "input": "$progress_records",
                                "as": "p",
                                "cond": {"$eq": ["$$p.status", "completed"]},
                            }
                        }
                    },
                    "hours_delivered": {
                        "$sum": {
                            "$map": {
                                "input": "$progress_records",
                                "as": "p",
                                "in": {"$ifNull": ["$$p.duration_taken", 0]},
                            }
                        }
                    },
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "title": 1,
                    "subject_name": 1,
                    "academic_year": 1,
                    "semester": 1,
                    "status": 1,
                    "total_topics": 1,
                    "completed_topics": 1,
                    "total_hours_planned": 1,
                    "hours_delivered": 1,
                }
            },
        ]

        docs = await self.lp_col.aggregate(pipeline).to_list(None)
        items = []
        for d in docs:
            total = d.get("total_topics", 0) or 0
            completed = d.get("completed_topics", 0) or 0
            pct = round((completed / total * 100) if total else 0, 1)
            pending = total - completed
            delayed = 0  # simplified
            risk = _compute_risk_score(pct, pending, total, delayed)

            items.append(SyllabusCompletionItem(
                lesson_plan_id=str(d["_id"]),
                title=d.get("title", ""),
                subject_name=d.get("subject_name", ""),
                academic_year=d.get("academic_year", ""),
                semester=d.get("semester", 0),
                status=d.get("status", ""),
                total_topics=total,
                completed_topics=completed,
                completion_pct=pct,
                hours_planned=round(float(d.get("total_hours_planned") or 0), 1),
                hours_delivered=round(float(d.get("hours_delivered") or 0), 1),
                risk_score=risk,
            ))

        avg_pct = round(sum(i.completion_pct for i in items) / len(items), 1) if items else 0.0
        result = SyllabusCompletionResponse(items=items, avg_completion_pct=avg_pct)
        _cache_set(cache_key, result)
        return result

    # -----------------------------------------------------------------------
    # 3. Faculty analytics
    # -----------------------------------------------------------------------
    async def get_faculty_analytics(
        self,
        academic_year: Optional[str] = None,
        department: Optional[str] = None,
    ) -> FacultyAnalyticsResponse:
        cache_key = f"faculty:{academic_year}:{department}"
        if cached := _cache_get(cache_key):
            return cached

        pipeline = [
            {
                "$group": {
                    "_id": "$teacher_id",
                    "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
                    "in_progress": {"$sum": {"$cond": [{"$eq": ["$status", "in_progress"]}, 1, 0]}},
                    "pending": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}},
                    "skipped": {"$sum": {"$cond": [{"$eq": ["$status", "skipped"]}, 1, 0]}},
                    "total": {"$sum": 1},
                    "hours_delivered": {"$sum": {"$ifNull": ["$duration_taken", 0]}},
                    "understanding_scores": {
                        "$push": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$eq": ["$student_understanding_level", "excellent"]}, "then": 4},
                                    {"case": {"$eq": ["$student_understanding_level", "good"]}, "then": 3},
                                    {"case": {"$eq": ["$student_understanding_level", "average"]}, "then": 2},
                                    {"case": {"$eq": ["$student_understanding_level", "poor"]}, "then": 1},
                                ],
                                "default": None,
                            }
                        }
                    },
                    "lesson_plans": {"$addToSet": "$lesson_plan_id"},
                }
            }
        ]

        tp_docs = await self.tp_col.aggregate(pipeline).to_list(None)

        # Fetch user details for each teacher_id
        teacher_ids = [d["_id"] for d in tp_docs if d["_id"]]
        from bson import ObjectId
        user_map: Dict[str, Any] = {}
        for tid in teacher_ids:
            try:
                user = await self.user_col.find_one({"_id": ObjectId(tid)})
                if user:
                    user_map[tid] = user
            except Exception:
                pass

        items = []
        for d in tp_docs:
            teacher_id = d["_id"]
            user = user_map.get(teacher_id, {})
            total = d.get("total", 0)
            completed = d.get("completed", 0)
            pct = round((completed / total * 100) if total else 0, 1)
            scores = [s for s in (d.get("understanding_scores") or []) if s is not None]
            avg_understanding = round(sum(scores) / len(scores), 2) if scores else None

            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or teacher_id
            items.append(FacultyAnalyticsItem(
                teacher_id=teacher_id,
                teacher_name=full_name or "Unknown",
                email=user.get("email", ""),
                total_topics_assigned=total,
                completed_topics=completed,
                in_progress_topics=d.get("in_progress", 0),
                pending_topics=d.get("pending", 0),
                skipped_topics=d.get("skipped", 0),
                completion_pct=pct,
                total_hours_delivered=round(float(d.get("hours_delivered") or 0), 1),
                avg_understanding_score=avg_understanding,
                lesson_plans_count=len(d.get("lesson_plans") or []),
            ))

        items.sort(key=lambda x: x.completion_pct, reverse=True)
        result = FacultyAnalyticsResponse(items=items)
        _cache_set(cache_key, result)
        return result

    # -----------------------------------------------------------------------
    # 4. Subject analytics
    # -----------------------------------------------------------------------
    async def get_subject_analytics(
        self,
        academic_year: Optional[str] = None,
        department: Optional[str] = None,
        semester: Optional[int] = None,
    ) -> SubjectAnalyticsResponse:
        cache_key = f"subject:{academic_year}:{department}:{semester}"
        if cached := _cache_get(cache_key):
            return cached

        lp_match = self._lp_match(academic_year, semester=semester)
        pipeline = [
            {"$match": lp_match},
            {
                "$lookup": {
                    "from": "subjects",
                    "let": {"sid": "$subject_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$sid"]}}},
                    ],
                    "as": "subject_doc",
                }
            },
            {"$unwind": {"path": "$subject_doc", "preserveNullAndEmpty": True}},
            # Filter by department if specified
            *([{"$match": {"subject_doc.department": department}}] if department else []),
            {
                "$addFields": {
                    "all_topics": {
                        "$reduce": {
                            "input": "$chapters",
                            "initialValue": [],
                            "in": {"$concatArrays": ["$$value", "$$this.topics"]}
                        }
                    }
                }
            },
            {
                "$lookup": {
                    "from": "topic_progress",
                    "localField": "_id",
                    "foreignField": "lesson_plan_id",
                    "as": "progress_records",
                }
            },
            {
                "$group": {
                    "_id": "$subject_id",
                    "subject_name": {"$first": "$subject_doc.name"},
                    "subject_code": {"$first": "$subject_doc.code"},
                    "department": {"$first": "$subject_doc.department"},
                    "semester": {"$first": "$subject_doc.semester"},
                    "total_lesson_plans": {"$sum": 1},
                    "total_topics": {"$sum": {"$size": "$all_topics"}},
                    "total_hours_planned": {
                        "$sum": {
                            "$sum": {
                                "$map": {
                                    "input": "$all_topics",
                                    "as": "t",
                                    "in": "$$t.planned_hours",
                                }
                            }
                        }
                    },
                    "completed_topics": {
                        "$sum": {
                            "$size": {
                                "$filter": {
                                    "input": "$progress_records",
                                    "as": "p",
                                    "cond": {"$eq": ["$$p.status", "completed"]},
                                }
                            }
                        }
                    },
                    "hours_delivered": {
                        "$sum": {
                            "$sum": {
                                "$map": {
                                    "input": "$progress_records",
                                    "as": "p",
                                    "in": {"$ifNull": ["$$p.duration_taken", 0]},
                                }
                            }
                        }
                    },
                }
            },
        ]

        docs = await self.lp_col.aggregate(pipeline).to_list(None)
        items = []
        for d in docs:
            total = d.get("total_topics", 0) or 0
            completed = d.get("completed_topics", 0) or 0
            pct = round((completed / total * 100) if total else 0, 1)
            items.append(SubjectAnalyticsItem(
                subject_id=str(d["_id"]),
                subject_name=d.get("subject_name") or "Unknown",
                subject_code=d.get("subject_code") or "",
                department=d.get("department") or "",
                semester=d.get("semester") or 0,
                total_lesson_plans=d.get("total_lesson_plans", 0),
                avg_completion_pct=pct,
                total_topics=total,
                completed_topics=completed,
                pending_topics=total - completed,
                total_hours_planned=round(float(d.get("total_hours_planned") or 0), 1),
                total_hours_delivered=round(float(d.get("hours_delivered") or 0), 1),
            ))

        items.sort(key=lambda x: x.avg_completion_pct, reverse=True)
        result = SubjectAnalyticsResponse(items=items)
        _cache_set(cache_key, result)
        return result

    # -----------------------------------------------------------------------
    # 5. Delayed topics
    # -----------------------------------------------------------------------
    async def get_delayed_topics(
        self,
        academic_year: Optional[str] = None,
        teacher_id: Optional[str] = None,
    ) -> DelayedTopicsResponse:
        cache_key = f"delayed:{academic_year}:{teacher_id}"
        if cached := _cache_get(cache_key):
            return cached

        now = datetime.now(timezone.utc)
        lp_match = self._lp_match(academic_year, teacher_id)

        pipeline = [
            {"$match": lp_match},
            {
                "$lookup": {
                    "from": "subjects",
                    "let": {"sid": "$subject_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$sid"]}}},
                        {"$project": {"name": 1}},
                    ],
                    "as": "subject_doc",
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "let": {"tid": "$teacher_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$tid"]}}},
                        {"$project": {"first_name": 1, "last_name": 1}},
                    ],
                    "as": "teacher_doc",
                }
            },
            {"$unwind": "$chapters"},
            {"$unwind": "$chapters.topics"},
            {
                "$match": {
                    "chapters.topics.planned_date": {"$lt": now, "$ne": None},
                }
            },
            {
                "$lookup": {
                    "from": "topic_progress",
                    "let": {"tid": "$chapters.topics.topic_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$topic_id", "$$tid"]}}},
                    ],
                    "as": "progress",
                }
            },
            {
                "$match": {
                    "$or": [
                        {"progress": {"$size": 0}},
                        {"progress.0.status": {"$nin": ["completed", "skipped"]}},
                    ]
                }
            },
            {
                "$project": {
                    "topic_id": "$chapters.topics.topic_id",
                    "topic_title": "$chapters.topics.title",
                    "chapter_title": "$chapters.title",
                    "lesson_plan_id": {"$toString": "$_id"},
                    "lesson_plan_title": "$title",
                    "subject_name": {"$ifNull": [{"$arrayElemAt": ["$subject_doc.name", 0]}, "Unknown"]},
                    "teacher_name": {
                        "$concat": [
                            {"$ifNull": [{"$arrayElemAt": ["$teacher_doc.first_name", 0]}, ""]},
                            " ",
                            {"$ifNull": [{"$arrayElemAt": ["$teacher_doc.last_name", 0]}, ""]},
                        ]
                    },
                    "planned_date": "$chapters.topics.planned_date",
                    "status": {"$ifNull": [{"$arrayElemAt": ["$progress.status", 0]}, "pending"]},
                    "completion_pct": {"$ifNull": [{"$arrayElemAt": ["$progress.completion_percentage", 0]}, 0]},
                }
            },
        ]

        docs = await self.lp_col.aggregate(pipeline).to_list(None)
        items = []
        for d in docs:
            planned = d.get("planned_date")
            if planned:
                if planned.tzinfo is None:
                    planned = planned.replace(tzinfo=timezone.utc)
                days_overdue = max(0, (now - planned).days)
            else:
                days_overdue = 0

            items.append(DelayedTopicItem(
                topic_id=d.get("topic_id", ""),
                topic_title=d.get("topic_title", ""),
                chapter_title=d.get("chapter_title", ""),
                lesson_plan_id=d.get("lesson_plan_id", ""),
                lesson_plan_title=d.get("lesson_plan_title", ""),
                subject_name=d.get("subject_name", ""),
                teacher_name=d.get("teacher_name", "").strip() or "Unknown",
                planned_date=planned,
                days_overdue=days_overdue,
                status=d.get("status", "pending"),
                completion_pct=float(d.get("completion_pct") or 0),
            ))

        items.sort(key=lambda x: x.days_overdue, reverse=True)
        result = DelayedTopicsResponse(items=items, total_delayed=len(items))
        _cache_set(cache_key, result)
        return result

    # -----------------------------------------------------------------------
    # 6. Risk scores
    # -----------------------------------------------------------------------
    async def get_risk_scores(
        self,
        academic_year: Optional[str] = None,
        semester: Optional[int] = None,
        teacher_id: Optional[str] = None,
    ) -> RiskScoresResponse:
        cache_key = f"risk:{academic_year}:{semester}:{teacher_id}"
        if cached := _cache_get(cache_key):
            return cached

        syllabus = await self.get_syllabus_completion(
            academic_year=academic_year, semester=semester, teacher_id=teacher_id
        )

        items = []
        for plan in syllabus.items:
            pending = plan.total_topics - plan.completed_topics
            delayed = 0  # simplified; full delayed count from pipeline is expensive
            risk = plan.risk_score
            risk_level = _risk_level(risk)
            rec = _risk_recommendation(risk_level, pending, plan.completion_pct)

            items.append(RiskScoreItem(
                lesson_plan_id=plan.lesson_plan_id,
                title=plan.title,
                subject_name=plan.subject_name,
                teacher_name="",  # enriched lazily
                risk_score=risk,
                risk_level=risk_level,
                completion_pct=plan.completion_pct,
                pending_topics=pending,
                delayed_topics=delayed,
                days_remaining=None,
                recommendation=rec,
            ))

        items.sort(key=lambda x: x.risk_score, reverse=True)
        avg_risk = round(sum(i.risk_score for i in items) / len(items), 1) if items else 0.0
        result = RiskScoresResponse(items=items, avg_risk_score=avg_risk)
        _cache_set(cache_key, result)
        return result

    # -----------------------------------------------------------------------
    # 7. Teaching method effectiveness
    # -----------------------------------------------------------------------
    async def get_teaching_method_effectiveness(
        self,
        academic_year: Optional[str] = None,
        teacher_id: Optional[str] = None,
    ) -> TeachingMethodResponse:
        cache_key = f"methods:{academic_year}:{teacher_id}"
        if cached := _cache_get(cache_key):
            return cached

        match: Dict[str, Any] = {"teaching_method": {"$ne": None}}
        if teacher_id:
            match["teacher_id"] = teacher_id

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$teaching_method",
                    "total_uses": {"$sum": 1},
                    "avg_completion": {"$avg": "$completion_percentage"},
                    "avg_duration": {"$avg": "$duration_taken"},
                    "excellent": {"$sum": {"$cond": [{"$eq": ["$student_understanding_level", "excellent"]}, 1, 0]}},
                    "good": {"$sum": {"$cond": [{"$eq": ["$student_understanding_level", "good"]}, 1, 0]}},
                    "average": {"$sum": {"$cond": [{"$eq": ["$student_understanding_level", "average"]}, 1, 0]}},
                    "poor": {"$sum": {"$cond": [{"$eq": ["$student_understanding_level", "poor"]}, 1, 0]}},
                    "understanding_scores": {
                        "$push": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$eq": ["$student_understanding_level", "excellent"]}, "then": 4},
                                    {"case": {"$eq": ["$student_understanding_level", "good"]}, "then": 3},
                                    {"case": {"$eq": ["$student_understanding_level", "average"]}, "then": 2},
                                    {"case": {"$eq": ["$student_understanding_level", "poor"]}, "then": 1},
                                ],
                                "default": None,
                            }
                        }
                    },
                }
            },
        ]

        docs = await self.tp_col.aggregate(pipeline).to_list(None)
        items = []
        for d in docs:
            scores = [s for s in (d.get("understanding_scores") or []) if s is not None]
            avg_und = round(sum(scores) / len(scores), 2) if scores else 0.0
            avg_comp = round(float(d.get("avg_completion") or 0), 1)
            # Composite effectiveness: 0.6 * understanding_pct + 0.4 * completion_pct
            effectiveness = round(0.6 * (avg_und / 4 * 100) + 0.4 * avg_comp, 1)
            items.append(TeachingMethodItem(
                method=d["_id"],
                label=_METHOD_LABELS.get(d["_id"], d["_id"]),
                total_uses=d.get("total_uses", 0),
                avg_completion_pct=avg_comp,
                avg_understanding_score=avg_und,
                excellent_count=d.get("excellent", 0),
                good_count=d.get("good", 0),
                average_count=d.get("average", 0),
                poor_count=d.get("poor", 0),
                avg_duration_hours=round(float(d.get("avg_duration") or 0), 2) or None,
                effectiveness_score=effectiveness,
            ))

        items.sort(key=lambda x: x.effectiveness_score, reverse=True)
        result = TeachingMethodResponse(items=items)
        _cache_set(cache_key, result)
        return result

    # -----------------------------------------------------------------------
    # 8. Student understanding analytics
    # -----------------------------------------------------------------------
    async def get_understanding_analytics(
        self,
        academic_year: Optional[str] = None,
        teacher_id: Optional[str] = None,
    ) -> UnderstandingAnalyticsResponse:
        cache_key = f"understanding:{academic_year}:{teacher_id}"
        if cached := _cache_get(cache_key):
            return cached

        match: Dict[str, Any] = {"student_understanding_level": {"$ne": None}}
        if teacher_id:
            match["teacher_id"] = teacher_id

        # Overall pipeline
        overall_pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$student_understanding_level",
                    "count": {"$sum": 1},
                }
            },
        ]

        # By subject pipeline
        by_subject_pipeline = [
            {"$match": match},
            {
                "$lookup": {
                    "from": "subjects",
                    "let": {"sid": "$subject_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": [{"$toString": "$_id"}, "$$sid"]}}},
                        {"$project": {"name": 1, "code": 1}},
                    ],
                    "as": "subject_doc",
                }
            },
            {
                "$group": {
                    "_id": "$subject_id",
                    "subject_name": {"$first": {"$arrayElemAt": ["$subject_doc.name", 0]}},
                    "subject_code": {"$first": {"$arrayElemAt": ["$subject_doc.code", 0]}},
                    "excellent": {"$sum": {"$cond": [{"$eq": ["$student_understanding_level", "excellent"]}, 1, 0]}},
                    "good": {"$sum": {"$cond": [{"$eq": ["$student_understanding_level", "good"]}, 1, 0]}},
                    "average": {"$sum": {"$cond": [{"$eq": ["$student_understanding_level", "average"]}, 1, 0]}},
                    "poor": {"$sum": {"$cond": [{"$eq": ["$student_understanding_level", "poor"]}, 1, 0]}},
                    "total": {"$sum": 1},
                }
            },
        ]

        overall_docs, by_subject_docs = await asyncio.gather(
            self.tp_col.aggregate(overall_pipeline).to_list(None),
            self.tp_col.aggregate(by_subject_pipeline).to_list(None),
        )

        # Build overall breakdown
        counts: Dict[str, int] = {d["_id"]: d["count"] for d in overall_docs if d["_id"]}
        total = sum(counts.values())
        overall = _build_breakdown(
            counts.get("excellent", 0),
            counts.get("good", 0),
            counts.get("average", 0),
            counts.get("poor", 0),
        )

        # Build by-subject
        by_subject = []
        for d in by_subject_docs:
            bd = _build_breakdown(
                d.get("excellent", 0), d.get("good", 0),
                d.get("average", 0), d.get("poor", 0),
            )
            by_subject.append(UnderstandingBySubject(
                subject_name=d.get("subject_name") or "Unknown",
                subject_code=d.get("subject_code") or "",
                breakdown=bd,
            ))

        by_subject.sort(key=lambda x: x.breakdown.avg_score, reverse=True)
        result = UnderstandingAnalyticsResponse(overall=overall, by_subject=by_subject)
        _cache_set(cache_key, result)
        return result

    # -----------------------------------------------------------------------
    # 9. Completion trend (time-series line chart)
    # -----------------------------------------------------------------------
    async def get_completion_trend(
        self,
        days: int = 30,
        teacher_id: Optional[str] = None,
    ) -> CompletionTrendResponse:
        cache_key = f"trend:{days}:{teacher_id}"
        if cached := _cache_get(cache_key):
            return cached

        since = datetime.now(timezone.utc) - timedelta(days=days)
        match: Dict[str, Any] = {
            "status": "completed",
            "actual_date": {"$gte": since},
        }
        if teacher_id:
            match["teacher_id"] = teacher_id

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$actual_date"},
                        "month": {"$month": "$actual_date"},
                        "day": {"$dayOfMonth": "$actual_date"},
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}},
        ]

        docs = await self.tp_col.aggregate(pipeline).to_list(None)
        points: List[CompletionTrendPoint] = []
        cumulative = 0
        for d in docs:
            g = d["_id"]
            date_str = f"{g['year']:04d}-{g['month']:02d}-{g['day']:02d}"
            cumulative += d["count"]
            points.append(CompletionTrendPoint(
                date=date_str,
                completed_count=d["count"],
                cumulative_completed=cumulative,
            ))

        result = CompletionTrendResponse(points=points, period_days=days)
        _cache_set(cache_key, result)
        return result

    # -----------------------------------------------------------------------
    # 10. Heatmap data
    # -----------------------------------------------------------------------
    async def get_heatmap(
        self,
        days: int = 90,
        teacher_id: Optional[str] = None,
    ) -> HeatmapResponse:
        cache_key = f"heatmap:{days}:{teacher_id}"
        if cached := _cache_get(cache_key):
            return cached

        since = datetime.now(timezone.utc) - timedelta(days=days)
        match: Dict[str, Any] = {
            "status": "completed",
            "actual_date": {"$gte": since},
        }
        if teacher_id:
            match["teacher_id"] = teacher_id

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$actual_date"},
                        "month": {"$month": "$actual_date"},
                        "day": {"$dayOfMonth": "$actual_date"},
                    },
                    "count": {"$sum": 1},
                }
            },
        ]

        docs = await self.tp_col.aggregate(pipeline).to_list(None)
        count_map: Dict[str, int] = {}
        for d in docs:
            g = d["_id"]
            key = f"{g['year']:04d}-{g['month']:02d}-{g['day']:02d}"
            count_map[key] = d["count"]

        max_count = max(count_map.values(), default=0)

        cells = []
        for date_str, cnt in count_map.items():
            intensity = min(4, int((cnt / max_count * 4) + 0.5)) if max_count else 0
            cells.append(HeatmapCell(date=date_str, count=cnt, intensity=intensity))

        cells.sort(key=lambda x: x.date)
        result = HeatmapResponse(cells=cells, max_count=max_count)
        _cache_set(cache_key, result)
        return result


# ===========================================================================
# Pure-function helpers
# ===========================================================================

def _compute_risk_score(
    completion_pct: float,
    pending_count: int,
    total_count: int,
    delayed_count: int,
) -> float:
    """
    Risk score 0-100 (higher = more risk).
    Formula: 0.5 * incompletion_ratio + 0.3 * pending_ratio + 0.2 * delayed_ratio
    """
    if total_count == 0:
        return 0.0
    incompletion = 1 - (completion_pct / 100)
    pending_ratio = pending_count / total_count
    delayed_ratio = min(1.0, delayed_count / total_count) if total_count else 0
    raw = 0.5 * incompletion + 0.3 * pending_ratio + 0.2 * delayed_ratio
    return round(raw * 100, 1)


def _risk_level(score: float) -> str:
    if score < 25:
        return "low"
    elif score < 50:
        return "medium"
    elif score < 75:
        return "high"
    return "critical"


def _risk_recommendation(risk_level: str, pending: int, completion_pct: float) -> str:
    if risk_level == "critical":
        return f"Immediate action required. {pending} topics pending with {completion_pct:.0f}% completion."
    elif risk_level == "high":
        return f"Accelerate coverage. Focus on the {pending} remaining topics."
    elif risk_level == "medium":
        return f"On watch – {pending} topics pending. Maintain consistent progress."
    return "On track. Continue at current pace."


def _build_breakdown(excellent: int, good: int, average: int, poor: int) -> UnderstandingBreakdown:
    total = excellent + good + average + poor
    if total == 0:
        return UnderstandingBreakdown()
    weighted = (excellent * 4 + good * 3 + average * 2 + poor * 1)
    return UnderstandingBreakdown(
        excellent=excellent,
        good=good,
        average=average,
        poor=poor,
        total=total,
        excellent_pct=round(excellent / total * 100, 1),
        good_pct=round(good / total * 100, 1),
        average_pct=round(average / total * 100, 1),
        poor_pct=round(poor / total * 100, 1),
        avg_score=round(weighted / total, 2),
    )

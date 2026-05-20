"""
Topic Progress repository – all MongoDB I/O for the `topic_progress` collection.

Uses upsert semantics: one progress document per teacher × lesson_plan × topic
(× optional subtopic). If a record already exists, updating it refreshes the
completion details.
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.lesson_plan import TopicProgressDocument, TopicStatus


class TopicProgressRepository:
    """Async repository for the `topic_progress` collection."""

    COLLECTION = "topic_progress"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db[self.COLLECTION]

    @staticmethod
    def _to_model(doc: dict) -> TopicProgressDocument:
        return TopicProgressDocument(**doc)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def find_by_id(self, progress_id: str) -> Optional[TopicProgressDocument]:
        if not ObjectId.is_valid(progress_id):
            return None
        doc = await self._col.find_one({"_id": ObjectId(progress_id)})
        return self._to_model(doc) if doc else None

    async def find_by_topic(
        self,
        lesson_plan_id: str,
        topic_id: str,
        subtopic_id: Optional[str] = None,
        teacher_id: Optional[str] = None,
    ) -> Optional[TopicProgressDocument]:
        """Find a progress record by its natural key composite."""
        query: dict = {
            "lesson_plan_id": lesson_plan_id,
            "topic_id": topic_id,
            "subtopic_id": subtopic_id,
        }
        if teacher_id:
            query["teacher_id"] = teacher_id
        doc = await self._col.find_one(query)
        return self._to_model(doc) if doc else None

    async def list_for_plan(
        self,
        lesson_plan_id: str,
        status: Optional[TopicStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TopicProgressDocument]:
        """All progress records for a lesson plan, optionally filtered by status."""
        query: dict = {"lesson_plan_id": lesson_plan_id}
        if status:
            query["status"] = status.value
        cursor = self._col.find(query).skip(skip).limit(limit).sort("updated_at", -1)
        docs = await cursor.to_list(length=limit)
        return [self._to_model(d) for d in docs]

    async def list_for_teacher(
        self,
        teacher_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TopicProgressDocument]:
        """All progress records for a specific teacher across all lesson plans."""
        cursor = (
            self._col.find({"teacher_id": teacher_id})
            .skip(skip)
            .limit(limit)
            .sort("updated_at", -1)
        )
        docs = await cursor.to_list(length=limit)
        return [self._to_model(d) for d in docs]

    async def list_pending(
        self,
        lesson_plan_id: str,
        teacher_id: Optional[str] = None,
    ) -> list[TopicProgressDocument]:
        """Return all pending / in-progress topics for a lesson plan."""
        query: dict = {
            "lesson_plan_id": lesson_plan_id,
            "status": {"$in": [TopicStatus.PENDING.value, TopicStatus.IN_PROGRESS.value]},
        }
        if teacher_id:
            query["teacher_id"] = teacher_id
        cursor = self._col.find(query).sort("updated_at", 1)
        docs = await cursor.to_list(length=200)
        return [self._to_model(d) for d in docs]

    async def count_by_status(self, lesson_plan_id: str) -> dict:
        """
        Return a status-count mapping for a lesson plan.
        Used by the completion-stats endpoint.

        Returns: {"pending": n, "in_progress": n, "completed": n, "skipped": n}
        """
        pipeline = [
            {"$match": {"lesson_plan_id": lesson_plan_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        results = await self._col.aggregate(pipeline).to_list(length=10)
        counts = {item["_id"]: item["count"] for item in results}
        return {
            "pending": counts.get(TopicStatus.PENDING.value, 0),
            "in_progress": counts.get(TopicStatus.IN_PROGRESS.value, 0),
            "completed": counts.get(TopicStatus.COMPLETED.value, 0),
            "skipped": counts.get(TopicStatus.SKIPPED.value, 0),
        }

    async def sum_hours_delivered(self, lesson_plan_id: str) -> float:
        """Sum of duration_taken across all completed progress records for a plan."""
        pipeline = [
            {
                "$match": {
                    "lesson_plan_id": lesson_plan_id,
                    "status": TopicStatus.COMPLETED.value,
                    "duration_taken": {"$ne": None},
                }
            },
            {"$group": {"_id": None, "total": {"$sum": "$duration_taken"}}},
        ]
        results = await self._col.aggregate(pipeline).to_list(length=1)
        return results[0]["total"] if results else 0.0

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def upsert(self, doc: TopicProgressDocument) -> TopicProgressDocument:
        """
        Insert or update a progress record.

        The natural key is: (lesson_plan_id, topic_id, subtopic_id, teacher_id).
        If a document with this key exists it is updated in-place; otherwise a
        new document is inserted.
        """
        filter_query = {
            "lesson_plan_id": doc.lesson_plan_id,
            "topic_id": doc.topic_id,
            "subtopic_id": doc.subtopic_id,
            "teacher_id": doc.teacher_id,
        }
        payload = doc.model_dump(by_alias=True, exclude={"id"})
        payload["updated_at"] = datetime.utcnow()

        result = await self._col.find_one_and_update(
            filter_query,
            {"$set": payload},
            upsert=True,
            return_document=True,
        )
        return self._to_model(result)

    async def update_progress(
        self, progress_id: str, updates: dict
    ) -> Optional[TopicProgressDocument]:
        """Apply a partial update to a progress record by its _id."""
        if not ObjectId.is_valid(progress_id):
            return None
        updates["updated_at"] = datetime.utcnow()
        result = await self._col.find_one_and_update(
            {"_id": ObjectId(progress_id)},
            {"$set": updates},
            return_document=True,
        )
        return self._to_model(result) if result else None

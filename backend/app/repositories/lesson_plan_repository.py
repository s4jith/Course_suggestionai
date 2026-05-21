
from datetime import datetime
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.lesson_plan import (
    ChapterDocument,
    LessonPlanDocument,
    LessonPlanStatus,
    SubtopicDocument,
    TopicDocument,
)

class LessonPlanRepository:

    COLLECTION = "lesson_plans"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db[self.COLLECTION]

    @staticmethod
    def _to_model(doc: dict) -> LessonPlanDocument:
        return LessonPlanDocument(**doc)

    async def find_by_id(self, plan_id: str) -> Optional[LessonPlanDocument]:
        if not ObjectId.is_valid(plan_id):
            return None
        doc = await self._col.find_one({"_id": ObjectId(plan_id)})
        return self._to_model(doc) if doc else None

    async def list_plans(
        self,
        teacher_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        academic_year: Optional[str] = None,
        status: Optional[LessonPlanStatus] = None,
        semester: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[LessonPlanDocument]:
        query: dict = {}
        if teacher_id:
            query["teacher_id"] = teacher_id
        if subject_id:
            query["subject_id"] = subject_id
        if academic_year:
            query["academic_year"] = academic_year
        if status:
            query["status"] = status.value
        if semester is not None:
            query["semester"] = semester

        cursor = self._col.find(query).skip(skip).limit(limit).sort("created_at", -1)
        docs = await cursor.to_list(length=limit)
        return [self._to_model(d) for d in docs]

    async def count_plans(
        self,
        teacher_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        academic_year: Optional[str] = None,
        status: Optional[LessonPlanStatus] = None,
        semester: Optional[int] = None,
    ) -> int:
        query: dict = {}
        if teacher_id:
            query["teacher_id"] = teacher_id
        if subject_id:
            query["subject_id"] = subject_id
        if academic_year:
            query["academic_year"] = academic_year
        if status:
            query["status"] = status.value
        if semester is not None:
            query["semester"] = semester
        return await self._col.count_documents(query)

    async def create(self, doc: LessonPlanDocument) -> LessonPlanDocument:
        payload = doc.model_dump(by_alias=True, exclude={"id"})
        result = await self._col.insert_one(payload)
        doc.id = result.inserted_id
        return doc

    async def update_plan(self, plan_id: str, updates: dict) -> Optional[LessonPlanDocument]:
        if not ObjectId.is_valid(plan_id):
            return None
        updates["updated_at"] = datetime.utcnow()
        result = await self._col.find_one_and_update(
            {"_id": ObjectId(plan_id)},
            {"$set": updates},
            return_document=True,
        )
        return self._to_model(result) if result else None

    async def add_chapter(
        self, plan_id: str, chapter: ChapterDocument, updated_by: str
    ) -> Optional[LessonPlanDocument]:
        if not ObjectId.is_valid(plan_id):
            return None
        chapter_dict = chapter.model_dump()
        result = await self._col.find_one_and_update(
            {"_id": ObjectId(plan_id)},
            {
                "$push": {"chapters": chapter_dict},
                "$set": {"updated_at": datetime.utcnow(), "updated_by": updated_by},
            },
            return_document=True,
        )
        return self._to_model(result) if result else None

    async def update_chapter(
        self, plan_id: str, chapter_id: str, updates: dict, updated_by: str
    ) -> Optional[LessonPlanDocument]:
        if not ObjectId.is_valid(plan_id):
            return None
        set_fields = {f"chapters.$[ch].{k}": v for k, v in updates.items()}
        set_fields["updated_at"] = datetime.utcnow()
        set_fields["updated_by"] = updated_by
        result = await self._col.find_one_and_update(
            {"_id": ObjectId(plan_id)},
            {"$set": set_fields},
            array_filters=[{"ch.chapter_id": chapter_id}],
            return_document=True,
        )
        return self._to_model(result) if result else None

    async def add_topic(
        self, plan_id: str, chapter_id: str, topic: TopicDocument, updated_by: str
    ) -> Optional[LessonPlanDocument]:
        if not ObjectId.is_valid(plan_id):
            return None
        topic_dict = topic.model_dump()
        result = await self._col.find_one_and_update(
            {"_id": ObjectId(plan_id), "chapters.chapter_id": chapter_id},
            {
                "$push": {"chapters.$[ch].topics": topic_dict},
                "$set": {"updated_at": datetime.utcnow(), "updated_by": updated_by},
            },
            array_filters=[{"ch.chapter_id": chapter_id}],
            return_document=True,
        )
        return self._to_model(result) if result else None

    async def update_topic(
        self,
        plan_id: str,
        chapter_id: str,
        topic_id: str,
        updates: dict,
        updated_by: str,
    ) -> Optional[LessonPlanDocument]:
        if not ObjectId.is_valid(plan_id):
            return None
        set_fields = {f"chapters.$[ch].topics.$[tp].{k}": v for k, v in updates.items()}
        set_fields["updated_at"] = datetime.utcnow()
        set_fields["updated_by"] = updated_by
        result = await self._col.find_one_and_update(
            {"_id": ObjectId(plan_id)},
            {"$set": set_fields},
            array_filters=[
                {"ch.chapter_id": chapter_id},
                {"tp.topic_id": topic_id},
            ],
            return_document=True,
        )
        return self._to_model(result) if result else None

    async def add_subtopic(
        self,
        plan_id: str,
        chapter_id: str,
        topic_id: str,
        subtopic: SubtopicDocument,
        updated_by: str,
    ) -> Optional[LessonPlanDocument]:
        if not ObjectId.is_valid(plan_id):
            return None
        subtopic_dict = subtopic.model_dump()
        result = await self._col.find_one_and_update(
            {"_id": ObjectId(plan_id)},
            {
                "$push": {"chapters.$[ch].topics.$[tp].subtopics": subtopic_dict},
                "$set": {"updated_at": datetime.utcnow(), "updated_by": updated_by},
            },
            array_filters=[
                {"ch.chapter_id": chapter_id},
                {"tp.topic_id": topic_id},
            ],
            return_document=True,
        )
        return self._to_model(result) if result else None

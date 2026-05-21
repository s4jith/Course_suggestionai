
from datetime import datetime
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.lesson_plan import SubjectDocument

class SubjectRepository:

    COLLECTION = "subjects"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db[self.COLLECTION]

    @staticmethod
    def _to_model(doc: dict) -> SubjectDocument:
        return SubjectDocument(**doc)

    async def find_by_id(self, subject_id: str) -> Optional[SubjectDocument]:
        if not ObjectId.is_valid(subject_id):
            return None
        doc = await self._col.find_one({"_id": ObjectId(subject_id)})
        return self._to_model(doc) if doc else None

    async def find_by_code(self, code: str) -> Optional[SubjectDocument]:
        doc = await self._col.find_one({"code": code.upper()})
        return self._to_model(doc) if doc else None

    async def code_exists(self, code: str) -> bool:
        return await self._col.count_documents({"code": code.upper()}, limit=1) > 0

    async def list_subjects(
        self,
        department: Optional[str] = None,
        semester: Optional[int] = None,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 20,
    ) -> list[SubjectDocument]:
        query: dict = {}
        if department:
            query["department"] = {"$regex": department, "$options": "i"}
        if semester is not None:
            query["semester"] = semester
        if is_active is not None:
            query["is_active"] = is_active

        cursor = self._col.find(query).skip(skip).limit(limit).sort("name", 1)
        docs = await cursor.to_list(length=limit)
        return [self._to_model(d) for d in docs]

    async def count_subjects(
        self,
        department: Optional[str] = None,
        semester: Optional[int] = None,
        is_active: Optional[bool] = True,
    ) -> int:
        query: dict = {}
        if department:
            query["department"] = {"$regex": department, "$options": "i"}
        if semester is not None:
            query["semester"] = semester
        if is_active is not None:
            query["is_active"] = is_active
        return await self._col.count_documents(query)

    async def create(self, doc: SubjectDocument) -> SubjectDocument:
        payload = doc.model_dump(by_alias=True, exclude={"id"})
        result = await self._col.insert_one(payload)
        doc.id = result.inserted_id
        return doc

    async def update(self, subject_id: str, updates: dict) -> Optional[SubjectDocument]:
        if not ObjectId.is_valid(subject_id):
            return None
        updates["updated_at"] = datetime.utcnow()
        result = await self._col.find_one_and_update(
            {"_id": ObjectId(subject_id)},
            {"$set": updates},
            return_document=True,
        )
        return self._to_model(result) if result else None

    async def deactivate(self, subject_id: str) -> bool:
        if not ObjectId.is_valid(subject_id):
            return False
        result = await self._col.update_one(
            {"_id": ObjectId(subject_id)},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
        )
        return result.modified_count == 1

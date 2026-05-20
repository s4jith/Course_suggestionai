"""
User repository – all MongoDB I/O operations for the users collection.

The repository pattern keeps database access isolated from business logic,
making it easy to swap the underlying store or write unit tests with mocks.
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.user import UserDocument, UserRole


class UserRepository:
    """Async repository for the `users` MongoDB collection."""

    COLLECTION = "users"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db[self.COLLECTION]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _doc_to_model(doc: dict) -> UserDocument:
        """Convert a raw MongoDB document dict to a UserDocument instance."""
        return UserDocument(**doc)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def find_by_id(self, user_id: str) -> Optional[UserDocument]:
        """Return a user by their ObjectId string, or None if not found."""
        if not ObjectId.is_valid(user_id):
            return None
        doc = await self._col.find_one({"_id": ObjectId(user_id)})
        return self._doc_to_model(doc) if doc else None

    async def find_by_email(self, email: str) -> Optional[UserDocument]:
        """Return a user by their email address (case-insensitive), or None."""
        doc = await self._col.find_one({"email": email.lower().strip()})
        return self._doc_to_model(doc) if doc else None

    async def email_exists(self, email: str) -> bool:
        """Return True if a user with the given email already exists."""
        count = await self._col.count_documents({"email": email.lower().strip()}, limit=1)
        return count > 0

    async def list_users(
        self,
        role: Optional[UserRole] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[UserDocument]:
        """
        Return a paginated list of users, optionally filtered by role.

        Args:
            role:  If provided, filter to users with this role.
            skip:  Number of documents to skip (for pagination).
            limit: Maximum number of documents to return.
        """
        query: dict = {}
        if role is not None:
            query["role"] = role.value

        cursor = self._col.find(query).skip(skip).limit(limit).sort("created_at", -1)
        docs = await cursor.to_list(length=limit)
        return [self._doc_to_model(d) for d in docs]

    async def count_users(self, role: Optional[UserRole] = None) -> int:
        """Return the total number of users, optionally filtered by role."""
        query: dict = {}
        if role is not None:
            query["role"] = role.value
        return await self._col.count_documents(query)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create(self, user_doc: UserDocument) -> UserDocument:
        """
        Insert a new user document.

        Args:
            user_doc: A fully-populated UserDocument (without _id).

        Returns:
            The same document with its new _id populated.
        """
        # Normalise email before storage
        user_doc.email = user_doc.email.lower().strip()

        payload = user_doc.model_dump(by_alias=True, exclude={"id"})
        result = await self._col.insert_one(payload)
        user_doc.id = result.inserted_id
        return user_doc

    async def update_profile(
        self,
        user_id: str,
        updates: dict,
    ) -> Optional[UserDocument]:
        """
        Apply a partial update to a user document.

        Args:
            user_id: The user's ObjectId string.
            updates: A dict of fields to set (e.g. {"full_name": "Alice"}).

        Returns:
            The updated UserDocument, or None if the user was not found.
        """
        if not ObjectId.is_valid(user_id):
            return None

        updates["updated_at"] = datetime.utcnow()
        result = await self._col.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": updates},
            return_document=True,  # Return the document AFTER the update
        )
        return self._doc_to_model(result) if result else None

    async def update_password(self, user_id: str, hashed_password: str) -> bool:
        """
        Replace the stored password hash for a user.

        Returns:
            True if the update was applied; False if the user was not found.
        """
        if not ObjectId.is_valid(user_id):
            return False
        result = await self._col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"hashed_password": hashed_password, "updated_at": datetime.utcnow()}},
        )
        return result.modified_count == 1

    async def deactivate(self, user_id: str) -> bool:
        """
        Soft-delete a user by setting is_active = False.

        Returns:
            True if the update was applied; False if the user was not found.
        """
        if not ObjectId.is_valid(user_id):
            return False
        result = await self._col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
        )
        return result.modified_count == 1

"""
User domain model – represents the document structure stored in MongoDB.

Note: These are NOT Pydantic models for request/response validation.
      For that, see app/schemas/user.py.
      These classes are used by the repository layer to map raw MongoDB
      documents to typed Python objects.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr


class UserRole(str, Enum):
    """Supported roles in the RBAC system."""
    ADMIN = "admin"
    TEACHER = "teacher"


class PyObjectId(ObjectId):
    """
    Custom type that lets Pydantic serialise MongoDB's ObjectId to a string.
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError(f"Invalid ObjectId: {v}")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.no_info_plain_validator_function(
            cls.validate,
            serialization=core_schema.to_string_ser_schema(),
        )


class UserDocument(BaseModel):
    """
    Represents a user document as stored in MongoDB.
    The `id` field maps to MongoDB's `_id` field via the alias.
    """

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    email: EmailStr
    full_name: str
    hashed_password: str
    role: UserRole = UserRole.TEACHER
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Name of the MongoDB collection this document belongs to
    class Collection:
        name = "users"

    class Config:
        # Allow population by field name AND by alias (_id)
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

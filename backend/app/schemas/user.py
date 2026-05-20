"""
Pydantic schemas for User request/response validation.

Separation of concerns:
  - UserCreate   → body of POST /register
  - UserLogin    → body of POST /login
  - UserResponse → safe public projection (no password)
  - UserUpdate   → body of PATCH /users/me
"""

import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.user import UserRole


# ---------------------------------------------------------------------------
# Inbound (request) schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    """Payload for creating a new user account."""

    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.TEACHER

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """
        Enforce a minimum password policy:
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character.")
        return v

    @field_validator("full_name")
    @classmethod
    def sanitise_name(cls, v: str) -> str:
        return v.strip()


class UserLogin(BaseModel):
    """Payload for authenticating an existing user."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class UserUpdate(BaseModel):
    """Payload for partially updating the current user's profile."""

    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None


# ---------------------------------------------------------------------------
# Outbound (response) schemas
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    """
    Safe public representation of a user – never includes password hash.
    `id` is the string-serialised MongoDB ObjectId.
    """

    id: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

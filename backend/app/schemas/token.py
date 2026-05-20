"""
Pydantic schemas for JWT token request/response objects.
"""

from typing import Optional
from pydantic import BaseModel
from app.models.user import UserRole


class TokenResponse(BaseModel):
    """Returned to the client after a successful login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until the access token expires


class TokenData(BaseModel):
    """
    The claims extracted from a decoded JWT payload.
    Used internally by authentication dependencies.
    """

    sub: str               # Subject – the user's string ObjectId
    email: Optional[str] = None
    role: Optional[UserRole] = None
    token_type: str = "access"  # "access" | "refresh"


class RefreshTokenRequest(BaseModel):
    """Body payload for the token-refresh endpoint."""

    refresh_token: str

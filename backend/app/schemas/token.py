
from typing import Optional
from pydantic import BaseModel
from app.models.user import UserRole

class TokenResponse(BaseModel):

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):

    sub: str
    email: Optional[str] = None
    role: Optional[UserRole] = None
    token_type: str = "access"

class RefreshTokenRequest(BaseModel):

    refresh_token: str

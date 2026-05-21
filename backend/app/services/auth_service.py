
from datetime import timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.jwt_handler import create_access_token, create_refresh_token, decode_token
from app.config.settings import settings
from app.core.exceptions import (
    AlreadyExistsException,
    CredentialsException,
    NotFoundException,
)
from app.models.user import UserDocument
from app.repositories.user_repository import UserRepository
from app.schemas.token import TokenResponse
from app.schemas.user import UserCreate, UserResponse
from app.utils.password import hash_password, needs_rehash, verify_password

def _user_to_response(user: UserDocument) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )

def _build_token_response(user: UserDocument) -> TokenResponse:
    user_id = str(user.id)
    access_token = create_access_token(
        subject=user_id,
        email=user.email,
        role=user.role,
    )
    refresh_token = create_refresh_token(
        subject=user_id,
        email=user.email,
        role=user.role,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

class AuthService:

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._repo = UserRepository(db)

    async def register(self, payload: UserCreate) -> UserResponse:
        if await self._repo.email_exists(payload.email):
            raise AlreadyExistsException("Email address")

        new_user = UserDocument(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role=payload.role,
        )
        created = await self._repo.create(new_user)
        return _user_to_response(created)

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self._repo.find_by_email(email)

        if user is None or not verify_password(password, user.hashed_password):
            raise CredentialsException("Invalid email or password.")

        if not user.is_active:
            raise CredentialsException("Account is deactivated. Contact an administrator.")

        if needs_rehash(user.hashed_password):
            await self._repo.update_password(str(user.id), hash_password(password))

        return _build_token_response(user)

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        token_data = decode_token(refresh_token, expected_type="refresh")
        user = await self._repo.find_by_id(token_data.sub)

        if user is None:
            raise NotFoundException("User")
        if not user.is_active:
            raise CredentialsException("Account is deactivated.")

        return _build_token_response(user)

    async def get_profile(self, user: UserDocument) -> UserResponse:
        return _user_to_response(user)

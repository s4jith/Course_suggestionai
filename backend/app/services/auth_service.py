"""
Authentication service – orchestrates registration, login, and token refresh.

Business logic lives here, not in the route handlers or the repository.
"""

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
    """Map a UserDocument to the public-facing UserResponse schema."""
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
    """Create access + refresh tokens for a user and wrap them in TokenResponse."""
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
    """Handles user registration, login, and token lifecycle."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._repo = UserRepository(db)

    async def register(self, payload: UserCreate) -> UserResponse:
        """
        Register a new user account.

        Raises:
            AlreadyExistsException: If the email is already registered.
        """
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
        """
        Authenticate a user and return JWT access + refresh tokens.

        Raises:
            CredentialsException: If the email or password is invalid,
                                  or the account is deactivated.
        """
        user = await self._repo.find_by_email(email)

        # Use a constant-time comparison via passlib – avoids timing attacks.
        if user is None or not verify_password(password, user.hashed_password):
            raise CredentialsException("Invalid email or password.")

        if not user.is_active:
            raise CredentialsException("Account is deactivated. Contact an administrator.")

        # Opportunistically upgrade the password hash if bcrypt rounds changed.
        if needs_rehash(user.hashed_password):
            await self._repo.update_password(str(user.id), hash_password(password))

        return _build_token_response(user)

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """
        Issue a fresh access + refresh token pair using a valid refresh token.

        Raises:
            TokenExpiredException:  If the refresh token has expired.
            CredentialsException:   If the token is invalid or the user is gone.
            NotFoundException:      If the user no longer exists.
        """
        token_data = decode_token(refresh_token, expected_type="refresh")
        user = await self._repo.find_by_id(token_data.sub)

        if user is None:
            raise NotFoundException("User")
        if not user.is_active:
            raise CredentialsException("Account is deactivated.")

        return _build_token_response(user)

    async def get_profile(self, user: UserDocument) -> UserResponse:
        """Return the public profile for an already-authenticated user."""
        return _user_to_response(user)

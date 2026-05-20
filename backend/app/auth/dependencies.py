"""
FastAPI dependency functions for authentication and authorisation.

Usage in route handlers:

    # Any authenticated user
    current_user = Depends(get_current_active_user)

    # Admin-only endpoint
    admin_user = Depends(require_admin)

    # Teacher-or-Admin endpoint
    teacher_user = Depends(require_teacher)
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt_handler import decode_token
from app.core.exceptions import (
    CredentialsException,
    InsufficientPermissionsException,
    NotFoundException,
)
from app.database.mongodb import get_database
from app.models.user import UserDocument, UserRole
from app.repositories.user_repository import UserRepository
from motor.motor_asyncio import AsyncIOMotorDatabase

# HTTPBearer extracts the token from the "Authorization: Bearer <token>" header.
_bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> UserDocument:
    """
    Core authentication dependency.

    1. Extracts the Bearer token from the Authorization header.
    2. Decodes and validates the JWT.
    3. Loads the corresponding user from MongoDB.
    4. Returns the UserDocument for use inside the route handler.
    """
    token_data = decode_token(credentials.credentials, expected_type="access")

    repo = UserRepository(db)
    user = await repo.find_by_id(token_data.sub)
    if user is None:
        raise NotFoundException("User")

    return user


async def get_current_active_user(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
) -> UserDocument:
    """
    Extends get_current_user to also verify the account is not deactivated.
    """
    if not current_user.is_active:
        raise CredentialsException("User account is deactivated.")
    return current_user


def require_role(*roles: UserRole):
    """
    Factory that returns a dependency enforcing one of the specified roles.

    Example:
        Depends(require_role(UserRole.ADMIN, UserRole.TEACHER))
    """

    async def role_checker(
        current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    ) -> UserDocument:
        if current_user.role not in roles:
            raise InsufficientPermissionsException(
                required_role=" or ".join(r.value for r in roles)
            )
        return current_user

    return role_checker


# ---------------------------------------------------------------------------
# Convenience aliases for common role checks
# ---------------------------------------------------------------------------

require_admin = require_role(UserRole.ADMIN)
require_teacher = require_role(UserRole.TEACHER, UserRole.ADMIN)

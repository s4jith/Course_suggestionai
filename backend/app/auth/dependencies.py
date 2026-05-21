
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

_bearer_scheme = HTTPBearer(auto_error=True)

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> UserDocument:
    token_data = decode_token(credentials.credentials, expected_type="access")

    repo = UserRepository(db)
    user = await repo.find_by_id(token_data.sub)
    if user is None:
        raise NotFoundException("User")

    return user

async def get_current_active_user(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
) -> UserDocument:
    if not current_user.is_active:
        raise CredentialsException("User account is deactivated.")
    return current_user

def require_role(*roles: UserRole):

    async def role_checker(
        current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    ) -> UserDocument:
        if current_user.role not in roles:
            raise InsufficientPermissionsException(
                required_role=" or ".join(r.value for r in roles)
            )
        return current_user

    return role_checker

require_admin = require_role(UserRole.ADMIN)
require_teacher = require_role(UserRole.TEACHER, UserRole.ADMIN)

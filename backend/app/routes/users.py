"""
User management routes – admin-only operations on user accounts.

All routes live under the /api/v1/users prefix (configured in main.py).
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_active_user, require_admin, require_teacher
from app.core.exceptions import NotFoundException
from app.core.responses import PaginatedResponse, SuccessResponse, success_response
from app.database.mongodb import get_database
from app.models.user import UserDocument, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_repo(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> UserRepository:
    return UserRepository(db)


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=PaginatedResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="[Admin] List all users with optional role filter",
)
async def list_users(
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    _: Annotated[UserDocument, Depends(require_admin)] = None,
    repo: Annotated[UserRepository, Depends(get_user_repo)] = None,
):
    """
    **Admin only** – Paginated list of all user accounts.
    Optionally filter by `role` (teacher | admin).
    """
    skip = (page - 1) * page_size
    users = await repo.list_users(role=role, skip=skip, limit=page_size)
    total = await repo.count_users(role=role)
    total_pages = -(-total // page_size)  # Ceiling division

    return PaginatedResponse(
        data=[
            UserResponse(
                id=str(u.id),
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                is_active=u.is_active,
                is_verified=u.is_verified,
                created_at=u.created_at,
                updated_at=u.updated_at,
            )
            for u in users
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{user_id}",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="[Admin] Get a specific user by ID",
)
async def get_user(
    user_id: str,
    _: Annotated[UserDocument, Depends(require_admin)] = None,
    repo: Annotated[UserRepository, Depends(get_user_repo)] = None,
):
    """**Admin only** – Retrieve a user by their MongoDB ObjectId string."""
    user = await repo.find_by_id(user_id)
    if user is None:
        raise NotFoundException("User")

    return success_response(
        data=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
        message="User retrieved successfully.",
    )


@router.delete(
    "/{user_id}/deactivate",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Deactivate a user account",
)
async def deactivate_user(
    user_id: str,
    _: Annotated[UserDocument, Depends(require_admin)] = None,
    repo: Annotated[UserRepository, Depends(get_user_repo)] = None,
):
    """**Admin only** – Soft-delete (deactivate) a user account."""
    success = await repo.deactivate(user_id)
    if not success:
        raise NotFoundException("User")
    return success_response(message="User account deactivated successfully.")


# ---------------------------------------------------------------------------
# Teacher / self-service endpoints
# ---------------------------------------------------------------------------

@router.patch(
    "/me",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="[Teacher/Admin] Update the current user's profile",
)
async def update_my_profile(
    payload: UserUpdate,
    current_user: Annotated[UserDocument, Depends(require_teacher)],
    repo: Annotated[UserRepository, Depends(get_user_repo)] = None,
):
    """
    Update own profile fields (full_name, email).
    Teachers and Admins can access this endpoint.
    """
    # Only include non-None fields in the update payload
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        return success_response(
            data=UserResponse(
                id=str(current_user.id),
                email=current_user.email,
                full_name=current_user.full_name,
                role=current_user.role,
                is_active=current_user.is_active,
                is_verified=current_user.is_verified,
                created_at=current_user.created_at,
                updated_at=current_user.updated_at,
            ),
            message="No changes provided.",
        )

    updated = await repo.update_profile(str(current_user.id), updates)
    if updated is None:
        raise NotFoundException("User")

    return success_response(
        data=UserResponse(
            id=str(updated.id),
            email=updated.email,
            full_name=updated.full_name,
            role=updated.role,
            is_active=updated.is_active,
            is_verified=updated.is_verified,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        ),
        message="Profile updated successfully.",
    )

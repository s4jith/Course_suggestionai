"""
Subject routes – CRUD for the `subjects` collection.

All routes live under the /api/v1/subjects prefix (configured in main.py).

Permissions:
  - GET  endpoints: any authenticated active user
  - POST / PATCH / DELETE: teacher or admin
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_active_user, require_teacher
from app.core.responses import PaginatedResponse, SuccessResponse, success_response
from app.database.mongodb import get_database
from app.models.user import UserDocument
from app.schemas.lesson_plan import SubjectCreate, SubjectResponse, SubjectUpdate
from app.services.lesson_plan_service import LessonPlanService

router = APIRouter(prefix="/subjects", tags=["Subjects"])


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_service(db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]) -> LessonPlanService:
    return LessonPlanService(db)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=SuccessResponse[SubjectResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new subject",
)
async def create_subject(
    payload: SubjectCreate,
    current_user: Annotated[UserDocument, Depends(require_teacher)],
    service: Annotated[LessonPlanService, Depends(get_service)],
):
    """
    Create a new academic subject.
    Subject codes are unique and automatically upper-cased.

    **Example request:**
    ```json
    {
      "name": "Data Structures",
      "code": "CS301",
      "description": "Fundamental data structures and algorithms",
      "department": "Computer Science",
      "semester": 3,
      "total_hours": 60
    }
    ```
    """
    subject = await service.create_subject(payload, current_user)
    return success_response(data=subject, message="Subject created successfully.")


@router.get(
    "/",
    response_model=PaginatedResponse[SubjectResponse],
    status_code=status.HTTP_200_OK,
    summary="List subjects with optional filters",
)
async def list_subjects(
    department: Optional[str] = Query(None, description="Filter by department (partial match)"),
    semester: Optional[int] = Query(None, ge=1, le=10, description="Filter by semester"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    _: Annotated[UserDocument, Depends(get_current_active_user)] = None,
    service: Annotated[LessonPlanService, Depends(get_service)] = None,
):
    """Return a paginated list of subjects, optionally filtered by department, semester, or active status."""
    skip = (page - 1) * page_size
    subjects, total = await service.list_subjects(department, semester, is_active, skip, page_size)
    return PaginatedResponse(
        data=subjects,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=-(-total // page_size),
    )


@router.get(
    "/{subject_id}",
    response_model=SuccessResponse[SubjectResponse],
    status_code=status.HTTP_200_OK,
    summary="Get a subject by ID",
)
async def get_subject(
    subject_id: str,
    _: Annotated[UserDocument, Depends(get_current_active_user)] = None,
    service: Annotated[LessonPlanService, Depends(get_service)] = None,
):
    subject = await service.get_subject(subject_id)
    return success_response(data=subject, message="Subject retrieved successfully.")


@router.patch(
    "/{subject_id}",
    response_model=SuccessResponse[SubjectResponse],
    status_code=status.HTTP_200_OK,
    summary="Update a subject",
)
async def update_subject(
    subject_id: str,
    payload: SubjectUpdate,
    current_user: Annotated[UserDocument, Depends(require_teacher)],
    service: Annotated[LessonPlanService, Depends(get_service)],
):
    updated = await service.update_subject(subject_id, payload, current_user)
    return success_response(data=updated, message="Subject updated successfully.")


@router.delete(
    "/{subject_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Deactivate a subject",
)
async def deactivate_subject(
    subject_id: str,
    current_user: Annotated[UserDocument, Depends(require_teacher)],
    service: Annotated[LessonPlanService, Depends(get_service)],
):
    """Soft-delete a subject by setting is_active = False."""
    await service.deactivate_subject(subject_id)
    return success_response(message="Subject deactivated successfully.")

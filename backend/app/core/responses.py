"""
Standardised API response wrappers.
All endpoints return one of these models so clients get a consistent envelope.
"""

from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Envelope for successful API responses."""

    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[T] = None

    class Config:
        # Allow arbitrary types inside the generic so nested Pydantic models work
        arbitrary_types_allowed = True


class ErrorResponse(BaseModel):
    """Envelope for error API responses."""

    success: bool = False
    error_code: str
    message: str
    detail: Optional[Any] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope for paginated list responses."""

    success: bool = True
    message: str = "Data retrieved successfully"
    data: list[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0


def success_response(data: Any = None, message: str = "Operation completed successfully") -> dict:
    """Utility to build a plain-dict success envelope (used in route handlers)."""
    return {"success": True, "message": message, "data": data}


def error_response(error_code: str, message: str, detail: Any = None) -> dict:
    """Utility to build a plain-dict error envelope."""
    return {"success": False, "error_code": error_code, "message": message, "detail": detail}

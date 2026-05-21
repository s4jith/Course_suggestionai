
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class SuccessResponse(BaseModel, Generic[T]):

    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[T] = None

    class Config:
        arbitrary_types_allowed = True

class ErrorResponse(BaseModel):

    success: bool = False
    error_code: str
    message: str
    detail: Optional[Any] = None

class PaginatedResponse(BaseModel, Generic[T]):

    success: bool = True
    message: str = "Data retrieved successfully"
    data: list[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0

def success_response(data: Any = None, message: str = "Operation completed successfully") -> dict:
    return {"success": True, "message": message, "data": data}

def error_response(error_code: str, message: str, detail: Any = None) -> dict:
    return {"success": False, "error_code": error_code, "message": message, "detail": detail}

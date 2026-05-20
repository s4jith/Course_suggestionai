"""
Custom application exceptions.
Each exception maps to a specific HTTP status code and a
machine-readable error code that clients can act on.
"""

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base class for all application-level HTTP exceptions."""

    def __init__(self, status_code: int, detail: str, error_code: str = "APP_ERROR"):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


# -------------------------------------------------------------------------
# Authentication / Authorisation
# -------------------------------------------------------------------------

class CredentialsException(AppException):
    """Raised when JWT credentials are invalid or expired."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="INVALID_CREDENTIALS",
        )


class TokenExpiredException(AppException):
    """Raised when a JWT token has expired."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            error_code="TOKEN_EXPIRED",
        )


class InsufficientPermissionsException(AppException):
    """Raised when the authenticated user lacks the required role."""

    def __init__(self, required_role: str = ""):
        detail = f"Insufficient permissions. Required role: {required_role}" if required_role else "Insufficient permissions"
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="INSUFFICIENT_PERMISSIONS",
        )


# -------------------------------------------------------------------------
# Resource
# -------------------------------------------------------------------------

class NotFoundException(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found",
            error_code="NOT_FOUND",
        )


class AlreadyExistsException(AppException):
    """Raised when trying to create a resource that already exists."""

    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{resource} already exists",
            error_code="ALREADY_EXISTS",
        )


class ValidationException(AppException):
    """Raised for domain-level validation errors."""

    def __init__(self, detail: str = "Validation error"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR",
        )


# -------------------------------------------------------------------------
# Infrastructure
# -------------------------------------------------------------------------

class DatabaseException(AppException):
    """Raised on unrecoverable database errors."""

    def __init__(self, detail: str = "Database error occurred"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="DATABASE_ERROR",
        )


from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.config.settings import settings
from app.core.exceptions import CredentialsException, TokenExpiredException
from app.schemas.token import TokenData
from app.models.user import UserRole

def _build_payload(
    subject: str,
    email: str,
    role: UserRole,
    token_type: str,
    expires_delta: timedelta,
) -> dict:
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    return {
        "sub": subject,
        "email": email,
        "role": role.value,
        "token_type": token_type,
        "iat": now,
        "exp": expire,
    }

def create_access_token(subject: str, email: str, role: UserRole) -> str:
    payload = _build_payload(
        subject=subject,
        email=email,
        role=role,
        token_type="access",
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(subject: str, email: str, role: UserRole) -> str:
    payload = _build_payload(
        subject=subject,
        email=email,
        role=role,
        token_type="refresh",
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str, expected_type: str = "access") -> TokenData:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        if "expired" in str(exc).lower():
            raise TokenExpiredException()
        raise CredentialsException() from exc

    subject: Optional[str] = payload.get("sub")
    token_type: str = payload.get("token_type", "")

    if subject is None:
        raise CredentialsException("Token is missing subject claim.")

    if token_type != expected_type:
        raise CredentialsException(
            f"Invalid token type. Expected '{expected_type}', got '{token_type}'."
        )

    return TokenData(
        sub=subject,
        email=payload.get("email"),
        role=UserRole(payload["role"]) if payload.get("role") else None,
        token_type=token_type,
    )

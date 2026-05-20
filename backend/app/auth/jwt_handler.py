"""
JWT token generation and verification.

Handles:
- Access token creation  (short-lived, e.g. 30 min)
- Refresh token creation (long-lived, e.g. 7 days)
- Token decoding / validation
"""

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
    """Assemble the JWT payload dict."""
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
    """
    Create a short-lived JWT access token.

    Args:
        subject:  The user's string ObjectId (used as the JWT `sub` claim).
        email:    The user's email address (informational claim).
        role:     The user's role (used by RBAC dependencies).

    Returns:
        A signed JWT string.
    """
    payload = _build_payload(
        subject=subject,
        email=email,
        role=role,
        token_type="access",
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, email: str, role: UserRole) -> str:
    """
    Create a long-lived JWT refresh token.
    Refresh tokens carry a different `token_type` so they cannot be
    used directly as access tokens.
    """
    payload = _build_payload(
        subject=subject,
        email=email,
        role=role,
        token_type="refresh",
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> TokenData:
    """
    Decode and validate a JWT token.

    Args:
        token:          The raw JWT string from the Authorization header.
        expected_type:  Either "access" or "refresh".

    Returns:
        A TokenData instance populated from the JWT claims.

    Raises:
        TokenExpiredException:    If the token's `exp` claim has passed.
        CredentialsException:     For any other invalid-token condition.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        # Distinguish expiry from other errors for a clearer client message
        if "expired" in str(exc).lower():
            raise TokenExpiredException()
        raise CredentialsException() from exc

    # Validate required claims
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

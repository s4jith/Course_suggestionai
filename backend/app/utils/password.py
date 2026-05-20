"""
Password hashing and verification utilities.
Uses passlib with bcrypt as the hashing algorithm.
"""

from passlib.context import CryptContext
from app.config.settings import settings

# CryptContext centralises algorithm selection.
# "deprecated='auto'" will automatically mark weaker hashes for re-hashing.
_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS,
)


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    Args:
        plain_password: The raw password string from the user.

    Returns:
        A bcrypt-hashed string safe to store in the database.
    """
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against its stored bcrypt hash.

    Args:
        plain_password:  The raw password provided during login.
        hashed_password: The bcrypt hash stored in the database.

    Returns:
        True if the password matches; False otherwise.
    """
    return _pwd_context.verify(plain_password, hashed_password)


def needs_rehash(hashed_password: str) -> bool:
    """
    Check whether a stored hash should be upgraded (e.g. after increasing bcrypt rounds).

    Returns:
        True if the hash uses deprecated settings and should be updated on next login.
    """
    return _pwd_context.needs_update(hashed_password)

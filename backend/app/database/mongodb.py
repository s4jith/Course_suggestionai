"""
Async MongoDB connection management using Motor.

Provides:
- A singleton MongoClient that is created on application startup
  and closed on shutdown (lifespan context manager pattern).
- A get_database() dependency for injecting the database handle
  into route handlers and repositories.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Module-level client reference – populated by connect_db() / closed by close_db()
_client: AsyncIOMotorClient | None = None


async def connect_db() -> None:
    """
    Create the Motor async client and verify connectivity with a ping command.
    Called once on application startup via the FastAPI lifespan hook.
    """
    global _client
    logger.info("Connecting to MongoDB at %s …", settings.MONGODB_URL)
    _client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        # Use a generous server-selection timeout so startup fails fast
        # rather than hanging if MongoDB is unreachable.
        serverSelectionTimeoutMS=5000,
    )
    # Ping to confirm the connection is usable before accepting traffic.
    await _client.admin.command("ping")
    logger.info("MongoDB connection established. Database: %s", settings.MONGODB_DB_NAME)


async def close_db() -> None:
    """
    Close the Motor client.
    Called once on application shutdown via the FastAPI lifespan hook.
    """
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    """
    FastAPI dependency – returns the active database handle.

    Usage in a route:
        db: AsyncIOMotorDatabase = Depends(get_database)
    """
    if _client is None:
        raise RuntimeError("Database client is not initialised. Did startup complete?")
    return _client[settings.MONGODB_DB_NAME]

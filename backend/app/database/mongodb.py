

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None

async def connect_db() -> None:
    global _client
    logger.info("Connecting to MongoDB at %s …", settings.MONGODB_URL)
    _client = AsyncIOMotorClient(
        settings.MONGODB_URL,
   
        serverSelectionTimeoutMS=5000,
    )
    
    await _client.admin.command("ping")
    logger.info("MongoDB connection established. Database: %s", settings.MONGODB_DB_NAME)

async def close_db() -> None:

    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed.")

def get_database() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("Database client is not initialised. Did startup complete?")
    return _client[settings.MONGODB_DB_NAME]

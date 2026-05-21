
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "Academic Lesson Plan API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-powered academic lesson plan management system"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080", "http://localhost:4200"]

    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "lesson_plan_db"

    JWT_SECRET_KEY: str = "change-this-to-a-strong-random-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    BCRYPT_ROUNDS: int = 12

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral:7b"
    OLLAMA_TIMEOUT: int = 60
    OLLAMA_ENABLED: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()


import logging
import logging.config
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.responses import error_response, success_response
from app.database.mongodb import close_db, connect_db
from app.middleware.logging_middleware import LoggingMiddleware
from app.routes import auth as auth_router
from app.routes import users as users_router
from app.routes import subjects as subjects_router
from app.routes import lesson_plans as lesson_plans_router
from app.routes import topic_progress as topic_progress_router
from app.routes import ai_recommendations as ai_router
from app.routes import analytics as analytics_router

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "DEBUG" if settings.DEBUG else "INFO",
        "handlers": ["console"],
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting up %s v%s [%s]", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)
    await connect_db()
    yield
    logger.info("Shutting down – closing database connection …")
    await close_db()

def create_app() -> FastAPI:

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(LoggingMiddleware)

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                error_code=exc.error_code,
                message=exc.detail,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        sanitised = []
        for err in exc.errors():
            clean = dict(err)
            if "ctx" in clean:
                clean["ctx"] = {k: str(v) for k, v in clean["ctx"].items()}
            sanitised.append(clean)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response(
                error_code="VALIDATION_ERROR",
                message="Request validation failed.",
                detail=sanitised,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                error_code="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred. Please try again later.",
            ),
        )

    app.include_router(auth_router.router, prefix=settings.API_V1_PREFIX)
    app.include_router(users_router.router, prefix=settings.API_V1_PREFIX)
    app.include_router(subjects_router.router, prefix=settings.API_V1_PREFIX)
    app.include_router(lesson_plans_router.router, prefix=settings.API_V1_PREFIX)
    app.include_router(topic_progress_router.router, prefix=settings.API_V1_PREFIX)
    app.include_router(ai_router.router, prefix=settings.API_V1_PREFIX)
    app.include_router(analytics_router.router, prefix=settings.API_V1_PREFIX)

    @app.get(
        "/health",
        tags=["Health"],
        summary="Application health check",
        status_code=status.HTTP_200_OK,
    )
    async def health_check():
        return success_response(
            data={
                "app": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "environment": settings.ENVIRONMENT,
                "status": "healthy",
            },
            message="Service is healthy.",
        )

    return app

app = create_app()

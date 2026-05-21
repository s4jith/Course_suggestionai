
from typing import Annotated

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_active_user
from app.core.responses import SuccessResponse, success_response
from app.database.mongodb import get_database
from app.models.user import UserDocument
from app.schemas.token import RefreshTokenRequest, TokenResponse
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_auth_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> AuthService:
    return AuthService(db)

@router.post(
    "/register",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: UserCreate,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    user = await service.register(payload)
    return success_response(data=user, message="Account created successfully.")

@router.post(
    "/login",
    response_model=SuccessResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive JWT tokens",
)
async def login(
    payload: UserLogin,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    tokens = await service.login(payload.email, payload.password)
    return success_response(data=tokens, message="Login successful.")

@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Refresh access token using a refresh token",
)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    tokens = await service.refresh_tokens(payload.refresh_token)
    return success_response(data=tokens, message="Tokens refreshed successfully.")

@router.get(
    "/me",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get the current authenticated user's profile",
)
async def get_me(
    current_user: Annotated[UserDocument, Depends(get_current_active_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    profile = await service.get_profile(current_user)
    return success_response(data=profile, message="Profile retrieved successfully.")

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenRefresh
from app.services.auth_service import AuthService
from app.utils.response import success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Bearer scheme for logout endpoint
bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account
    """
    user = AuthService.register_user(db, user_data)

    return success_response(
        data={
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role
            }
        },
        message="User registered successfully. Please login to get access tokens.",
        status_code=status.HTTP_201_CREATED
    )


@router.post("/login", response_model=dict)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login user and get access + refresh tokens
    """
    user, access_token, refresh_token = AuthService.login_user(db, login_data)

    return success_response(
        data={
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        },
        message="Login successful"
    )


@router.post("/refresh", response_model=dict)
async def refresh_token(
    refresh_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    Old refresh token is blacklisted after use (token rotation).
    """
    access_token, refresh_token = AuthService.refresh_access_token(
        db, refresh_data.refresh_token
    )

    return success_response(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        },
        message="Token refreshed successfully"
    )


@router.post("/logout", response_model=dict)
async def logout(
    refresh_data: Optional[TokenRefresh] = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Logout user. Blacklists access token and optionally refresh token.
    Send refresh_token in body to invalidate it as well.
    """
    # Extract access token from Authorization header
    access_token = credentials.credentials if credentials else None

    # Extract refresh token from body if provided
    refresh_token = refresh_data.refresh_token if refresh_data else None

    result = AuthService.logout_user(
        db=db,
        access_token=access_token,
        refresh_token=refresh_token
    )

    return success_response(
        data=result,
        message="Logout successful"
    )
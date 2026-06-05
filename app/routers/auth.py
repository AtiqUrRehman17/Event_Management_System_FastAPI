from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, Token, TokenRefresh, TokenResponse, LogoutResponse
from app.services.auth_service import AuthService
from app.utils.response import success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account
    Returns user data without tokens
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
    Login user and get access token
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
    Refresh access token using refresh token
    """
    access_token, refresh_token = AuthService.refresh_access_token(db, refresh_data.refresh_token)
    
    return success_response(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        },
        message="Token refreshed successfully"
    )


@router.post("/logout", response_model=dict)
async def logout():
    """
    Logout user (client should discard tokens)
    """
    result = AuthService.logout_user()
    return success_response(data=result, message="Logout successful")
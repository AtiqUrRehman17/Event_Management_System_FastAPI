from fastapi import APIRouter, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, 
    RegisterRequest, 
    TokenRefresh,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    EmailVerificationRequest,
    ResendVerificationRequest
)
from app.services.auth_service import AuthService
from app.utils.response import success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])

bearer_scheme = HTTPBearer(auto_error=False)


# This is needed for oauth.py to access
def build_user_info(user: User) -> dict:
    """Build user info dict to include in JWT token"""
    return {
        "username": user.username,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
    }


# Make it available as a static method reference
AuthService._build_user_info = staticmethod(build_user_info)


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user account."""
    user = AuthService.register_user(db, user_data)

    return success_response(
        data={
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "is_verified": user.is_verified
            },
            "message": "A verification email has been sent to your email address."
        },
        message="User registered successfully. Please check your email for verification link.",
        status_code=status.HTTP_201_CREATED
    )


@router.post("/verify-email", response_model=dict)
async def verify_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """Verify user's email address using verification token."""
    result = AuthService.verify_email(db, request.token)
    return success_response(
        data=result,
        message=result["message"]
    )


@router.post("/resend-verification", response_model=dict)
async def resend_verification(
    request: ResendVerificationRequest,
    db: Session = Depends(get_db)
):
    """Resend verification email to user."""
    result = AuthService.resend_verification_email(db, request.email)
    return success_response(
        data=result,
        message=result["message"]
    )


@router.post("/login", response_model=dict)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login using username and password."""
    user, access_token, refresh_token = AuthService.login_user(db, login_data)

    return success_response(
        data={
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "is_verified": user.is_verified
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        },
        message="Login successful"
    )


@router.post("/forgot-password", response_model=dict)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """Request password reset."""
    result = AuthService.forgot_password(db, request)
    return success_response(
        data=result,
        message="Password reset email processed"
    )


@router.post("/reset-password", response_model=dict)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset password using token."""
    result = AuthService.reset_password(db, request)
    return success_response(
        data=result,
        message="Password reset successful"
    )


@router.post("/refresh", response_model=dict)
async def refresh_token(
    refresh_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """Refresh access token."""
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
    """Logout and blacklist tokens."""
    access_token = credentials.credentials if credentials else None
    refresh_token = refresh_data.refresh_token if refresh_data else None

    result = AuthService.logout_user(
        db=db,
        access_token=access_token,
        refresh_token=refresh_token
    )

    return success_response(data=result, message="Logout successful")
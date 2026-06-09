from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db
from app.core.config import settings
from app.core.security import Security
from app.services.oauth_service import GoogleOAuthService
from app.services.linkedin_oauth_service import LinkedInOAuthService
from app.services.auth_service import AuthService
from app.schemas.auth import GoogleAuthRequest, LinkedInAuthRequest
from app.utils.response import success_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ==================== GOOGLE OAuth Endpoints ====================

@router.get("/google/login")
async def google_login():
    """
    Redirect user to Google's OAuth consent screen.
    """
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        f"&client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        "&scope=email profile openid"
        "&access_type=offline"
        "&prompt=consent"
    )
    
    return RedirectResponse(url=google_auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    db: Session = Depends(get_db)
):
    """
    Google OAuth callback endpoint.
    """
    try:
        user, is_new_user = await GoogleOAuthService.authenticate_or_create_user(
            db=db,
            code=code,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )
        
        user_info = AuthService._build_user_info(user)
        
        access_token = Security.create_access_token(
            data={"sub": str(user.id)},
            user_info=user_info
        )
        refresh_token = Security.create_refresh_token(
            data={"sub": str(user.id)},
            user_info=user_info
        )
        
        response_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "is_verified": user.is_verified,
                "profile_picture": user.profile_picture
            },
            "is_new_user": is_new_user
        }
        
        message = "Account created and logged in successfully with Google" if is_new_user else "Logged in successfully with Google"
        
        return success_response(
            data=response_data,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Google OAuth callback error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}"
        )


@router.post("/google/token")
async def google_token_exchange(
    request: GoogleAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Exchange Google authorization code for JWT tokens.
    """
    try:
        redirect_uri = request.redirect_uri or settings.GOOGLE_REDIRECT_URI
        
        user, is_new_user = await GoogleOAuthService.authenticate_or_create_user(
            db=db,
            code=request.code,
            redirect_uri=redirect_uri
        )
        
        user_info = AuthService._build_user_info(user)
        
        access_token = Security.create_access_token(
            data={"sub": str(user.id)},
            user_info=user_info
        )
        refresh_token = Security.create_refresh_token(
            data={"sub": str(user.id)},
            user_info=user_info
        )
        
        response_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "is_new_user": is_new_user
        }
        
        return success_response(
            data=response_data,
            message="Google authentication successful"
        )
        
    except Exception as e:
        logger.error(f"Google token exchange error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}"
        )


# ==================== LINKEDIN OAuth Endpoints ====================

@router.get("/linkedin/login")
async def linkedin_login():
    """
    Redirect user to LinkedIn's OAuth consent screen.
    """
    linkedin_auth_url = LinkedInOAuthService.get_login_url()
    return RedirectResponse(url=linkedin_auth_url)


@router.get("/linkedin/callback")
async def linkedin_callback(
    code: str,
    db: Session = Depends(get_db)
):
    """
    LinkedIn OAuth callback endpoint.
    LinkedIn redirects here after user approves/denies the request.
    """
    try:
        # Authenticate or create user
        user, is_new_user, token_info = await LinkedInOAuthService.authenticate_or_create_user(
            db=db,
            code=code,
            redirect_uri=settings.LINKEDIN_REDIRECT_URI
        )
        
        # Generate JWT tokens for your application
        user_info = AuthService._build_user_info(user)
        
        access_token = Security.create_access_token(
            data={"sub": str(user.id)},
            user_info=user_info
        )
        refresh_token = Security.create_refresh_token(
            data={"sub": str(user.id)},
            user_info=user_info
        )
        
        response_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "is_verified": user.is_verified,
                "profile_picture": user.profile_picture
            },
            "is_new_user": is_new_user,
            "linkedin_token_expires_in": token_info.get("expires_in"),
            "linkedin_token_expires_at": token_info.get("expires_at").isoformat() if token_info.get("expires_at") else None
        }
        
        message = "Account created and logged in successfully with LinkedIn" if is_new_user else "Logged in successfully with LinkedIn"
        
        return success_response(
            data=response_data,
            message=message
        )
        
    except Exception as e:
        logger.error(f"LinkedIn OAuth callback error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LinkedIn authentication failed: {str(e)}"
        )


@router.post("/linkedin/token")
async def linkedin_token_exchange(
    request: LinkedInAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Exchange LinkedIn authorization code for JWT tokens.
    This endpoint is useful for mobile apps or single-page applications
    that handle the OAuth redirect themselves.
    """
    try:
        redirect_uri = request.redirect_uri or settings.LINKEDIN_REDIRECT_URI
        
        user, is_new_user, token_info = await LinkedInOAuthService.authenticate_or_create_user(
            db=db,
            code=request.code,
            redirect_uri=redirect_uri
        )
        
        user_info = AuthService._build_user_info(user)
        
        access_token = Security.create_access_token(
            data={"sub": str(user.id)},
            user_info=user_info
        )
        refresh_token = Security.create_refresh_token(
            data={"sub": str(user.id)},
            user_info=user_info
        )
        
        response_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "is_new_user": is_new_user,
            "linkedin_token_expires_in": token_info.get("expires_in")
        }
        
        return success_response(
            data=response_data,
            message="LinkedIn authentication successful"
        )
        
    except Exception as e:
        logger.error(f"LinkedIn token exchange error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LinkedIn authentication failed: {str(e)}"
        )
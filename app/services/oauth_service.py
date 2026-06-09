from sqlalchemy.orm import Session
from typing import Dict, Any, Tuple
import httpx
import secrets
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.user import User
from app.core.enums import UserRole
from app.utils.auth_utils import hash_password
from app.utils.datetime_utils import get_current_utc
from app.core.security import Security
import logging

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    """Service for handling Google OAuth authentication"""
    
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    @classmethod
    async def get_google_user_info(cls, code: str, redirect_uri: str = None) -> Dict[str, Any]:
        """
        Exchange authorization code for user info from Google
        """
        if not redirect_uri:
            redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        # Exchange code for access token
        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        
        async with httpx.AsyncClient() as client:
            # Get access token
            token_response = await client.post(
                cls.GOOGLE_TOKEN_URL,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                logger.error(f"Google token exchange failed: {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to authenticate with Google"
                )
            
            token_json = token_response.json()
            access_token = token_json.get("access_token")
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from Google"
                )
            
            # Get user info
            userinfo_response = await client.get(
                cls.GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if userinfo_response.status_code != 200:
                logger.error(f"Google userinfo failed: {userinfo_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user info from Google"
                )
            
            return userinfo_response.json()
    
    @classmethod
    def generate_username_from_email(cls, email: str) -> str:
        """
        Generate a unique username from email address
        Example: john.doe@gmail.com -> john_doe
        """
        # Extract part before @
        base_username = email.split('@')[0]
        # Replace dots and special characters with underscore
        base_username = re.sub(r'[^a-zA-Z0-9]', '_', base_username)
        # Limit length
        base_username = base_username[:45]
        return base_username
    
    @classmethod
    async def authenticate_or_create_user(
        cls, 
        db: Session, 
        code: str, 
        redirect_uri: str = None
    ) -> Tuple[User, bool]:
        """
        Authenticate user with Google. If user doesn't exist, create new account.
        Returns: (user, is_new_user)
        """
        # Get user info from Google
        google_user = await cls.get_google_user_info(code, redirect_uri)
        
        google_id = google_user.get("id")
        email = google_user.get("email")
        verified_email = google_user.get("verified_email", False)
        first_name = google_user.get("given_name", "")
        last_name = google_user.get("family_name", "")
        picture = google_user.get("picture")
        
        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient user info from Google"
            )
        
        # Check if user exists by OAuth ID
        user = db.query(User).filter(
            User.oauth_provider == "google",
            User.oauth_id == google_id
        ).first()
        
        is_new_user = False
        
        if user:
            # User exists via OAuth
            logger.info(f"User found via Google OAuth: {user.username}")
            
            # Update profile picture if changed
            if picture and picture != user.profile_picture:
                user.profile_picture = picture
            
            db.commit()
            db.refresh(user)
            
        else:
            # Check if user exists by email (might have registered normally)
            user = db.query(User).filter(User.email == email).first()
            
            if user:
                # User exists via email/password, link Google account
                logger.info(f"Linking Google account to existing user: {user.username}")
                user.oauth_provider = "google"
                user.oauth_id = google_id
                if picture:
                    user.profile_picture = picture
                # Google email is already verified
                user.is_verified = True
                db.commit()
                db.refresh(user)
            else:
                # Create new user
                is_new_user = True
                base_username = cls.generate_username_from_email(email)
                
                # Ensure username is unique
                username = base_username
                counter = 1
                while db.query(User).filter(User.username == username).first():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                # Generate random password (user will use Google to login)
                random_password = secrets.token_urlsafe(32)
                hashed_password = hash_password(random_password)
                
                user = User(
                    username=username,
                    email=email,
                    password_hash=hashed_password,
                    first_name=first_name or email.split('@')[0],
                    last_name=last_name or "",
                    role=UserRole.USER,
                    is_active=True,
                    is_verified=True,  # Google emails are verified
                    oauth_provider="google",
                    oauth_id=google_id,
                    profile_picture=picture
                )
                
                db.add(user)
                db.commit()
                db.refresh(user)
                
                logger.info(f"New user created via Google OAuth: {user.username}")
        
        return user, is_new_user


# Import re module for username generation
import re
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
import re

logger = logging.getLogger(__name__)


class LinkedInOAuthService:
    """Service for handling LinkedIn OAuth authentication using OpenID Connect"""
    
    # LinkedIn OAuth endpoints
    LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    # OpenID Connect userinfo endpoint (NEW - required for OIDC)
    LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
    
    @classmethod
    def get_login_url(cls) -> str:
        """
        Generate LinkedIn OAuth login URL using OpenID Connect scopes
        """
        return (
            f"{cls.LINKEDIN_AUTH_URL}"
            f"?response_type=code"
            f"&client_id={settings.LINKEDIN_CLIENT_ID}"
            f"&redirect_uri={settings.LINKEDIN_REDIRECT_URI}"
            f"&scope=openid profile email"  # OIDC scopes
        )
    
    @classmethod
    async def get_linkedin_user_info(cls, code: str, redirect_uri: str = None) -> Dict[str, Any]:
        """
        Exchange authorization code for user info from LinkedIn using OpenID Connect
        """
        if not redirect_uri:
            redirect_uri = settings.LINKEDIN_REDIRECT_URI
        
        async with httpx.AsyncClient() as client:
            # Step 1: Exchange code for access token
            token_response = await client.post(
                cls.LINKEDIN_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": settings.LINKEDIN_CLIENT_ID,
                    "client_secret": settings.LINKEDIN_CLIENT_SECRET
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                logger.error(f"LinkedIn token exchange failed: {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to authenticate with LinkedIn"
                )
            
            token_json = token_response.json()
            access_token = token_json.get("access_token")
            expires_in = token_json.get("expires_in", 5184000)  # ~60 days default
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from LinkedIn"
                )
            
            # Step 2: Get user info using OpenID Connect userinfo endpoint
            userinfo_response = await client.get(
                cls.LINKEDIN_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if userinfo_response.status_code != 200:
                logger.error(f"LinkedIn userinfo failed: {userinfo_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user info from LinkedIn"
                )
            
            user_data = userinfo_response.json()
            
            # Add token expiry info
            user_data["access_token"] = access_token
            user_data["expires_at"] = get_current_utc() + timedelta(seconds=expires_in)
            user_data["expires_in"] = expires_in
            
            logger.info(f"LinkedIn user info retrieved for user: {user_data.get('sub')}")
            
            return user_data
    
    @classmethod
    def generate_username_from_email(cls, email: str) -> str:
        """
        Generate a unique username from email address
        Example: john.doe@example.com -> john_doe
        """
        # Extract part before @
        base_username = email.split('@')[0]
        # Replace dots and special characters with underscore
        base_username = re.sub(r'[^a-zA-Z0-9]', '_', base_username)
        # Remove consecutive underscores
        base_username = re.sub(r'_+', '_', base_username)
        # Remove leading/trailing underscores
        base_username = base_username.strip('_')
        # Limit length
        base_username = base_username[:45]
        return base_username
    
    @classmethod
    async def authenticate_or_create_user(
        cls, 
        db: Session, 
        code: str, 
        redirect_uri: str = None
    ) -> Tuple[User, bool, Dict[str, Any]]:
        """
        Authenticate user with LinkedIn. If user doesn't exist, create new account.
        Returns: (user, is_new_user, token_info)
        """
        # Get user info from LinkedIn via OpenID Connect
        linkedin_data = await cls.get_linkedin_user_info(code, redirect_uri)
        
        # Extract user information from OpenID Connect response
        # 'sub' is the standard OpenID Connect user identifier
        linkedin_id = linkedin_data.get("sub")
        email = linkedin_data.get("email")
        email_verified = linkedin_data.get("email_verified", True)
        first_name = linkedin_data.get("given_name", "")
        last_name = linkedin_data.get("family_name", "")
        picture = linkedin_data.get("picture", None)
        preferred_username = linkedin_data.get("preferred_username", "")
        
        if not linkedin_id:
            logger.error("LinkedIn OAuth: No user ID (sub) received")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient user info from LinkedIn"
            )
        
        if not email:
            logger.warning(f"LinkedIn OAuth: No email received for user {linkedin_id}")
            # For LinkedIn, email might be missing if not properly configured
            # We'll still proceed but with a warning
        
        # Check if user exists by OAuth ID
        user = db.query(User).filter(
            User.oauth_provider == "linkedin",
            User.oauth_id == linkedin_id
        ).first()
        
        is_new_user = False
        token_info = {
            "access_token": linkedin_data.get("access_token"),
            "expires_at": linkedin_data.get("expires_at"),
            "expires_in": linkedin_data.get("expires_in")
        }
        
        if user:
            # User exists via LinkedIn OAuth
            logger.info(f"User found via LinkedIn OAuth: {user.username}")
            
            # Update profile picture if changed
            if picture and picture != user.profile_picture:
                user.profile_picture = picture
            
            # Update name if changed on LinkedIn
            if first_name and first_name != user.first_name:
                user.first_name = first_name
            if last_name and last_name != user.last_name:
                user.last_name = last_name
            
            # Update email if LinkedIn provides it and it's different
            if email and email != user.email:
                # Check if new email is already taken by another user
                existing_user = db.query(User).filter(
                    User.email == email,
                    User.id != user.id
                ).first()
                if not existing_user:
                    user.email = email
            
            db.commit()
            db.refresh(user)
            
        else:
            # Check if user exists by email (might have registered normally or with Google)
            if email:
                user = db.query(User).filter(User.email == email).first()
            
            if user:
                # User exists via email/password or other OAuth, link LinkedIn account
                logger.info(f"Linking LinkedIn account to existing user: {user.username}")
                user.oauth_provider = "linkedin"
                user.oauth_id = linkedin_id
                if picture:
                    user.profile_picture = picture
                # Update name if user doesn't have it
                if not user.first_name and first_name:
                    user.first_name = first_name
                if not user.last_name and last_name:
                    user.last_name = last_name
                # LinkedIn email is considered verified
                user.is_verified = True
                db.commit()
                db.refresh(user)
            else:
                # Create new user
                is_new_user = True
                
                # Generate username
                if preferred_username:
                    base_username = preferred_username[:45]
                elif email:
                    base_username = cls.generate_username_from_email(email)
                else:
                    base_username = f"linkedin_user_{linkedin_id[:10]}"
                
                # Ensure username is unique
                username = base_username
                counter = 1
                while db.query(User).filter(User.username == username).first():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                # Generate random password (user will use LinkedIn to login)
                random_password = secrets.token_urlsafe(32)
                hashed_password = hash_password(random_password)
                
                # Create email if not provided by LinkedIn
                user_email = email if email else f"{username}@linkedin.user"
                
                user = User(
                    username=username,
                    email=user_email,
                    password_hash=hashed_password,
                    first_name=first_name or username,
                    last_name=last_name or "",
                    role=UserRole.USER,
                    is_active=True,
                    is_verified=True,  # OAuth users are considered verified
                    oauth_provider="linkedin",
                    oauth_id=linkedin_id,
                    profile_picture=picture
                )
                
                db.add(user)
                db.commit()
                db.refresh(user)
                
                logger.info(f"New user created via LinkedIn OAuth: {user.username}")
        
        return user, is_new_user, token_info
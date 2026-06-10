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


class FacebookOAuthService:
    """Service for handling Facebook OAuth authentication"""
    
    # Facebook OAuth endpoints
    FACEBOOK_AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
    FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
    FACEBOOK_USERINFO_URL = "https://graph.facebook.com/v18.0/me"
    
    @classmethod
    def get_login_url(cls) -> str:
        """
        Generate Facebook OAuth login URL
        """
        return (
            f"{cls.FACEBOOK_AUTH_URL}"
            f"?response_type=code"
            f"&client_id={settings.FACEBOOK_CLIENT_ID}"
            f"&redirect_uri={settings.FACEBOOK_REDIRECT_URI}"
            f"&scope=public_profile,email"
        )
    
    @classmethod
    async def get_facebook_user_info(cls, code: str, redirect_uri: str = None) -> Dict[str, Any]:
        """
        Exchange authorization code for user info from Facebook
        """
        if not redirect_uri:
            redirect_uri = settings.FACEBOOK_REDIRECT_URI
        
        async with httpx.AsyncClient() as client:
            # Step 1: Exchange code for access token
            token_response = await client.get(
                cls.FACEBOOK_TOKEN_URL,
                params={
                    "client_id": settings.FACEBOOK_CLIENT_ID,
                    "client_secret": settings.FACEBOOK_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri
                }
            )
            
            if token_response.status_code != 200:
                logger.error(f"Facebook token exchange failed: {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to authenticate with Facebook"
                )
            
            token_json = token_response.json()
            access_token = token_json.get("access_token")
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from Facebook"
                )
            
            # Step 2: Get user info with the access token
            userinfo_response = await client.get(
                cls.FACEBOOK_USERINFO_URL,
                params={
                    "fields": "id,name,first_name,last_name,email,picture.width(200).height(200)",
                    "access_token": access_token
                }
            )
            
            if userinfo_response.status_code != 200:
                logger.error(f"Facebook userinfo failed: {userinfo_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user info from Facebook"
                )
            
            user_data = userinfo_response.json()
            
            # Add token info
            user_data["access_token"] = access_token
            user_data["expires_at"] = get_current_utc() + timedelta(seconds=token_json.get("expires_in", 5184000))
            user_data["expires_in"] = token_json.get("expires_in", 5184000)
            
            # Extract picture URL if available
            if user_data.get("picture") and user_data["picture"].get("data"):
                user_data["picture_url"] = user_data["picture"]["data"].get("url")
            
            logger.info(f"Facebook user info retrieved for user: {user_data.get('id')}")
            
            return user_data
    
    @classmethod
    def generate_username_from_email(cls, email: str) -> str:
        """
        Generate a unique username from email address
        Example: john.doe@example.com -> john_doe
        """
        if not email:
            return None
        
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
        Authenticate user with Facebook. If user doesn't exist, create new account.
        Returns: (user, is_new_user, token_info)
        """
        # Get user info from Facebook
        facebook_data = await cls.get_facebook_user_info(code, redirect_uri)
        
        # Extract user information
        facebook_id = facebook_data.get("id")
        email = facebook_data.get("email")
        first_name = facebook_data.get("first_name", "")
        last_name = facebook_data.get("last_name", "")
        name = facebook_data.get("name", "")
        picture_url = facebook_data.get("picture_url")
        
        if not facebook_id:
            logger.error("Facebook OAuth: No user ID received")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient user info from Facebook"
            )
        
        # Check if user exists by OAuth ID
        user = db.query(User).filter(
            User.oauth_provider == "facebook",
            User.oauth_id == facebook_id
        ).first()
        
        is_new_user = False
        token_info = {
            "access_token": facebook_data.get("access_token"),
            "expires_at": facebook_data.get("expires_at"),
            "expires_in": facebook_data.get("expires_in")
        }
        
        if user:
            # User exists via Facebook OAuth
            logger.info(f"User found via Facebook OAuth: {user.username}")
            
            # Update profile picture if changed
            if picture_url and picture_url != user.profile_picture:
                user.profile_picture = picture_url
            
            # Update name if changed on Facebook
            if first_name and first_name != user.first_name:
                user.first_name = first_name
            if last_name and last_name != user.last_name:
                user.last_name = last_name
            
            # Update email if Facebook provides it and it's different
            if email and email != user.email:
                existing_user = db.query(User).filter(
                    User.email == email,
                    User.id != user.id
                ).first()
                if not existing_user:
                    user.email = email
            
            db.commit()
            db.refresh(user)
            
        else:
            # Check if user exists by email (might have registered normally or with other OAuth)
            if email:
                user = db.query(User).filter(User.email == email).first()
            
            if user:
                # User exists via email/password or other OAuth, link Facebook account
                logger.info(f"Linking Facebook account to existing user: {user.username}")
                user.oauth_provider = "facebook"
                user.oauth_id = facebook_id
                if picture_url:
                    user.profile_picture = picture_url
                # Update name if user doesn't have it
                if not user.first_name and first_name:
                    user.first_name = first_name
                if not user.last_name and last_name:
                    user.last_name = last_name
                if not user.first_name and not user.last_name and name:
                    # If no first/last name, try to split the full name
                    name_parts = name.split(' ', 1)
                    user.first_name = name_parts[0]
                    user.last_name = name_parts[1] if len(name_parts) > 1 else ""
                # Facebook email is considered verified
                user.is_verified = True
                db.commit()
                db.refresh(user)
            else:
                # Create new user
                is_new_user = True
                
                # Generate username
                if email:
                    base_username = cls.generate_username_from_email(email)
                else:
                    base_username = f"fb_user_{facebook_id[:10]}"
                
                if not base_username:
                    base_username = f"fb_user_{facebook_id[:10]}"
                
                # Ensure username is unique
                username = base_username
                counter = 1
                while db.query(User).filter(User.username == username).first():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                # Generate random password (user will use Facebook to login)
                random_password = secrets.token_urlsafe(32)
                hashed_password = hash_password(random_password)
                
                # Use name or first_name/last_name
                if first_name and last_name:
                    user_first_name = first_name
                    user_last_name = last_name
                elif name:
                    name_parts = name.split(' ', 1)
                    user_first_name = name_parts[0]
                    user_last_name = name_parts[1] if len(name_parts) > 1 else ""
                else:
                    user_first_name = username
                    user_last_name = ""
                
                # Create email if not provided by Facebook
                user_email = email if email else f"{username}@facebook.user"
                
                user = User(
                    username=username,
                    email=user_email,
                    password_hash=hashed_password,
                    first_name=user_first_name,
                    last_name=user_last_name,
                    role=UserRole.USER,
                    is_active=True,
                    is_verified=True,  # OAuth users are considered verified
                    oauth_provider="facebook",
                    oauth_id=facebook_id,
                    profile_picture=picture_url
                )
                
                db.add(user)
                db.commit()
                db.refresh(user)
                
                logger.info(f"New user created via Facebook OAuth: {user.username}")
        
        return user, is_new_user, token_info
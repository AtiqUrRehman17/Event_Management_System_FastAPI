from sqlalchemy.orm import Session
from datetime import datetime
from typing import Tuple, Optional
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.utils.auth_utils import hash_password, verify_password
from app.core import Security, InvalidCredentialsException, EmailAlreadyExistsException
from app.core.enums import UserRole


class AuthService:
    
    @staticmethod
    def register_user(db: Session, user_data: RegisterRequest) -> User:
        """
        Register a new user - returns only user, no tokens
        """
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise EmailAlreadyExistsException()
        
        # Create new user
        hashed_password = hash_password(user_data.password)
        new_user = User(
            email=user_data.email,
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=UserRole.USER,
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user
    
    @staticmethod
    def login_user(db: Session, login_data: LoginRequest) -> Tuple[User, str, str]:
        """
        Authenticate user and return tokens
        Returns: (user, access_token, refresh_token)
        """
        # Find user by email
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user:
            raise InvalidCredentialsException()
        
        # Verify password
        if not verify_password(login_data.password, user.password_hash):
            raise InvalidCredentialsException()
        
        # Check if user is active
        if not user.is_active:
            raise InvalidCredentialsException()
        
        # Generate tokens
        access_token = Security.create_access_token(data={"sub": str(user.id)})
        refresh_token = Security.create_refresh_token(data={"sub": str(user.id)})
        
        return user, access_token, refresh_token
    
    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Tuple[str, str]:
        """
        Generate new access token using refresh token
        Returns: (new_access_token, new_refresh_token)
        """
        # Verify refresh token
        payload = Security.verify_token(refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            raise InvalidCredentialsException()
        
        # Check if user exists and is active
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise InvalidCredentialsException()
        
        # Generate new tokens
        new_access_token = Security.create_access_token(data={"sub": str(user.id)})
        new_refresh_token = Security.create_refresh_token(data={"sub": str(user.id)})
        
        return new_access_token, new_refresh_token
    
    @staticmethod
    def logout_user() -> dict:
        """
        Logout user (client-side token removal)
        """
        return {"message": "Successfully logged out"}
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .db import get_db
from app.core import Security, settings, get_current_token
from app.core.exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
    TokenExpiredException,
    PermissionDeniedException,
    UserNotFoundException,
)
from app.models.user import User
from app.core.enums import UserRole

# Create HTTPBearer instance for Swagger UI
oauth2_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="Enter your JWT token"
)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user
    """
    if not credentials:
        raise InvalidCredentialsException()
    
    # Extract and verify token
    token = credentials.credentials
    
    try:
        payload = Security.verify_token(token, token_type="access")
        user_id: int = payload.get("sub")
        if user_id is None:
            raise InvalidTokenException()
    except Exception:
        raise InvalidTokenException()
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise UserNotFoundException()
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get current user and verify admin role
    """
    if current_user.role != UserRole.ADMIN:
        raise PermissionDeniedException()
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to get current user if authenticated, otherwise return None
    Useful for endpoints that work for both authenticated and unauthenticated users
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = Security.verify_token(token, token_type="access")
        user_id: int = payload.get("sub")
        
        if user_id is None:
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        return user if user and user.is_active else None
    except (InvalidTokenException, TokenExpiredException, UserNotFoundException):
        return None
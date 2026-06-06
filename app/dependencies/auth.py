from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .db import get_db
from app.core.security import Security
from app.core.exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
    TokenExpiredException,
    PermissionDeniedException,
    UserNotFoundException,
)
from app.models.user import User
from app.models.token_blacklist import TokenBlacklist
from app.core.enums import UserRole

# Protected endpoints - auto_error=True → rejects if no token
oauth2_scheme = HTTPBearer(
    auto_error=True,
    scheme_name="BearerAuth",
    description="Enter your JWT token"
)

# Optional endpoints - auto_error=False → allows no token
oauth2_scheme_optional = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="Enter your JWT token (optional)"
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user.
    REQUIRED authentication - will reject if no token provided.
    Also checks if token has been blacklisted (logged out).
    """
    # credentials is guaranteed to exist because auto_error=True
    token = credentials.credentials

    # Check if token is blacklisted (user logged out)
    blacklisted = db.query(TokenBlacklist).filter(
        TokenBlacklist.token == token
    ).first()
    if blacklisted:
        raise InvalidTokenException()

    try:
        payload = Security.verify_token(token, token_type="access")
        user_id = payload.get("sub")
        if user_id is None:
            raise InvalidTokenException()
    except (InvalidTokenException, TokenExpiredException):
        raise
    except Exception:
        raise InvalidTokenException()

    # Get user from database
    user = db.query(User).filter(User.id == int(user_id)).first()
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
    Dependency to verify admin role.
    Requires authentication first (via get_current_user).
    """
    if current_user.role != UserRole.ADMIN:
        raise PermissionDeniedException()
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication.
    Returns User if valid token provided.
    Returns None if no token or invalid token.
    Used for public endpoints that work for both logged-in and anonymous users.
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials

        # Check blacklist
        blacklisted = db.query(TokenBlacklist).filter(
            TokenBlacklist.token == token
        ).first()
        if blacklisted:
            return None

        payload = Security.verify_token(token, token_type="access")
        user_id = payload.get("sub")

        if user_id is None:
            return None

        user = db.query(User).filter(User.id == int(user_id)).first()
        return user if user and user.is_active else None

    except (InvalidTokenException, TokenExpiredException, UserNotFoundException):
        return None
    except Exception:
        return None
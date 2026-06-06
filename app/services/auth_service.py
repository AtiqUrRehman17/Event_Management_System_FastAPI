from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from app.models.user import User
from app.models.token_blacklist import TokenBlacklist
from app.schemas.auth import LoginRequest, RegisterRequest
from app.utils.auth_utils import hash_password, verify_password
from app.core import Security, settings
from app.core.exceptions import (
    InvalidCredentialsException,
    EmailAlreadyExistsException,
    InvalidTokenException
)
from app.core.enums import UserRole
import logging

logger = logging.getLogger(__name__)


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
        # Check if refresh token is blacklisted
        if AuthService.is_token_blacklisted(db, refresh_token):
            raise InvalidTokenException()

        # Verify refresh token
        payload = Security.verify_token(refresh_token, token_type="refresh")
        user_id = payload.get("sub")

        if not user_id:
            raise InvalidCredentialsException()

        # Check if user exists and is active
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise InvalidCredentialsException()

        # Blacklist old refresh token so it cannot be reused
        AuthService._blacklist_token(
            db=db,
            token=refresh_token,
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        )

        # Generate new tokens
        new_access_token = Security.create_access_token(data={"sub": str(user.id)})
        new_refresh_token = Security.create_refresh_token(data={"sub": str(user.id)})

        return new_access_token, new_refresh_token

    @staticmethod
    def logout_user(db: Session, access_token: str, refresh_token: Optional[str] = None) -> dict:
        """
        Logout user by blacklisting both access and refresh tokens
        """
        # Blacklist access token
        try:
            payload = Security.verify_token(access_token, token_type="access")
            expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            AuthService._blacklist_token(db, access_token, expires_at)
        except Exception as e:
            logger.warning(f"Could not blacklist access token during logout: {str(e)}")

        # Blacklist refresh token if provided
        if refresh_token:
            try:
                payload = Security.verify_token(refresh_token, token_type="refresh")
                expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
                AuthService._blacklist_token(db, refresh_token, expires_at)
            except Exception as e:
                logger.warning(f"Could not blacklist refresh token during logout: {str(e)}")

        return {"message": "Successfully logged out"}

    @staticmethod
    def is_token_blacklisted(db: Session, token: str) -> bool:
        """
        Check if a token is in the blacklist
        """
        blacklisted = db.query(TokenBlacklist).filter(
            TokenBlacklist.token == token
        ).first()
        return blacklisted is not None

    @staticmethod
    def _blacklist_token(db: Session, token: str, expires_at: datetime) -> None:
        """
        Add a token to the blacklist
        """
        # Check if already blacklisted to avoid duplicate entry
        existing = db.query(TokenBlacklist).filter(
            TokenBlacklist.token == token
        ).first()

        if not existing:
            blacklisted_token = TokenBlacklist(
                token=token,
                expires_at=expires_at
            )
            db.add(blacklisted_token)
            db.commit()

    @staticmethod
    def cleanup_expired_tokens(db: Session) -> int:
        """
        Remove expired tokens from blacklist to keep table clean.
        Called by scheduler.
        """
        now = datetime.now(timezone.utc)
        try:
            expired = db.query(TokenBlacklist).filter(
                TokenBlacklist.expires_at < now
            ).all()

            count = len(expired)
            if count > 0:
                for token in expired:
                    db.delete(token)
                db.commit()
                logger.info(f"Cleaned up {count} expired blacklisted token(s)")

            return count

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to cleanup expired tokens: {str(e)}")
            raise
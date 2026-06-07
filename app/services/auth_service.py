from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Tuple, Optional
from app.models.user import User
from app.models.token_blacklist import TokenBlacklist
from app.schemas.auth import LoginRequest, RegisterRequest
from app.utils.auth_utils import hash_password, verify_password
from app.core import Security, settings
from app.core.exceptions import (
    InvalidCredentialsException,
    EmailAlreadyExistsException,
    UsernameAlreadyExistsException,
    InvalidTokenException
)
from app.core.enums import UserRole
import logging

logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    def register_user(db: Session, user_data: RegisterRequest) -> User:
        """Register a new user with unique username and email"""
        # Check if username already taken
        existing_username = db.query(User).filter(
            User.username == user_data.username.lower()
        ).first()
        if existing_username:
            raise UsernameAlreadyExistsException()

        # Check if email already taken
        existing_email = db.query(User).filter(
            User.email == user_data.email
        ).first()
        if existing_email:
            raise EmailAlreadyExistsException()

        hashed_password = hash_password(user_data.password)
        new_user = User(
            username=user_data.username.lower(),
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
        Authenticate user using username and password.
        """
        # Find user by username
        user = db.query(User).filter(
            User.username == login_data.username.lower()
        ).first()
        if not user:
            raise InvalidCredentialsException()

        if not verify_password(login_data.password, user.password_hash):
            raise InvalidCredentialsException()

        if not user.is_active:
            raise InvalidCredentialsException()

        access_token = Security.create_access_token(data={"sub": str(user.id)})
        refresh_token = Security.create_refresh_token(data={"sub": str(user.id)})

        return user, access_token, refresh_token

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Tuple[str, str]:
        """Generate new tokens using refresh token"""
        if AuthService.is_token_blacklisted(db, refresh_token):
            raise InvalidTokenException()

        payload = Security.verify_token(refresh_token, token_type="refresh")
        user_id = payload.get("sub")

        if not user_id:
            raise InvalidCredentialsException()

        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise InvalidCredentialsException()

        AuthService._blacklist_token(
            db=db,
            token=refresh_token,
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        )

        new_access_token = Security.create_access_token(data={"sub": str(user.id)})
        new_refresh_token = Security.create_refresh_token(data={"sub": str(user.id)})

        return new_access_token, new_refresh_token

    @staticmethod
    def logout_user(db: Session, access_token: str, refresh_token: Optional[str] = None) -> dict:
        """Logout user by blacklisting tokens"""
        try:
            payload = Security.verify_token(access_token, token_type="access")
            expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            AuthService._blacklist_token(db, access_token, expires_at)
        except Exception as e:
            logger.warning(f"Could not blacklist access token: {str(e)}")

        if refresh_token:
            try:
                payload = Security.verify_token(refresh_token, token_type="refresh")
                expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
                AuthService._blacklist_token(db, refresh_token, expires_at)
            except Exception as e:
                logger.warning(f"Could not blacklist refresh token: {str(e)}")

        return {"message": "Successfully logged out"}

    @staticmethod
    def is_token_blacklisted(db: Session, token: str) -> bool:
        """Check if token is blacklisted"""
        blacklisted = db.query(TokenBlacklist).filter(
            TokenBlacklist.token == token
        ).first()
        return blacklisted is not None

    @staticmethod
    def _blacklist_token(db: Session, token: str, expires_at: datetime) -> None:
        """Add token to blacklist"""
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
        """Remove expired tokens from blacklist"""
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
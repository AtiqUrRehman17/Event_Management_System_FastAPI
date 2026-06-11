from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
import secrets
from fastapi import HTTPException, status
from app.models.user import User
from app.models.token_blacklist import TokenBlacklist
from app.models.password_reset_token import PasswordResetToken
from app.models.email_verification_token import EmailVerificationToken
from app.schemas.auth import LoginRequest, RegisterRequest, ForgotPasswordRequest, ResetPasswordRequest
from app.utils.auth_utils import hash_password, verify_password
from app.utils.datetime_utils import get_current_utc
from app.core import Security, settings
from app.core.exceptions import (
    InvalidCredentialsException,
    EmailAlreadyExistsException,
    UsernameAlreadyExistsException,
    InvalidTokenException,
    UserNotFoundException
)
from app.core.enums import UserRole
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    def _build_user_info(user: User) -> dict:
        """Build user info dict to include in JWT token"""
        return {
            "username": user.username,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
        }

    @staticmethod
    def register_user(db: Session, user_data: RegisterRequest) -> User:
        """
        Register a new user and send verification email
        Returns: User object (token is NOT returned for security)
        """
        # Check existing username
        existing_username = db.query(User).filter(
            User.username == user_data.username.lower()
        ).first()
        if existing_username:
            raise UsernameAlreadyExistsException()

        # Check existing email
        existing_email = db.query(User).filter(
            User.email == user_data.email
        ).first()
        if existing_email:
            raise EmailAlreadyExistsException()

        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Create user (is_verified = False by default)
        new_user = User(
            username=user_data.username.lower(),
            email=user_data.email,
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=UserRole.USER,
            is_active=True,
            is_verified=False
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"User created successfully: {new_user.username} ({new_user.email})")

        # Generate verification token
        verification_token = secrets.token_urlsafe(32)
        expires_at = get_current_utc() + timedelta(minutes=settings.VERIFICATION_TOKEN_EXPIRE_MINUTES)

        # Create verification token record
        verification_record = EmailVerificationToken(
            token=verification_token,
            user_id=new_user.id,
            expires_at=expires_at,
            is_used=False
        )
        
        db.add(verification_record)
        db.commit()

        logger.info(f"Verification token created for user {new_user.username}")

        # Send verification email
        try:
            email_sent = EmailService.send_verification_email(
                to_email=new_user.email,
                username=new_user.username,
                verification_token=verification_token
            )
            
            if email_sent:
                logger.info(f"Verification email sent successfully to {new_user.email}")
            else:
                logger.error(f"Failed to send verification email to {new_user.email}")
        except Exception as e:
            logger.error(f"Error sending verification email: {str(e)}")

        return new_user

    @staticmethod
    def verify_email(db: Session, token: str) -> dict:
        """
        Verify user's email address using verification token
        """
        verification_record = db.query(EmailVerificationToken).filter(
            EmailVerificationToken.token == token,
            EmailVerificationToken.is_used == False
        ).first()

        if not verification_record:
            raise InvalidTokenException()

        if verification_record.is_expired:
            db.delete(verification_record)
            db.commit()
            raise InvalidTokenException()

        user = db.query(User).filter(User.id == verification_record.user_id).first()
        if not user:
            raise UserNotFoundException()

        if user.is_verified:
            return {"message": "Email already verified", "is_verified": True}

        user.is_verified = True
        user.updated_at = get_current_utc()
        verification_record.is_used = True

        db.commit()

        logger.info(f"Email verified successfully for user {user.username}")

        try:
            EmailService.send_verification_confirmation(
                to_email=user.email,
                username=user.username
            )
        except Exception as e:
            logger.error(f"Failed to send verification confirmation email: {str(e)}")

        return {"message": "Email verified successfully", "is_verified": True}

    @staticmethod
    def resend_verification_email(db: Session, email: str) -> dict:
        """Resend verification email to user"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {"message": "If your email is registered, you will receive a verification email"}

        if user.is_verified:
            return {"message": "Email already verified", "is_verified": True}

        existing_token = db.query(EmailVerificationToken).filter(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.is_used == False
        ).first()
        
        if existing_token:
            db.delete(existing_token)
            db.commit()
            logger.info(f"Deleted existing verification token for user {user.username}")

        verification_token = secrets.token_urlsafe(32)
        expires_at = get_current_utc() + timedelta(minutes=settings.VERIFICATION_TOKEN_EXPIRE_MINUTES)

        verification_record = EmailVerificationToken(
            token=verification_token,
            user_id=user.id,
            expires_at=expires_at,
            is_used=False
        )
        
        db.add(verification_record)
        db.commit()

        logger.info(f"New verification token created for user {user.username}")

        try:
            email_sent = EmailService.send_verification_email(
                to_email=user.email,
                username=user.username,
                verification_token=verification_token
            )

            if email_sent:
                logger.info(f"Verification email resent successfully to {user.email}")
                return {"message": "Verification email sent successfully"}
            else:
                logger.error(f"Failed to resend verification email to {user.email}")
                return {"message": "Unable to send verification email. Please try again later."}
        except Exception as e:
            logger.error(f"Error resending verification email: {str(e)}")
            return {"message": "Unable to send verification email. Please try again later."}

    @staticmethod
    def login_user(db: Session, login_data: LoginRequest) -> Tuple[User, str, str]:
        """Authenticate user using username and password"""
        user = db.query(User).filter(
            User.username == login_data.username.lower()
        ).first()
        if not user:
            raise InvalidCredentialsException()

        if not verify_password(login_data.password, user.password_hash):
            raise InvalidCredentialsException()

        if not user.is_active:
            raise InvalidCredentialsException()

        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please verify your email before logging in."
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

        return user, access_token, refresh_token

    @staticmethod
    def forgot_password(db: Session, request: ForgotPasswordRequest) -> dict:
        """Send password reset email to user with reset token"""
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            return {"message": "If your email is registered, you will receive a password reset email"}

        reset_token = secrets.token_urlsafe(32)
        expires_at = get_current_utc() + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)

        reset_token_record = PasswordResetToken(
            token=reset_token,
            user_id=user.id,
            expires_at=expires_at,
            is_used=False
        )
        
        db.add(reset_token_record)
        db.commit()

        email_sent = EmailService.send_password_reset_email(
            to_email=user.email,
            username=user.username,
            reset_token=reset_token
        )

        if not email_sent:
            logger.error(f"Failed to send password reset email to {user.email}")

        return {"message": "If your email is registered, you will receive a password reset email"}

    @staticmethod
    def reset_password(db: Session, request: ResetPasswordRequest) -> dict:
        """Reset password using valid token"""
        reset_record = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == request.token,
            PasswordResetToken.is_used == False
        ).first()

        if not reset_record:
            raise InvalidTokenException()

        if reset_record.is_expired:
            db.delete(reset_record)
            db.commit()
            raise InvalidTokenException()

        user = db.query(User).filter(User.id == reset_record.user_id).first()
        if not user:
            raise UserNotFoundException()

        user.password_hash = hash_password(request.new_password)
        user.updated_at = get_current_utc()
        reset_record.is_used = True

        db.commit()

        EmailService.send_password_reset_confirmation(
            to_email=user.email,
            username=user.username
        )
        
        # Send password changed notification
        try:
            NotificationService.send_password_changed_notification(db, user.id)
        except Exception as e:
            logger.error(f"Failed to send password changed notification: {str(e)}")

        logger.info(f"Password reset successful for user {user.username}")
        return {"message": "Password reset successful. You can now login with your new password."}

    @staticmethod
    def change_password(db: Session, user_id: int, current_password: str, new_password: str) -> User:
        """Change user password"""
        user = AuthService.get_user_by_id(db, user_id)

        if not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsException()

        user.password_hash = hash_password(new_password)
        user.updated_at = get_current_utc()
        
        db.commit()
        db.refresh(user)
        
        # Send password changed notification
        try:
            NotificationService.send_password_changed_notification(db, user.id)
        except Exception as e:
            logger.error(f"Failed to send password changed notification: {str(e)}")

        logger.info(f"Password changed for user {user.username}")
        
        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """Get user by ID"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundException()
        return user

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

        expires_at = datetime.fromtimestamp(payload["exp"])

        AuthService._blacklist_token(db, refresh_token, expires_at)

        user_info = AuthService._build_user_info(user)

        new_access_token = Security.create_access_token(
            data={"sub": str(user.id)},
            user_info=user_info
        )
        new_refresh_token = Security.create_refresh_token(
            data={"sub": str(user.id)},
            user_info=user_info
        )

        return new_access_token, new_refresh_token

    @staticmethod
    def logout_user(db: Session, access_token: str, refresh_token: Optional[str] = None) -> dict:
        """Logout user by blacklisting tokens"""
        try:
            payload = Security.verify_token(access_token, token_type="access")
            expires_at = datetime.fromtimestamp(payload["exp"])
            AuthService._blacklist_token(db, access_token, expires_at)
        except Exception as e:
            logger.warning(f"Could not blacklist access token: {str(e)}")

        if refresh_token:
            try:
                payload = Security.verify_token(refresh_token, token_type="refresh")
                expires_at = datetime.fromtimestamp(payload["exp"])
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
        now = get_current_utc()
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

    @staticmethod
    def cleanup_expired_reset_tokens(db: Session) -> int:
        """Remove expired and used reset tokens"""
        now = get_current_utc()
        try:
            expired = db.query(PasswordResetToken).filter(
                PasswordResetToken.expires_at < now
            ).all()
            
            one_hour_ago = now - timedelta(hours=1)
            used_old = db.query(PasswordResetToken).filter(
                PasswordResetToken.is_used == True,
                PasswordResetToken.created_at < one_hour_ago
            ).all()
            
            total = len(expired) + len(used_old)
            
            for token in expired + used_old:
                db.delete(token)
            
            if total > 0:
                db.commit()
                logger.info(f"Cleaned up {total} expired/used reset tokens")
            
            return total
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to cleanup reset tokens: {str(e)}")
            raise

    @staticmethod
    def cleanup_expired_verification_tokens(db: Session) -> int:
        """Remove expired and used verification tokens"""
        now = get_current_utc()
        try:
            expired = db.query(EmailVerificationToken).filter(
                EmailVerificationToken.expires_at < now
            ).all()
            
            one_day_ago = now - timedelta(hours=24)
            used_old = db.query(EmailVerificationToken).filter(
                EmailVerificationToken.is_used == True,
                EmailVerificationToken.created_at < one_day_ago
            ).all()
            
            total = len(expired) + len(used_old)
            
            for token in expired + used_old:
                db.delete(token)
            
            if total > 0:
                db.commit()
                logger.info(f"Cleaned up {total} expired/used verification tokens")
            
            return total
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to cleanup verification tokens: {str(e)}")
            raise
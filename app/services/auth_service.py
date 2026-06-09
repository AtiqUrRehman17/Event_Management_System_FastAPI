from sqlalchemy.orm import Session
from datetime import datetime, timedelta
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
        Returns: User object only (token is NOT returned for security)
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
        logger.info(f"Verifying email with token: {token[:20]}...")
        
        # Find valid verification token
        verification_record = db.query(EmailVerificationToken).filter(
            EmailVerificationToken.token == token,
            EmailVerificationToken.is_used == False
        ).first()

        if not verification_record:
            # Check if token exists but is used
            used_record = db.query(EmailVerificationToken).filter(
                EmailVerificationToken.token == token,
                EmailVerificationToken.is_used == True
            ).first()
            
            if used_record:
                logger.warning(f"Token already used: {token[:20]}...")
                raise InvalidTokenException()
            
            # Check if token exists but expired
            expired_record = db.query(EmailVerificationToken).filter(
                EmailVerificationToken.token == token
            ).first()
            
            if expired_record and expired_record.is_expired:
                logger.warning(f"Token expired: {token[:20]}...")
                db.delete(expired_record)
                db.commit()
                raise InvalidTokenException()
            
            logger.warning(f"No token found: {token[:20]}...")
            raise InvalidTokenException()

        # Check if token is expired
        if verification_record.is_expired:
            logger.warning(f"Token expired: {token[:20]}...")
            db.delete(verification_record)
            db.commit()
            raise InvalidTokenException()

        # Get user
        user = db.query(User).filter(User.id == verification_record.user_id).first()
        if not user:
            logger.warning(f"User not found for token: {token[:20]}...")
            raise UserNotFoundException()

        # Check if already verified
        if user.is_verified:
            logger.info(f"User already verified: {user.username}")
            return {"message": "Email already verified", "is_verified": True}

        # Mark user as verified
        user.is_verified = True
        user.updated_at = get_current_utc()

        # Mark token as used
        verification_record.is_used = True

        db.commit()

        logger.info(f"Email verified successfully for user {user.username}")

        # Send confirmation email
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
        """
        Resend verification email to user
        """
        # Find user by email
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # For security, don't reveal if user exists
            return {"message": "If your email is registered, you will receive a verification email"}

        # Check if already verified
        if user.is_verified:
            return {"message": "Email already verified", "is_verified": True}

        # Check for existing unused token and delete it
        existing_token = db.query(EmailVerificationToken).filter(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.is_used == False
        ).first()
        
        if existing_token:
            db.delete(existing_token)
            db.commit()
            logger.info(f"Deleted existing verification token for user {user.username}")

        # Generate new verification token
        verification_token = secrets.token_urlsafe(32)
        expires_at = get_current_utc() + timedelta(minutes=settings.VERIFICATION_TOKEN_EXPIRE_MINUTES)

        # Create new verification token record
        verification_record = EmailVerificationToken(
            token=verification_token,
            user_id=user.id,
            expires_at=expires_at,
            is_used=False
        )
        
        db.add(verification_record)
        db.commit()

        logger.info(f"New verification token created for user {user.username}")

        # Send verification email
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
        """
        Authenticate user using username and password
        Check email verification if required
        """
        user = db.query(User).filter(
            User.username == login_data.username.lower()
        ).first()
        if not user:
            raise InvalidCredentialsException()

        if not verify_password(login_data.password, user.password_hash):
            raise InvalidCredentialsException()

        if not user.is_active:
            raise InvalidCredentialsException()

        # Check email verification
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
        """
        Send password reset email to user with reset token
        """
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            # For security, don't reveal if user exists
            return {
                "message": "If your email is registered, you will receive a password reset email"
            }

        # Generate secure token
        reset_token = secrets.token_urlsafe(32)
        
        # Calculate expiry
        expires_at = get_current_utc() + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)

        # Create reset token record
        reset_token_record = PasswordResetToken(
            token=reset_token,
            user_id=user.id,
            expires_at=expires_at,
            is_used=False
        )
        
        db.add(reset_token_record)
        db.commit()

        # Send email with token
        email_sent = EmailService.send_password_reset_email(
            to_email=user.email,
            username=user.username,
            reset_token=reset_token
        )

        if not email_sent:
            logger.error(f"Failed to send password reset email to {user.email}")
            return {
                "message": "Unable to send reset email. Please try again later."
            }

        logger.info(f"Password reset email sent to {user.email}")
        return {"message": "If your email is registered, you will receive a password reset email"}

    @staticmethod
    def reset_password(db: Session, request: ResetPasswordRequest) -> dict:
        """
        Reset password using valid token
        """
        # Find valid reset token
        reset_record = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == request.token,
            PasswordResetToken.is_used == False
        ).first()

        if not reset_record:
            raise InvalidTokenException()

        # Check if token is expired
        if reset_record.is_expired:
            db.delete(reset_record)
            db.commit()
            raise InvalidTokenException()

        # Get user
        user = db.query(User).filter(User.id == reset_record.user_id).first()
        if not user:
            raise UserNotFoundException()

        # Update password
        user.password_hash = hash_password(request.new_password)
        user.updated_at = get_current_utc()

        # Mark token as used
        reset_record.is_used = True

        db.commit()

        # Send confirmation email
        EmailService.send_password_reset_confirmation(
            to_email=user.email,
            username=user.username
        )

        logger.info(f"Password reset successful for user {user.username}")
        return {"message": "Password reset successful. You can now login with your new password."}

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

        # Convert timestamp to naive datetime for blacklist
        expires_at = datetime.fromtimestamp(payload["exp"])

        AuthService._blacklist_token(
            db=db,
            token=refresh_token,
            expires_at=expires_at
        )

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
            # Delete expired tokens
            expired = db.query(PasswordResetToken).filter(
                PasswordResetToken.expires_at < now
            ).all()
            
            # Delete used tokens older than 1 hour
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
            # Delete expired tokens
            expired = db.query(EmailVerificationToken).filter(
                EmailVerificationToken.expires_at < now
            ).all()
            
            # Delete used tokens older than 24 hours
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
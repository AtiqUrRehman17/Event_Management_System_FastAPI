from sqlalchemy.orm import Session
from typing import Optional, Tuple, List
from datetime import datetime, timezone
from app.models.user import User
from app.models.token_blacklist import TokenBlacklist
from app.schemas.user import UserUpdate, UserProfileUpdate
from app.utils.auth_utils import hash_password, verify_password
from app.core.exceptions import UserNotFoundException, EmailAlreadyExistsException, InvalidCredentialsException
from app.core.enums import UserRole
from app.pagination import PaginationParams, paginate_query
import logging

logger = logging.getLogger(__name__)


class UserService:

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """Get user by ID"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundException()
        return user

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username.lower()).first()

    @staticmethod
    def update_user_profile(db: Session, user_id: int, profile_data: UserProfileUpdate) -> User:
        """Update user profile (user self-update)"""
        user = UserService.get_user_by_id(db, user_id)

        # Check email uniqueness if being changed
        if profile_data.email and profile_data.email != user.email:
            existing_user = UserService.get_user_by_email(db, profile_data.email)
            if existing_user:
                raise EmailAlreadyExistsException()
            user.email = profile_data.email

        # Update fields
        if profile_data.first_name is not None:
            user.first_name = profile_data.first_name
        if profile_data.last_name is not None:
            user.last_name = profile_data.last_name
        if profile_data.phone is not None:
            user.phone = profile_data.phone
        if profile_data.bio is not None:
            user.bio = profile_data.bio
        if profile_data.timezone is not None:
            user.timezone = profile_data.timezone
        if profile_data.profile_picture is not None:
            user.profile_picture = str(profile_data.profile_picture)

        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def change_password(
        db: Session, 
        user_id: int, 
        current_password: str, 
        new_password: str,
        blacklist_all_tokens: bool = True
    ) -> User:
        """
        Change user password.
        Optionally blacklist all user tokens to force re-login.
        """
        user = UserService.get_user_by_id(db, user_id)

        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsException()

        # Update password
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)

        # Optional: Blacklist all active tokens for this user
        if blacklist_all_tokens:
            # Note: This requires adding user_id to token blacklist or 
            # implementing a token versioning system
            logger.info(f"Password changed for user {user.id}. Tokens should be invalidated.")
            # For now, we'll just log this. Full implementation would require
            # storing token version in user table or blacklisting by user_id

        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def get_all_users(
        db: Session,
        pagination: PaginationParams,
        role: Optional[UserRole] = None,
        search: Optional[str] = None
    ) -> Tuple[List[User], int]:
        """Get all users with pagination and filters (Admin only)"""
        query = db.query(User)

        if role:
            query = query.filter(User.role == role)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.username.ilike(search_term)) |
                (User.email.ilike(search_term)) |
                (User.first_name.ilike(search_term)) |
                (User.last_name.ilike(search_term)) |
                (User.phone.ilike(search_term))
            )

        # Use pagination module
        users, total = paginate_query(query, pagination)

        return users, total

    @staticmethod
    def deactivate_user(db: Session, user_id: int) -> User:
        """Deactivate a user account (Admin only)"""
        user = UserService.get_user_by_id(db, user_id)
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def activate_user(db: Session, user_id: int) -> User:
        """Activate a user account (Admin only)"""
        user = UserService.get_user_by_id(db, user_id)
        user.is_active = True
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        return user
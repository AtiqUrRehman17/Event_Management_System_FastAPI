from sqlalchemy.orm import Session
from app.models.user import User
from app.core.enums import UserRole
from app.utils.auth_utils import hash_password
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def seed_admin(db: Session) -> None:
    """Create default admin user if no admin exists."""
    try:
        existing_admin = db.query(User).filter(
            User.role == UserRole.ADMIN
        ).first()

        if existing_admin:
            logger.info(
                f"Admin already exists: {existing_admin.username} "
                f"- Skipping seed"
            )
            return

        admin = User(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            first_name=settings.ADMIN_FIRST_NAME,
            last_name=settings.ADMIN_LAST_NAME,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,  # Admin is auto-verified
            phone=None,
            bio="System Administrator",
            timezone="UTC",
            profile_picture=None,
            oauth_provider=None,
            oauth_id=None
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        logger.info(
            f"Default admin created successfully - username: {admin.username}"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed admin user: {str(e)}")
        raise
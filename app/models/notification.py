from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.utils.datetime_utils import get_current_utc
import enum


class NotificationType(str, enum.Enum):
    """Types of notifications"""
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"
    PAYMENT_SUCCESSFUL = "payment_successful"
    PAYMENT_FAILED = "payment_failed"
    EVENT_REMINDER = "event_reminder"
    WAITLIST_PROMOTION = "waitlist_promotion"
    WAITLIST_EXPIRY = "waitlist_expiry"
    EVENT_CANCELLED = "event_cancelled"
    PASSWORD_CHANGED = "password_changed"
    PROFILE_UPDATED = "profile_updated"


class NotificationChannel(str, enum.Enum):
    """Notification channels"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationStatus(str, enum.Enum):
    """Notification status"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(String(1000), nullable=False)
    channel = Column(SQLEnum(NotificationChannel), nullable=False)
    status = Column(SQLEnum(NotificationStatus), default=NotificationStatus.PENDING)
    is_read = Column(Boolean, default=False, index=True)
    extra_data = Column(String(500), nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_current_utc, nullable=False)
    
    # Relationships
    user = relationship("User", backref="notifications")
    
    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type}, is_read={self.is_read})>"


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Channel preferences
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)
    push_enabled = Column(Boolean, default=False)
    in_app_enabled = Column(Boolean, default=True)
    
    # Type-specific preferences (which notification types to receive)
    booking_confirmed_enabled = Column(Boolean, default=True)
    booking_cancelled_enabled = Column(Boolean, default=True)
    payment_successful_enabled = Column(Boolean, default=True)
    payment_failed_enabled = Column(Boolean, default=True)
    event_reminder_enabled = Column(Boolean, default=True)
    waitlist_promotion_enabled = Column(Boolean, default=True)
    waitlist_expiry_enabled = Column(Boolean, default=True)
    event_cancelled_enabled = Column(Boolean, default=True)
    password_changed_enabled = Column(Boolean, default=True)
    profile_updated_enabled = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=get_current_utc, nullable=False)
    updated_at = Column(DateTime, default=get_current_utc, onupdate=get_current_utc, nullable=False)
    
    # Relationships
    user = relationship("User", backref="notification_preferences")
    
    def __repr__(self) -> str:
        return f"<NotificationPreference(user_id={self.user_id}, email_enabled={self.email_enabled})>"
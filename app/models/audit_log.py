from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.utils.datetime_utils import get_current_utc
import enum


class AuditActionCategory(str, enum.Enum):
    """Categories of audit actions"""
    USER = "user"
    EVENT = "event"
    BOOKING = "booking"
    PAYMENT = "payment"
    ADMIN = "admin"
    AUTH = "auth"


class AuditActionType(str, enum.Enum):
    """Specific action types for audit logging"""
    # User actions
    USER_REGISTER = "user.register"
    USER_LOGIN_SUCCESS = "user.login.success"
    USER_LOGIN_FAILED = "user.login.failed"
    USER_LOGOUT = "user.logout"
    USER_PASSWORD_CHANGE = "user.password.change"
    USER_PROFILE_UPDATE = "user.profile.update"
    USER_ACCOUNT_ACTIVATE = "user.account.activate"
    USER_ACCOUNT_DEACTIVATE = "user.account.deactivate"
    USER_ROLE_CHANGE = "user.role.change"
    
    # Event actions
    EVENT_CREATE = "event.create"
    EVENT_UPDATE = "event.update"
    EVENT_DELETE = "event.delete"
    EVENT_STATUS_CHANGE = "event.status.change"
    
    # Booking actions
    BOOKING_CREATE = "booking.create"
    BOOKING_CANCEL = "booking.cancel"
    BOOKING_ADMIN_CANCEL = "booking.admin.cancel"
    
    # Payment actions
    PAYMENT_INITIATE = "payment.initiate"
    PAYMENT_SUCCESS = "payment.success"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_UPDATE = "payment.update"
    PAYMENT_REFUND = "payment.refund"
    
    # Admin actions
    ADMIN_ACTION = "admin.action"
    ADMIN_CATEGORY_CREATE = "admin.category.create"
    ADMIN_CATEGORY_UPDATE = "admin.category.update"
    ADMIN_CATEGORY_DELETE = "admin.category.delete"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=True, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=get_current_utc, nullable=False, index=True)
    
    # Relationship
    user = relationship("User", backref="audit_logs")
    
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action={self.action}, created_at={self.created_at})>"
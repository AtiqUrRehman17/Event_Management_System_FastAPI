from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class AuditActionCategoryEnum(str, Enum):
    USER = "user"
    EVENT = "event"
    BOOKING = "booking"
    PAYMENT = "payment"
    ADMIN = "admin"
    AUTH = "auth"


class AuditActionTypeEnum(str, Enum):
    USER_REGISTER = "user.register"
    USER_LOGIN_SUCCESS = "user.login.success"
    USER_LOGIN_FAILED = "user.login.failed"
    USER_LOGOUT = "user.logout"
    USER_PASSWORD_CHANGE = "user.password.change"
    USER_PROFILE_UPDATE = "user.profile.update"
    USER_ACCOUNT_ACTIVATE = "user.account.activate"
    USER_ACCOUNT_DEACTIVATE = "user.account.deactivate"
    USER_ROLE_CHANGE = "user.role.change"
    EVENT_CREATE = "event.create"
    EVENT_UPDATE = "event.update"
    EVENT_DELETE = "event.delete"
    EVENT_STATUS_CHANGE = "event.status.change"
    BOOKING_CREATE = "booking.create"
    BOOKING_CANCEL = "booking.cancel"
    BOOKING_ADMIN_CANCEL = "booking.admin.cancel"
    PAYMENT_INITIATE = "payment.initiate"
    PAYMENT_SUCCESS = "payment.success"
    PAYMENT_FAILED = "payment.failed"
    ADMIN_ACTION = "admin.action"
    ADMIN_CATEGORY_CREATE = "admin.category.create"
    ADMIN_CATEGORY_UPDATE = "admin.category.update"
    ADMIN_CATEGORY_DELETE = "admin.category.delete"


class AuditLogResponse(BaseModel):
    """Audit log entry response"""
    id: int
    user_id: Optional[int]
    username: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    category: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    old_value: Optional[str]
    new_value: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated audit log list response"""
    logs: List[AuditLogResponse]
    total: int
    page: int
    limit: int
    total_pages: int
    filters_applied: Dict[str, Any]


class AuditLogFilterParams(BaseModel):
    """Filter parameters for audit logs"""
    user_id: Optional[int] = None
    action: Optional[str] = None
    category: Optional[AuditActionCategoryEnum] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    limit: int = 50


class AuditSummaryResponse(BaseModel):
    """Audit log summary statistics"""
    total_logs: int
    logs_by_category: Dict[str, int]
    logs_by_action: Dict[str, int]
    recent_activity: List[AuditLogResponse]
    top_users: List[Dict[str, Any]]
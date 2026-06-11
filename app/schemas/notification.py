from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class NotificationTypeEnum(str, Enum):
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


class NotificationChannelEnum(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationStatusEnum(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


class NotificationResponse(BaseModel):
    """Notification response schema"""
    id: int
    user_id: int
    type: NotificationTypeEnum
    title: str
    message: str
    channel: NotificationChannelEnum
    status: NotificationStatusEnum
    is_read: bool
    extra_data: Optional[str] = None  # Renamed from 'metadata'
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Paginated notification list response"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    limit: int
    total_pages: int


class MarkNotificationsReadRequest(BaseModel):
    """Request to mark notifications as read"""
    notification_ids: Optional[List[int]] = Field(None, description="List of notification IDs to mark as read. If null, mark all as read.")


class NotificationPreferenceResponse(BaseModel):
    """User notification preferences response"""
    user_id: int
    email_enabled: bool
    sms_enabled: bool
    push_enabled: bool
    in_app_enabled: bool
    booking_confirmed_enabled: bool
    booking_cancelled_enabled: bool
    payment_successful_enabled: bool
    payment_failed_enabled: bool
    event_reminder_enabled: bool
    waitlist_promotion_enabled: bool
    waitlist_expiry_enabled: bool
    event_cancelled_enabled: bool
    password_changed_enabled: bool
    profile_updated_enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NotificationPreferenceUpdate(BaseModel):
    """Update user notification preferences"""
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    booking_confirmed_enabled: Optional[bool] = None
    booking_cancelled_enabled: Optional[bool] = None
    payment_successful_enabled: Optional[bool] = None
    payment_failed_enabled: Optional[bool] = None
    event_reminder_enabled: Optional[bool] = None
    waitlist_promotion_enabled: Optional[bool] = None
    waitlist_expiry_enabled: Optional[bool] = None
    event_cancelled_enabled: Optional[bool] = None
    password_changed_enabled: Optional[bool] = None
    profile_updated_enabled: Optional[bool] = None


class SendTestNotificationRequest(BaseModel):
    """Send test notification request (Admin only)"""
    user_id: int
    type: NotificationTypeEnum
    title: str
    message: str
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from app.dependencies import get_db, get_current_user, get_current_admin
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse, NotificationListResponse, MarkNotificationsReadRequest,
    NotificationPreferenceResponse, NotificationPreferenceUpdate, SendTestNotificationRequest,
    NotificationTypeEnum, NotificationChannelEnum
)
from app.services.notification_service import NotificationService
from app.utils.response import success_response

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ==================== User Notification Endpoints ====================

@router.get("/", response_model=dict)
async def get_my_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_read: Optional[bool] = None,
    notification_type: Optional[NotificationTypeEnum] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's notifications with pagination.
    """
    notifications, total, unread_count, total_pages = NotificationService.get_user_notifications(
        db, current_user.id, page, limit, is_read, notification_type
    )
    
    return success_response(
        data={
            "notifications": [
                {
                    "id": n.id,
                    "type": n.type.value,
                    "title": n.title,
                    "message": n.message,
                    "channel": n.channel.value,
                    "status": n.status.value,
                    "is_read": n.is_read,
                    "metadata": n.metadata,
                    "sent_at": n.sent_at,
                    "read_at": n.read_at,
                    "created_at": n.created_at
                }
                for n in notifications
            ],
            "total": total,
            "unread_count": unread_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        },
        message="Notifications retrieved successfully"
    )


@router.get("/unread/count", response_model=dict)
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get count of unread notifications.
    """
    count = NotificationService.get_unread_count(db, current_user.id)
    
    return success_response(
        data={"unread_count": count},
        message="Unread count retrieved successfully"
    )


@router.post("/mark-read", response_model=dict)
async def mark_notifications_read(
    request: MarkNotificationsReadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark notifications as read.
    If notification_ids is not provided, marks all unread notifications as read.
    """
    count = NotificationService.mark_as_read(db, current_user.id, request.notification_ids)
    
    return success_response(
        data={"marked_count": count},
        message=f"{count} notification(s) marked as read"
    )


@router.delete("/{notification_id}", response_model=dict)
async def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a notification.
    """
    success = NotificationService.delete_notification(db, current_user.id, notification_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return success_response(
        data=None,
        message="Notification deleted successfully"
    )


# ==================== Notification Preferences Endpoints ====================

@router.get("/preferences", response_model=dict)
async def get_my_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's notification preferences.
    """
    prefs = NotificationService.get_user_preferences(db, current_user.id)
    
    return success_response(
        data={
            "user_id": prefs.user_id,
            "email_enabled": prefs.email_enabled,
            "sms_enabled": prefs.sms_enabled,
            "push_enabled": prefs.push_enabled,
            "in_app_enabled": prefs.in_app_enabled,
            "booking_confirmed_enabled": prefs.booking_confirmed_enabled,
            "booking_cancelled_enabled": prefs.booking_cancelled_enabled,
            "payment_successful_enabled": prefs.payment_successful_enabled,
            "payment_failed_enabled": prefs.payment_failed_enabled,
            "event_reminder_enabled": prefs.event_reminder_enabled,
            "waitlist_promotion_enabled": prefs.waitlist_promotion_enabled,
            "waitlist_expiry_enabled": prefs.waitlist_expiry_enabled,
            "event_cancelled_enabled": prefs.event_cancelled_enabled,
            "password_changed_enabled": prefs.password_changed_enabled,
            "profile_updated_enabled": prefs.profile_updated_enabled,
            "created_at": prefs.created_at,
            "updated_at": prefs.updated_at
        },
        message="Notification preferences retrieved successfully"
    )


@router.put("/preferences", response_model=dict)
async def update_my_preferences(
    updates: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update current user's notification preferences.
    """
    prefs = NotificationService.update_user_preferences(
        db, current_user.id, updates.dict(exclude_unset=True)
    )
    
    return success_response(
        data={
            "user_id": prefs.user_id,
            "email_enabled": prefs.email_enabled,
            "sms_enabled": prefs.sms_enabled,
            "push_enabled": prefs.push_enabled,
            "in_app_enabled": prefs.in_app_enabled,
            "booking_confirmed_enabled": prefs.booking_confirmed_enabled,
            "booking_cancelled_enabled": prefs.booking_cancelled_enabled,
            "payment_successful_enabled": prefs.payment_successful_enabled,
            "payment_failed_enabled": prefs.payment_failed_enabled,
            "event_reminder_enabled": prefs.event_reminder_enabled,
            "waitlist_promotion_enabled": prefs.waitlist_promotion_enabled,
            "waitlist_expiry_enabled": prefs.waitlist_expiry_enabled,
            "event_cancelled_enabled": prefs.event_cancelled_enabled,
            "password_changed_enabled": prefs.password_changed_enabled,
            "profile_updated_enabled": prefs.profile_updated_enabled,
            "created_at": prefs.created_at,
            "updated_at": prefs.updated_at
        },
        message="Notification preferences updated successfully"
    )


# ==================== Admin Endpoints ====================

@router.post("/test", response_model=dict)
async def send_test_notification(
    request: SendTestNotificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Send a test notification to a user (Admin only).
    """
    from app.models.notification import NotificationType, NotificationChannel
    
    notification = NotificationService.create_notification(
        db=db,
        user_id=request.user_id,
        notification_type=NotificationType(request.type.value),
        title=request.title,
        message=request.message,
        channel=NotificationChannel.EMAIL,
        metadata={"test": True}
    )
    
    return success_response(
        data={"notification_id": notification.id if notification else None},
        message="Test notification sent successfully" if notification else "Notification was suppressed by user preferences"
    )


@router.post("/send-event-reminders", response_model=dict)
async def send_event_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Manually trigger event reminders (Admin only).
    """
    from app.services.notification_service import NotificationService
    
    NotificationService.send_event_reminders(db)
    
    return success_response(
        data=None,
        message="Event reminders sent successfully"
    )
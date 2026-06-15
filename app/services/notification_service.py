from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import logging
from fastapi import HTTPException, status
from app.models.notification import Notification, NotificationPreference, NotificationType, NotificationChannel, NotificationStatus
from app.models.user import User
from app.models.event import Event
from app.models.booking import Booking
from app.schemas.notification import NotificationTypeEnum, NotificationChannelEnum
from app.services.email_service import EmailService
from app.utils.datetime_utils import get_current_utc
from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    
    # ==================== Notification Creation ====================
    
    @staticmethod
    def create_notification(
        db: Session,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        channel: NotificationChannel,
        extra_data: Optional[Dict] = None
    ) -> Notification:
        """Create a notification record"""
        
        # Check user preferences
        if not NotificationService._should_send_notification(db, user_id, notification_type, channel):
            logger.info(f"Notification suppressed due to user preferences: user={user_id}, type={notification_type}, channel={channel}")
            return None
        
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            channel=channel,
            status=NotificationStatus.PENDING,
            extra_data=json.dumps(extra_data) if extra_data else None
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # Send notification through the appropriate channel
        NotificationService._deliver_notification(db, notification)
        
        return notification
    
    @staticmethod
    def _should_send_notification(
        db: Session,
        user_id: int,
        notification_type: NotificationType,
        channel: NotificationChannel
    ) -> bool:
        """Check if notification should be sent based on user preferences"""
        
        # Get user preferences
        prefs = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id
        ).first()
        
        if not prefs:
            # Default preferences if not set
            return True
        
        # Check channel preference
        if channel == NotificationChannel.EMAIL and not prefs.email_enabled:
            return False
        if channel == NotificationChannel.SMS and not prefs.sms_enabled:
            return False
        if channel == NotificationChannel.PUSH and not prefs.push_enabled:
            return False
        if channel == NotificationChannel.IN_APP and not prefs.in_app_enabled:
            return False
        
        # Check type preference
        type_pref_map = {
            NotificationType.BOOKING_CONFIRMED: prefs.booking_confirmed_enabled,
            NotificationType.BOOKING_CANCELLED: prefs.booking_cancelled_enabled,
            NotificationType.PAYMENT_SUCCESSFUL: prefs.payment_successful_enabled,
            NotificationType.PAYMENT_FAILED: prefs.payment_failed_enabled,
            NotificationType.EVENT_REMINDER: prefs.event_reminder_enabled,
            NotificationType.WAITLIST_PROMOTION: prefs.waitlist_promotion_enabled,
            NotificationType.WAITLIST_EXPIRY: prefs.waitlist_expiry_enabled,
            NotificationType.EVENT_CANCELLED: prefs.event_cancelled_enabled,
            NotificationType.PASSWORD_CHANGED: prefs.password_changed_enabled,
            NotificationType.PROFILE_UPDATED: prefs.profile_updated_enabled,
        }
        
        return type_pref_map.get(notification_type, True)
    
    @staticmethod
    def _deliver_notification(db: Session, notification: Notification):
        """Deliver notification through its channel"""
        
        user = db.query(User).filter(User.id == notification.user_id).first()
        if not user:
            notification.status = NotificationStatus.FAILED
            db.commit()
            return
        
        success = False
        
        if notification.channel == NotificationChannel.EMAIL:
            success = NotificationService._send_email_notification(user, notification)
        elif notification.channel == NotificationChannel.SMS:
            success = NotificationService._send_sms_notification(user, notification)
        elif notification.channel == NotificationChannel.PUSH:
            success = NotificationService._send_push_notification(user, notification)
        elif notification.channel == NotificationChannel.IN_APP:
            success = True  # In-app is already saved in DB
        
        if success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = get_current_utc()
        else:
            notification.status = NotificationStatus.FAILED
        
        db.commit()
    
    @staticmethod
    def _send_email_notification(user: User, notification: Notification) -> bool:
        """Send email notification"""
        try:
            # Use email service to send notification
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #3498db; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>{notification.title}</h2>
                    </div>
                    <div class="content">
                        <p>Hello {user.first_name},</p>
                        <p>{notification.message}</p>
                        <hr>
                        <p>You can manage your notification preferences in your account settings.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return EmailService.send_email(
                to_email=user.email,
                subject=notification.title,
                html_content=html_content,
                text_content=notification.message
            )
        except Exception as e:
            logger.error(f"Failed to send email notification to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def _send_sms_notification(user: User, notification: Notification) -> bool:
        """Send SMS notification (placeholder - integrate with SMS provider)"""
        # TODO: Integrate with SMS provider like Twilio
        logger.info(f"SMS notification would be sent to {user.phone}: {notification.title}")
        return True
    
    @staticmethod
    def _send_push_notification(user: User, notification: Notification) -> bool:
        """Send push notification (placeholder - integrate with Firebase)"""
        # TODO: Integrate with push notification service like Firebase Cloud Messaging
        logger.info(f"Push notification would be sent to user {user.id}: {notification.title}")
        return True
    
    # ==================== Notification Retrieval ====================
    
    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: int,
        page: int = 1,
        limit: int = 20,
        is_read: Optional[bool] = None,
        notification_type: Optional[NotificationType] = None
    ) -> tuple:
        """Get user's notifications with pagination"""
        
        query = db.query(Notification).filter(Notification.user_id == user_id)
        
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        
        if notification_type:
            query = query.filter(Notification.type == notification_type)
        
        total = query.count()
        unread_count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()
        
        offset = (page - 1) * limit
        notifications = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
        
        total_pages = (total + limit - 1) // limit if total > 0 else 0
        
        return notifications, total, unread_count, total_pages
    
    @staticmethod
    def get_unread_count(db: Session, user_id: int) -> int:
        """Get unread notification count"""
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()
    
    @staticmethod
    def mark_as_read(db: Session, user_id: int, notification_ids: Optional[List[int]] = None) -> int:
        """Mark notifications as read"""
        
        query = db.query(Notification).filter(Notification.user_id == user_id)
        
        if notification_ids:
            query = query.filter(Notification.id.in_(notification_ids))
        else:
            query = query.filter(Notification.is_read == False)
        
        count = query.update(
            {"is_read": True, "read_at": get_current_utc()},
            synchronize_session=False
        )
        db.commit()
        
        return count
    
    @staticmethod
    def delete_notification(db: Session, user_id: int, notification_id: int) -> bool:
        """Delete a notification"""
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if not notification:
            return False
        
        db.delete(notification)
        db.commit()
        
        return True
    
    # ==================== Notification Preferences ====================
    
    @staticmethod
    def get_user_preferences(db: Session, user_id: int) -> NotificationPreference:
        """Get user's notification preferences"""
        
        prefs = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id
        ).first()
        
        if not prefs:
            # Create default preferences
            prefs = NotificationPreference(user_id=user_id)
            db.add(prefs)
            db.commit()
            db.refresh(prefs)
        
        return prefs
    
    @staticmethod
    def update_user_preferences(db: Session, user_id: int, updates: Dict) -> NotificationPreference:
        """Update user's notification preferences"""
        
        prefs = NotificationService.get_user_preferences(db, user_id)
        
        for key, value in updates.items():
            if hasattr(prefs, key) and value is not None:
                setattr(prefs, key, value)
        
        db.commit()
        db.refresh(prefs)
        
        return prefs
    
    # ==================== Automated Notifications ====================
    
    @staticmethod
    def send_booking_confirmation(db: Session, booking_id: int):
        """Send booking confirmation notification"""
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return
        
        event = booking.event
        user = booking.user
        
        # Create in-app notification
        NotificationService.create_notification(
            db=db,
            user_id=booking.user_id,
            notification_type=NotificationType.BOOKING_CONFIRMED,
            title="Booking Confirmed! 🎉",
            message=f"Your booking for '{event.title}' has been confirmed. You have booked {booking.number_of_seats} seat(s).",
            channel=NotificationChannel.IN_APP,
            extra_data={"booking_id": booking.id, "event_id": event.id}
        )
        
        # Send email using dedicated booking confirmation email template
        EmailService.send_booking_confirmation_email(
            to_email=user.email,
            username=user.username,
            event_title=event.title,
            booking_id=booking.id,
            seats=booking.number_of_seats,
            total_price=booking.total_price
        )
    
    @staticmethod
    def send_booking_cancellation(db: Session, booking_id: int):
        """Send booking cancellation notification"""
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return
        
        event = booking.event
        
        NotificationService.create_notification(
            db=db,
            user_id=booking.user_id,
            notification_type=NotificationType.BOOKING_CANCELLED,
            title="Booking Cancelled",
            message=f"Your booking for '{event.title}' has been cancelled. {booking.number_of_seats} seat(s) have been released.",
            channel=NotificationChannel.IN_APP,
            extra_data={"booking_id": booking.id, "event_id": event.id}
        )
        
        NotificationService.create_notification(
            db=db,
            user_id=booking.user_id,
            notification_type=NotificationType.BOOKING_CANCELLED,
            title=f"Booking Cancelled - {event.title}",
            message=f"Dear customer,\n\nYour booking for '{event.title}' has been cancelled.\n\nCancelled Booking Details:\n- Event: {event.title}\n- Date: {event.event_date}\n- Seats: {booking.number_of_seats}\n- Total Refund: ${booking.total_price}\n\nWe hope to see you at future events!",
            channel=NotificationChannel.EMAIL,
            extra_data={"booking_id": booking.id, "event_id": event.id}
        )
    
    @staticmethod
    def send_event_reminders(db: Session):
        """Send event reminders for events happening tomorrow"""
        tomorrow = get_current_utc() + timedelta(days=1)
        day_after = tomorrow + timedelta(days=1)
        
        # Find bookings for events happening tomorrow
        bookings = db.query(Booking).join(Event).filter(
            Event.event_date >= tomorrow,
            Event.event_date < day_after,
            Booking.status == "active"
        ).all()
        
        for booking in bookings:
            event = booking.event
            days_until = (event.event_date - get_current_utc()).days
            
            NotificationService.create_notification(
                db=db,
                user_id=booking.user_id,
                notification_type=NotificationType.EVENT_REMINDER,
                title=f"Event Reminder: {event.title}",
                message=f"Reminder: '{event.title}' is happening in {days_until} day(s)! Location: {event.location}. Don't forget to attend!",
                channel=NotificationChannel.IN_APP,
                extra_data={"booking_id": booking.id, "event_id": event.id}
            )
            
            NotificationService.create_notification(
                db=db,
                user_id=booking.user_id,
                notification_type=NotificationType.EVENT_REMINDER,
                title=f"Event Reminder - {event.title}",
                message=f"Dear customer,\n\nThis is a reminder that '{event.title}' is happening tomorrow!\n\nEvent Details:\n- Date: {event.event_date}\n- Location: {event.location}\n- Time: {event.event_date.strftime('%I:%M %p')}\n\nWe look forward to seeing you there!",
                channel=NotificationChannel.EMAIL,
                extra_data={"booking_id": booking.id, "event_id": event.id}
            )
    
    @staticmethod
    def send_waitlist_promotion(db: Session, user_id: int, event_id: int, position: int):
        """Send waitlist promotion notification"""
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return
        
        NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationType.WAITLIST_PROMOTION,
            title="Spot Available! 🎉",
            message=f"A spot has opened up for '{event.title}'! You are #{position} in line. Please confirm within 48 hours.",
            channel=NotificationChannel.IN_APP,
            extra_data={"event_id": event_id, "position": position}
        )
        
        NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationType.WAITLIST_PROMOTION,
            title=f"Spot Available - {event.title}",
            message=f"Dear customer,\n\nGood news! A spot has become available for '{event.title}'.\n\nYou are #{position} in line. Please confirm your interest within 48 hours to claim this spot.\n\nClick here to confirm: /api/v1/waitlist/{event_id}/confirm",
            channel=NotificationChannel.EMAIL,
            extra_data={"event_id": event_id, "position": position}
        )
    
    @staticmethod
    def send_event_cancellation(db: Session, event_id: int):
        """Send event cancellation notifications to all booked users"""
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return
        
        bookings = db.query(Booking).filter(
            Booking.event_id == event_id,
            Booking.status == "active"
        ).all()
        
        for booking in bookings:
            NotificationService.create_notification(
                db=db,
                user_id=booking.user_id,
                notification_type=NotificationType.EVENT_CANCELLED,
                title="Event Cancelled 😢",
                message=f"We regret to inform you that '{event.title}' has been cancelled. Your payment will be refunded.",
                channel=NotificationChannel.IN_APP,
                extra_data={"event_id": event_id}
            )
            
            NotificationService.create_notification(
                db=db,
                user_id=booking.user_id,
                notification_type=NotificationType.EVENT_CANCELLED,
                title=f"Event Cancelled - {event.title}",
                message=f"Dear customer,\n\nWe regret to inform you that '{event.title}' has been cancelled due to unforeseen circumstances.\n\nYour payment of ${booking.total_price} will be refunded to your original payment method within 5-7 business days.\n\nWe apologize for the inconvenience and hope to serve you at future events.",
                channel=NotificationChannel.EMAIL,
                extra_data={"event_id": event_id}
            )
    
    @staticmethod
    def send_password_changed_notification(db: Session, user_id: int):
        """Send password changed notification"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        
        NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationType.PASSWORD_CHANGED,
            title="Password Changed",
            message="Your password has been successfully changed. If you didn't make this change, please contact support immediately.",
            channel=NotificationChannel.IN_APP,
            extra_data={}
        )
        
        NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationType.PASSWORD_CHANGED,
            title="Password Changed - Security Alert",
            message=f"Dear {user.first_name},\n\nYour password has been successfully changed.\n\nIf you made this change, no further action is needed.\n\nIf you did NOT make this change, please contact our support team immediately to secure your account.\n\nBest regards,\nEvent Management System Team",
            channel=NotificationChannel.EMAIL,
            extra_data={}
        )
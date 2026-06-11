from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from app.models.waitlist import Waitlist, WaitlistStatus
from app.models.event import Event
from app.models.user import User
from app.models.booking import Booking
from app.core.enums import EventStatus, BookingStatus
from app.core.exceptions import EventNotFoundException, PermissionDeniedException
from app.utils.datetime_utils import get_current_utc
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)


class WaitlistService:
    
    @staticmethod
    def join_waitlist(db: Session, user_id: int, event_id: int) -> Waitlist:
        """Add user to event waitlist"""
        
        # Check if event exists
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise EventNotFoundException()
        
        # Check if event is sold out
        if event.available_seats > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event has available seats. Please book directly."
            )
        
        # Check if event is still upcoming
        if event.status != EventStatus.UPCOMING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot join waitlist for completed or cancelled events"
            )
        
        # Check if user already has an active waitlist entry
        existing = db.query(Waitlist).filter(
            Waitlist.user_id == user_id,
            Waitlist.event_id == event_id,
            Waitlist.status.in_([WaitlistStatus.WAITING, WaitlistStatus.NOTIFIED])
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already on the waitlist for this event"
            )
        
        # Get current max position
        max_position = db.query(func.max(Waitlist.position)).filter(
            Waitlist.event_id == event_id,
            Waitlist.status == WaitlistStatus.WAITING
        ).scalar() or 0
        
        # Create waitlist entry
        waitlist_entry = Waitlist(
            user_id=user_id,
            event_id=event_id,
            position=max_position + 1,
            status=WaitlistStatus.WAITING,
            joined_at=get_current_utc()
        )
        
        db.add(waitlist_entry)
        db.commit()
        db.refresh(waitlist_entry)
        
        # Send confirmation email
        user = db.query(User).filter(User.id == user_id).first()
        try:
            EmailService.send_waitlist_joined_email(
                to_email=user.email,
                username=user.username,
                event_title=event.title,
                position=waitlist_entry.position
            )
        except Exception as e:
            logger.error(f"Failed to send waitlist joined email: {str(e)}")
        
        # Create in-app notification
        try:
            from app.models.notification import NotificationType, NotificationChannel
            NotificationService.create_notification(
                db=db,
                user_id=user_id,
                notification_type=NotificationType.WAITLIST_PROMOTION,
                title="Added to Waitlist",
                message=f"You have been added to the waitlist for '{event.title}'. Your position is #{waitlist_entry.position}.",
                channel=NotificationChannel.IN_APP,
                metadata={"event_id": event_id, "position": waitlist_entry.position}
            )
        except Exception as e:
            logger.error(f"Failed to create waitlist notification: {str(e)}")
        
        logger.info(f"User {user_id} joined waitlist for event {event_id} at position {waitlist_entry.position}")
        
        return waitlist_entry
    
    @staticmethod
    def get_user_position(db: Session, user_id: int, event_id: int) -> Dict[str, Any]:
        """Get user's current position in waitlist"""
        
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise EventNotFoundException()
        
        # Get user's waitlist entry
        entry = db.query(Waitlist).filter(
            Waitlist.user_id == user_id,
            Waitlist.event_id == event_id
        ).first()
        
        if not entry:
            return {
                "position": None,
                "total_waiting": 0,
                "status": None,
                "estimated_chance": "N/A",
                "message": "You are not on the waitlist for this event"
            }
        
        # If user has been notified, check if notification expired
        if entry.status == WaitlistStatus.NOTIFIED and entry.expires_at:
            if get_current_utc() > entry.expires_at:
                entry.status = WaitlistStatus.EXPIRED
                db.commit()
        
        # Get total waiting count
        total_waiting = db.query(func.count(Waitlist.id)).filter(
            Waitlist.event_id == event_id,
            Waitlist.status == WaitlistStatus.WAITING
        ).scalar() or 0
        
        # Calculate estimated chance based on position and total capacity
        if entry.position <= 5:
            estimated_chance = "High"
        elif entry.position <= 15:
            estimated_chance = "Medium"
        elif entry.position <= 30:
            estimated_chance = "Low"
        else:
            estimated_chance = "Very Low"
        
        # Custom message based on position
        if entry.position == 1:
            message = "You are first in line! You'll be notified as soon as a spot opens up."
        elif entry.position <= 5:
            message = f"You are #{entry.position} in line. Good chance of getting a spot!"
        elif entry.position <= 15:
            message = f"You are #{entry.position} in line. Keep an eye on your email!"
        else:
            message = f"You are #{entry.position} in line. Consider checking other events as well."
        
        return {
            "position": entry.position,
            "total_waiting": total_waiting,
            "status": entry.status.value,
            "estimated_chance": estimated_chance,
            "message": message
        }
    
    @staticmethod
    def leave_waitlist(db: Session, user_id: int, event_id: int) -> Dict[str, Any]:
        """Remove user from waitlist"""
        
        entry = db.query(Waitlist).filter(
            Waitlist.user_id == user_id,
            Waitlist.event_id == event_id,
            Waitlist.status.in_([WaitlistStatus.WAITING, WaitlistStatus.NOTIFIED])
        ).first()
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You are not on the waitlist for this event"
            )
        
        # Store position and event title for logging
        old_position = entry.position
        event = db.query(Event).filter(Event.id == event_id).first()
        
        # Update status
        entry.status = WaitlistStatus.CANCELLED
        db.commit()
        
        # Recalculate positions for remaining users
        WaitlistService._recalculate_positions(db, event_id)
        
        # Create notification for leaving waitlist
        if event:
            try:
                from app.models.notification import NotificationType, NotificationChannel
                NotificationService.create_notification(
                    db=db,
                    user_id=user_id,
                    notification_type=NotificationType.WAITLIST_EXPIRY,
                    title="Left Waitlist",
                    message=f"You have left the waitlist for '{event.title}'.",
                    channel=NotificationChannel.IN_APP,
                    metadata={"event_id": event_id}
                )
            except Exception as e:
                logger.error(f"Failed to create leave waitlist notification: {str(e)}")
        
        logger.info(f"User {user_id} left waitlist for event {event_id} (was position {old_position})")
        
        return {
            "message": "You have been removed from the waitlist",
            "event_id": event_id
        }
    
    @staticmethod
    def _recalculate_positions(db: Session, event_id: int) -> None:
        """Recalculate positions for all waiting users"""
        waiting_entries = db.query(Waitlist).filter(
            Waitlist.event_id == event_id,
            Waitlist.status == WaitlistStatus.WAITING
        ).order_by(Waitlist.joined_at.asc()).all()
        
        for idx, entry in enumerate(waiting_entries, 1):
            entry.position = idx
        
        db.commit()
    
    @staticmethod
    def process_cancellation(db: Session, event_id: int) -> None:
        """Process when a booking is cancelled - notify next user in waitlist"""
        
        # Get first waiting user
        next_in_line = db.query(Waitlist).filter(
            Waitlist.event_id == event_id,
            Waitlist.status == WaitlistStatus.WAITING
        ).order_by(Waitlist.position.asc()).first()
        
        if not next_in_line:
            return
        
        # Update status to notified
        next_in_line.status = WaitlistStatus.NOTIFIED
        next_in_line.notified_at = get_current_utc()
        next_in_line.expires_at = get_current_utc() + timedelta(hours=48)  # 48 hours to confirm
        
        db.commit()
        
        # Send notification email
        user = db.query(User).filter(User.id == next_in_line.user_id).first()
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if user and event:
            try:
                EmailService.send_waitlist_notification_email(
                    to_email=user.email,
                    username=user.username,
                    event_title=event.title,
                    event_id=event_id,
                    expires_at=next_in_line.expires_at
                )
            except Exception as e:
                logger.error(f"Failed to send waitlist notification email: {str(e)}")
            
            # Create in-app notification
            try:
                from app.models.notification import NotificationType, NotificationChannel
                NotificationService.create_notification(
                    db=db,
                    user_id=next_in_line.user_id,
                    notification_type=NotificationType.WAITLIST_PROMOTION,
                    title="Spot Available! 🎉",
                    message=f"A spot has opened up for '{event.title}'! You have 48 hours to confirm your spot.",
                    channel=NotificationChannel.IN_APP,
                    metadata={"event_id": event_id, "expires_at": next_in_line.expires_at.isoformat()}
                )
            except Exception as e:
                logger.error(f"Failed to create waitlist promotion notification: {str(e)}")
        
        logger.info(f"Notified user {next_in_line.user_id} about available spot for event {event_id}")
    
    @staticmethod
    def confirm_spot(db: Session, user_id: int, event_id: int) -> Dict[str, Any]:
        """User confirms they want the available spot"""
        
        entry = db.query(Waitlist).filter(
            Waitlist.user_id == user_id,
            Waitlist.event_id == event_id,
            Waitlist.status == WaitlistStatus.NOTIFIED
        ).first()
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No pending notification found for this event"
            )
        
        # Check if expired
        if entry.expires_at and get_current_utc() > entry.expires_at:
            entry.status = WaitlistStatus.EXPIRED
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your offer has expired. Please rejoin the waitlist."
            )
        
        # Mark as confirmed
        entry.status = WaitlistStatus.CONFIRMED
        entry.confirmed_at = get_current_utc()
        db.commit()
        
        # Recalculate positions
        WaitlistService._recalculate_positions(db, event_id)
        
        # Create confirmation notification
        event = db.query(Event).filter(Event.id == event_id).first()
        if event:
            try:
                from app.models.notification import NotificationType, NotificationChannel
                NotificationService.create_notification(
                    db=db,
                    user_id=user_id,
                    notification_type=NotificationType.WAITLIST_PROMOTION,
                    title="Spot Confirmed!",
                    message=f"You have confirmed your spot for '{event.title}'. You can now book your ticket.",
                    channel=NotificationChannel.IN_APP,
                    metadata={"event_id": event_id}
                )
            except Exception as e:
                logger.error(f"Failed to create spot confirmation notification: {str(e)}")
        
        logger.info(f"User {user_id} confirmed spot for event {event_id}")
        
        return {
            "message": "Spot confirmed! You can now book your ticket.",
            "event_id": event_id,
            "expires_at": entry.expires_at
        }
    
    @staticmethod
    def get_event_waitlist_summary(db: Session, event_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get waitlist summary for an event"""
        
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise EventNotFoundException()
        
        # Get counts by status
        total_waiting = db.query(func.count(Waitlist.id)).filter(
            Waitlist.event_id == event_id,
            Waitlist.status == WaitlistStatus.WAITING
        ).scalar() or 0
        
        total_notified = db.query(func.count(Waitlist.id)).filter(
            Waitlist.event_id == event_id,
            Waitlist.status == WaitlistStatus.NOTIFIED
        ).scalar() or 0
        
        total_confirmed = db.query(func.count(Waitlist.id)).filter(
            Waitlist.event_id == event_id,
            Waitlist.status == WaitlistStatus.CONFIRMED
        ).scalar() or 0
        
        total_expired = db.query(func.count(Waitlist.id)).filter(
            Waitlist.event_id == event_id,
            Waitlist.status == WaitlistStatus.EXPIRED
        ).scalar() or 0
        
        result = {
            "event_id": event_id,
            "event_title": event.title,
            "total_waiting": total_waiting,
            "total_notified": total_notified,
            "total_confirmed": total_confirmed,
            "total_expired": total_expired
        }
        
        # If user is authenticated, check their position
        if user_id:
            user_entry = db.query(Waitlist).filter(
                Waitlist.user_id == user_id,
                Waitlist.event_id == event_id
            ).first()
            
            if user_entry:
                result["your_position"] = user_entry.position if user_entry.status == WaitlistStatus.WAITING else None
                result["your_status"] = user_entry.status.value
        
        return result
    
    @staticmethod
    def get_event_waitlist_admin(
        db: Session, 
        event_id: int, 
        page: int = 1, 
        limit: int = 50
    ) -> Tuple[List[Waitlist], int]:
        """Admin view of waitlist entries"""
        
        query = db.query(Waitlist).filter(Waitlist.event_id == event_id)
        
        total = query.count()
        offset = (page - 1) * limit
        entries = query.order_by(Waitlist.position.asc()).offset(offset).limit(limit).all()
        
        return entries, total
    
    @staticmethod
    def cleanup_expired_notifications(db: Session) -> int:
        """Clean up expired notifications (run via scheduler)"""
        now = get_current_utc()
        
        expired = db.query(Waitlist).filter(
            Waitlist.status == WaitlistStatus.NOTIFIED,
            Waitlist.expires_at < now
        ).all()
        
        count = 0
        for entry in expired:
            entry.status = WaitlistStatus.EXPIRED
            count += 1
        
        if count > 0:
            db.commit()
            logger.info(f"Cleaned up {count} expired waitlist notifications")
        
        return count
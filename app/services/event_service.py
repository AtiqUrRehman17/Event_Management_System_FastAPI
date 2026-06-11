from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Tuple, Optional
from datetime import datetime
from app.models.event import Event
from app.schemas.event import EventCreate, EventUpdate, EventSearchParams
from app.core.exceptions import (
    EventNotFoundException,
    EventNotAvailableException,
    InvalidStatusTransitionException
)
from app.core.enums import EventStatus
from app.pagination import PaginationParams, paginate_query
from app.utils.datetime_utils import get_current_utc, make_aware, make_naive  # ✅ Proper imports
from app.services.audit_service import AuditService
from app.models.audit_log import AuditActionType, AuditActionCategory
import logging

logger = logging.getLogger(__name__)


class EventService:

    VALID_STATUS_TRANSITIONS = {
        EventStatus.UPCOMING: [
            EventStatus.CANCELLED,
            EventStatus.COMPLETED
        ],
        EventStatus.COMPLETED: [
            EventStatus.CANCELLED
        ],
        EventStatus.CANCELLED: []
    }

    @staticmethod
    def _enrich_event_with_category_info(event: Event, db: Session) -> Event:
        """
        Add category icon, color, and image to event response.
        """
        if event.category_id:
            from app.services.category_service import CategoryService
            try:
                category = CategoryService.get_category_by_id(db, event.category_id)
                event.category_name = category.name
                event.category_icon = category.icon
                event.category_color = category.color
                event.category_image_url = category.image_url
            except:
                event.category_name = None
                event.category_icon = None
                event.category_color = None
                event.category_image_url = None
        else:
            event.category_name = None
            event.category_icon = None
            event.category_color = None
            event.category_image_url = None
        return event

    @staticmethod
    def _validate_status_transition(
        current_status: EventStatus,
        new_status: EventStatus,
        event_date: datetime
    ) -> None:
        """Validate if a status transition is allowed."""
        if current_status == new_status:
            return

        allowed = EventService.VALID_STATUS_TRANSITIONS.get(current_status, [])

        if new_status not in allowed:
            raise InvalidStatusTransitionException(
                from_status=current_status.value,
                to_status=new_status.value
            )

        if (
            current_status == EventStatus.UPCOMING
            and new_status == EventStatus.COMPLETED
        ):
            now = get_current_utc()
            # ✅ Use the imported make_aware from datetime_utils
            event_date_aware = make_aware(event_date)

            if event_date_aware > now:
                raise InvalidStatusTransitionException(
                    from_status=current_status.value,
                    to_status=new_status.value
                )

    @staticmethod
    def create_event(db: Session, event_data: EventCreate, admin_id: int, request=None) -> Event:
        """Create a new event"""
        event = Event(
            title=event_data.title,
            description=event_data.description,
            location=event_data.location,
            event_date=event_data.event_date,
            total_seats=event_data.total_seats,
            available_seats=event_data.total_seats,
            price=event_data.price,
            category_id=event_data.category_id,
            image_url=event_data.image_url,
            created_by=admin_id
        )

        db.add(event)
        db.commit()
        db.refresh(event)

        # Enrich with category info
        event = EventService._enrich_event_with_category_info(event, db)
        
        # Audit log: Event created
        AuditService.log_action(
            db=db,
            user_id=admin_id,
            action=AuditActionType.EVENT_CREATE,
            category=AuditActionCategory.EVENT,
            request=request,
            entity_type="event",
            entity_id=event.id,
            new_value={
                "title": event.title,
                "location": event.location,
                "event_date": str(event.event_date),
                "total_seats": event.total_seats,
                "price": event.price
            }
        )

        return event

    @staticmethod
    def get_event_by_id(db: Session, event_id: int, include_deleted: bool = False) -> Event:
        """
        Get event by ID.
        By default, only returns non-deleted events.
        Set include_deleted=True to include soft-deleted events.
        """
        query = db.query(Event).filter(Event.id == event_id)
        if not include_deleted:
            query = query.filter(Event.is_deleted == False)
        
        event = query.first()
        if not event:
            raise EventNotFoundException()
        
        # Enrich with category info
        event = EventService._enrich_event_with_category_info(event, db)
        
        return event

    @staticmethod
    def get_all_events(
        db: Session,
        params: EventSearchParams,
        include_deleted: bool = False
    ) -> Tuple[List[Event], int]:
        """
        Get all events with search/filter/pagination and category enrichment.
        By default, excludes soft-deleted events.
        """
        query = db.query(Event)
        
        # Exclude soft-deleted events by default
        if not include_deleted:
            query = query.filter(Event.is_deleted == False)

        # Apply filters
        if params.search:
            search_term = f"%{params.search}%"
            query = query.filter(
                or_(
                    Event.title.ilike(search_term),
                    Event.description.ilike(search_term),
                    Event.location.ilike(search_term)
                )
            )

        if params.category_id:
            query = query.filter(Event.category_id == params.category_id)

        if params.location:
            query = query.filter(Event.location.ilike(f"%{params.location}%"))

        if params.status:
            query = query.filter(Event.status == params.status)
        else:
            # By default, show only upcoming events for normal users
            query = query.filter(Event.status == EventStatus.UPCOMING)

        if params.min_price is not None:
            query = query.filter(Event.price >= params.min_price)

        if params.max_price is not None:
            query = query.filter(Event.price <= params.max_price)

        if params.start_date:
            query = query.filter(Event.event_date >= params.start_date)

        if params.end_date:
            query = query.filter(Event.event_date <= params.end_date)

        # Order by event date
        query = query.order_by(Event.event_date)

        # Get total count before pagination
        total = query.count()

        # Apply pagination
        offset = (params.page - 1) * params.limit
        events = query.offset(offset).limit(params.limit).all()

        # Enrich each event with category info
        enriched_events = []
        for event in events:
            enriched_event = EventService._enrich_event_with_category_info(event, db)
            enriched_events.append(enriched_event)

        return enriched_events, total

    @staticmethod
    def update_event(
        db: Session,
        event_id: int,
        event_data: EventUpdate,
        admin_id: int,
        request=None
    ) -> Event:
        """Update event with status transition validation"""
        event = EventService.get_event_by_id(db, event_id)

        # Store old values for audit
        old_values = {
            "title": event.title,
            "description": event.description,
            "location": event.location,
            "event_date": str(event.event_date) if event.event_date else None,
            "total_seats": event.total_seats,
            "price": event.price,
            "status": event.status.value if event.status else None,
            "category_id": event.category_id
        }

        if event_data.status is not None:
            EventService._validate_status_transition(
                current_status=event.status,
                new_status=event_data.status,
                event_date=event.event_date
            )

        if event_data.title is not None:
            event.title = event_data.title

        if event_data.description is not None:
            event.description = event_data.description

        if event_data.location is not None:
            event.location = event_data.location

        if event_data.event_date is not None:
            # ✅ Use make_aware from datetime_utils
            new_date = make_aware(event_data.event_date)
            if new_date < get_current_utc():
                raise EventNotAvailableException("Event date cannot be in the past")
            event.event_date = event_data.event_date

        if event_data.total_seats is not None:
            booked_seats = event.total_seats - event.available_seats
            new_available = event_data.total_seats - booked_seats

            if new_available < 0:
                raise EventNotAvailableException(
                    f"Cannot reduce total seats below already booked seats "
                    f"({booked_seats} seats booked)"
                )
            event.total_seats = event_data.total_seats
            event.available_seats = new_available

        if event_data.available_seats is not None:
            if event_data.available_seats > event.total_seats:
                raise EventNotAvailableException(
                    "Available seats cannot exceed total seats"
                )
            event.available_seats = event_data.available_seats

        if event_data.price is not None:
            event.price = event_data.price

        if event_data.status is not None:
            event.status = event_data.status

        if event_data.category_id is not None:
            event.category_id = event_data.category_id

        if event_data.image_url is not None:
            event.image_url = event_data.image_url

        event.updated_at = get_current_utc()
        event.created_by = admin_id

        db.commit()
        db.refresh(event)

        # Audit log: Event updated
        new_values = {
            "title": event.title,
            "description": event.description,
            "location": event.location,
            "event_date": str(event.event_date) if event.event_date else None,
            "total_seats": event.total_seats,
            "price": event.price,
            "status": event.status.value if event.status else None,
            "category_id": event.category_id
        }
        
        AuditService.log_action(
            db=db,
            user_id=admin_id,
            action=AuditActionType.EVENT_UPDATE,
            category=AuditActionCategory.EVENT,
            request=request,
            entity_type="event",
            entity_id=event_id,
            old_value=old_values,
            new_value=new_values
        )

        # Enrich with category info
        event = EventService._enrich_event_with_category_info(event, db)

        return event

    @staticmethod
    def delete_event(
        db: Session, 
        event_id: int, 
        admin_id: int,
        request=None
    ) -> Event:
        """
        Soft delete an event.
        Instead of hard deleting, marks the event as deleted.
        Active bookings are preserved for historical records.
        """
        event = EventService.get_event_by_id(db, event_id, include_deleted=False)
        
        # Check if event has active bookings
        active_bookings_count = len([b for b in event.bookings if b.status.value == "active"])
        
        if active_bookings_count > 0:
            logger.warning(f"Event {event_id} has {active_bookings_count} active bookings. Proceeding with soft delete.")
        
        # Store old status for audit
        old_status = event.status.value if event.status else None
        
        # Soft delete the event
        event.is_deleted = True
        event.deleted_at = get_current_utc()
        event.deleted_by = admin_id
        event.updated_at = get_current_utc()
        
        # Optionally: Update event status to cancelled
        if event.status == EventStatus.UPCOMING:
            event.status = EventStatus.CANCELLED
        
        db.commit()
        db.refresh(event)
        
        # Audit log: Event deleted
        AuditService.log_action(
            db=db,
            user_id=admin_id,
            action=AuditActionType.EVENT_DELETE,
            category=AuditActionCategory.EVENT,
            request=request,
            entity_type="event",
            entity_id=event_id,
            details={
                "soft_delete": True,
                "event_title": event.title,
                "active_bookings_count": active_bookings_count,
                "event_status_before": old_status,
                "event_status_after": event.status.value if event.status else None
            }
        )
        
        logger.info(f"Event {event_id} ({event.title}) soft deleted by admin {admin_id}")
        
        return event

    @staticmethod
    def restore_event(
        db: Session, 
        event_id: int, 
        admin_id: int,
        request=None
    ) -> Event:
        """
        Restore a soft-deleted event.
        """
        event = EventService.get_event_by_id(db, event_id, include_deleted=True)
        
        if not event.is_deleted:
            raise EventNotAvailableException("Event is not deleted")
        
        # Restore the event
        event.is_deleted = False
        event.deleted_at = None
        event.deleted_by = None
        event.updated_at = get_current_utc()
        
        # Restore original status if it was changed and event is still in future
        if event.event_date > get_current_utc():
            event.status = EventStatus.UPCOMING
        
        db.commit()
        db.refresh(event)
        
        # Audit log: Event restored
        AuditService.log_action(
            db=db,
            user_id=admin_id,
            action=AuditActionType.EVENT_UPDATE,
            category=AuditActionCategory.EVENT,
            request=request,
            entity_type="event",
            entity_id=event_id,
            details={"restored": True, "event_title": event.title}
        )
        
        logger.info(f"Event {event_id} ({event.title}) restored by admin {admin_id}")
        
        # Enrich with category info
        event = EventService._enrich_event_with_category_info(event, db)
        
        return event

    @staticmethod
    def hard_delete_event(
        db: Session, 
        event_id: int, 
        admin_id: int,
        request=None
    ) -> None:
        """
        Permanent hard delete - USE WITH CAUTION!
        Only available for events with no bookings or after confirmation.
        """
        event = EventService.get_event_by_id(db, event_id, include_deleted=True)
        
        # Check if event has any bookings
        if event.bookings:
            raise EventNotAvailableException(
                f"Cannot hard delete event with {len(event.bookings)} bookings. "
                "Use soft delete instead."
            )
        
        # Audit log before deletion
        AuditService.log_action(
            db=db,
            user_id=admin_id,
            action=AuditActionType.EVENT_DELETE,
            category=AuditActionCategory.EVENT,
            request=request,
            entity_type="event",
            entity_id=event_id,
            details={"hard_delete": True, "event_title": event.title}
        )
        
        # Hard delete
        db.delete(event)
        db.commit()
        
        logger.warning(f"Event {event_id} ({event.title}) HARD DELETED by admin {admin_id}")

    @staticmethod
    def get_deleted_events(
        db: Session,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[Event], int]:
        """
        Get all soft-deleted events (Admin only).
        """
        query = db.query(Event).filter(Event.is_deleted == True)
        
        total = query.count()
        offset = (page - 1) * limit
        events = query.order_by(Event.deleted_at.desc()).offset(offset).limit(limit).all()
        
        # Enrich events with category info
        enriched_events = []
        for event in events:
            enriched_events.append(EventService._enrich_event_with_category_info(event, db))
        
        return enriched_events, total

    @staticmethod
    def update_event_status(db: Session) -> int:
        """Auto-update event statuses."""
        # ✅ Use get_current_utc from datetime_utils
        now = get_current_utc()

        try:
            # Find all upcoming events that are not deleted
            upcoming_events = db.query(Event).filter(
                Event.status == EventStatus.UPCOMING,
                Event.is_deleted == False
            ).all()

            count = 0
            for event in upcoming_events:
                # Convert event_date to naive for comparison
                event_date = event.event_date
                if hasattr(event_date, 'tzinfo') and event_date.tzinfo is not None:
                    event_date = event_date.replace(tzinfo=None)
                
                if event_date < now:
                    event.status = EventStatus.COMPLETED
                    event.updated_at = now
                    count += 1

            if count > 0:
                db.commit()
                logger.info(f"Auto-status update: {count} event(s) marked as COMPLETED")

            return count

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to auto-update event statuses: {str(e)}")
            raise

    @staticmethod
    def get_events_by_category(
        db: Session,
        category_id: int,
        limit: int = 10,
        upcoming_only: bool = True,
        include_deleted: bool = False
    ) -> List[Event]:
        """
        Get events by category ID with optional upcoming filter.
        """
        query = db.query(Event).filter(Event.category_id == category_id)
        
        if not include_deleted:
            query = query.filter(Event.is_deleted == False)
        
        if upcoming_only:
            query = query.filter(Event.status == EventStatus.UPCOMING)
            query = query.filter(Event.event_date >= get_current_utc())
        
        events = query.order_by(Event.event_date).limit(limit).all()
        
        # Enrich each event with category info
        enriched_events = []
        for event in events:
            enriched_event = EventService._enrich_event_with_category_info(event, db)
            enriched_events.append(enriched_event)
        
        return enriched_events

    @staticmethod
    def get_upcoming_events_by_category(
        db: Session,
        category_id: int,
        limit: int = 5
    ) -> List[Event]:
        """Get upcoming events for a specific category"""
        return EventService.get_events_by_category(db, category_id, limit, upcoming_only=True)

    @staticmethod
    def get_category_event_count(db: Session, category_id: int, include_deleted: bool = False) -> int:
        """
        Get total number of upcoming events in a category
        """
        query = db.query(Event).filter(
            Event.category_id == category_id,
            Event.status == EventStatus.UPCOMING
        )
        
        if not include_deleted:
            query = query.filter(Event.is_deleted == False)
        
        return query.count()
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
from app.utils.datetime_utils import get_current_utc
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
            # Compare naive datetimes directly
            if event_date > now:
                raise InvalidStatusTransitionException(
                    from_status=current_status.value,
                    to_status=new_status.value
                )

    @staticmethod
    def create_event(db: Session, event_data: EventCreate, admin_id: int) -> Event:
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

        event = EventService._enrich_event_with_category_info(event, db)

        return event

    @staticmethod
    def get_event_by_id(db: Session, event_id: int) -> Event:
        """Get event by ID with category icon and color"""
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise EventNotFoundException()
        
        event = EventService._enrich_event_with_category_info(event, db)
        
        return event

    @staticmethod
    def get_all_events(
        db: Session,
        params: EventSearchParams
    ) -> Tuple[List[Event], int]:
        """Get all events with search/filter/pagination and category enrichment"""
        query = db.query(Event)

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
            query = query.filter(Event.status == EventStatus.UPCOMING)

        if params.min_price is not None:
            query = query.filter(Event.price >= params.min_price)

        if params.max_price is not None:
            query = query.filter(Event.price <= params.max_price)

        if params.start_date:
            query = query.filter(Event.event_date >= params.start_date)

        if params.end_date:
            query = query.filter(Event.event_date <= params.end_date)

        query = query.order_by(Event.event_date)

        total = query.count()
        offset = (params.page - 1) * params.limit
        events = query.offset(offset).limit(params.limit).all()

        enriched_events = []
        for event in events:
            enriched_events.append(EventService._enrich_event_with_category_info(event, db))

        return enriched_events, total

    @staticmethod
    def update_event(
        db: Session,
        event_id: int,
        event_data: EventUpdate,
        admin_id: int
    ) -> Event:
        """Update event with status transition validation"""
        event = EventService.get_event_by_id(db, event_id)

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
            if event_data.event_date < get_current_utc():
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

        event = EventService._enrich_event_with_category_info(event, db)

        return event

    @staticmethod
    def delete_event(db: Session, event_id: int) -> None:
        """Delete event"""
        event = EventService.get_event_by_id(db, event_id)
        db.delete(event)
        db.commit()

    @staticmethod
    def update_event_status(db: Session) -> int:
        """Auto-update event statuses."""
        # Get current UTC time as naive datetime
        now = get_current_utc()

        try:
            # Find all upcoming events
            upcoming_events = db.query(Event).filter(
                Event.status == EventStatus.UPCOMING
            ).all()

            count = 0
            for event in upcoming_events:
                # event_date is stored as naive datetime in SQLite
                event_date = event.event_date
                
                # Simple naive comparison (no timezone involved)
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
        upcoming_only: bool = True
    ) -> List[Event]:
        """Get events by category ID with optional upcoming filter"""
        query = db.query(Event).filter(Event.category_id == category_id)
        
        if upcoming_only:
            query = query.filter(Event.status == EventStatus.UPCOMING)
            query = query.filter(Event.event_date >= get_current_utc())
        
        events = query.order_by(Event.event_date).limit(limit).all()
        
        enriched_events = []
        for event in events:
            enriched_events.append(EventService._enrich_event_with_category_info(event, db))
        
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
    def get_category_event_count(db: Session, category_id: int) -> int:
        """Get total number of events in a category"""
        return db.query(Event).filter(
            Event.category_id == category_id,
            Event.status == EventStatus.UPCOMING
        ).count()
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
import logging
from app.utils.datetime_utils import get_current_utc, make_aware


logger = logging.getLogger(__name__)


def make_aware(dt: datetime) -> datetime:
    """Convert naive datetime to UTC aware datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=get_current_utc())
    return dt


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
            event_date_aware = make_aware(event_date)

            if event_date_aware > now:
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

        return event

    @staticmethod
    def get_event_by_id(db: Session, event_id: int) -> Event:
        """Get event by ID"""
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise EventNotFoundException()
        return event

    @staticmethod
    def get_all_events(
        db: Session,
        params: EventSearchParams
    ) -> Tuple[List[Event], int]:
        """Get all events with search/filter/pagination"""
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

        # Use pagination module
        pagination = PaginationParams(page=params.page, limit=params.limit)
        events, total = paginate_query(query, pagination)

        return events, total

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

        db.commit()
        db.refresh(event)

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
        now = get_current_utc()
        
        try:
            # Find all upcoming events
            upcoming_events = db.query(Event).filter(
                Event.status == EventStatus.UPCOMING
            ).all()

            count = 0
            for event in upcoming_events:
                # Convert event_date to timezone-naive if needed
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
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Tuple, Optional
from datetime import datetime, timezone
from app.models.event import Event
from app.schemas.event import EventCreate, EventUpdate, EventSearchParams
from app.core.exceptions import (
    EventNotFoundException,
    EventNotAvailableException,
    InvalidStatusTransitionException
)
from app.core.enums import EventStatus
import logging

logger = logging.getLogger(__name__)


class EventService:

    # Valid status transitions map
    # Key = current status, Value = list of allowed next statuses
    VALID_STATUS_TRANSITIONS = {
        EventStatus.UPCOMING: [
            EventStatus.CANCELLED,   # Admin cancels upcoming event
            EventStatus.COMPLETED    # Only if event date has passed
        ],
        EventStatus.COMPLETED: [
            EventStatus.CANCELLED    # Admin can cancel a completed event
        ],
        EventStatus.CANCELLED: []    # Cannot transition out of cancelled
    }

    @staticmethod
    def _validate_status_transition(
        current_status: EventStatus,
        new_status: EventStatus,
        event_date: datetime
    ) -> None:
        """
        Validate if a status transition is allowed.
        Raises InvalidStatusTransitionException if not allowed.
        """
        # No change → nothing to validate
        if current_status == new_status:
            return

        allowed = EventService.VALID_STATUS_TRANSITIONS.get(current_status, [])

        if new_status not in allowed:
            raise InvalidStatusTransitionException(
                from_status=current_status.value,
                to_status=new_status.value
            )

        # Extra check: UPCOMING → COMPLETED only allowed if event date has passed
        if (
            current_status == EventStatus.UPCOMING
            and new_status == EventStatus.COMPLETED
        ):
            now = datetime.now(timezone.utc)
            # Make event_date timezone aware for comparison
            event_date_aware = event_date.replace(tzinfo=timezone.utc) \
                if event_date.tzinfo is None else event_date

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
        total = query.count()
        offset = (params.page - 1) * params.limit
        events = query.offset(offset).limit(params.limit).all()

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

        # Validate status transition FIRST before any other updates
        if event_data.status is not None:
            EventService._validate_status_transition(
                current_status=event.status,
                new_status=event_data.status,
                event_date=event.event_date
            )

        # Update title
        if event_data.title is not None:
            event.title = event_data.title

        # Update description
        if event_data.description is not None:
            event.description = event_data.description

        # Update location
        if event_data.location is not None:
            event.location = event_data.location

        # Update event date
        if event_data.event_date is not None:
            if event_data.event_date < datetime.now(timezone.utc):
                raise EventNotAvailableException("Event date cannot be in the past")
            event.event_date = event_data.event_date

        # Update total seats with protection
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

        # Update available seats manually
        if event_data.available_seats is not None:
            if event_data.available_seats > event.total_seats:
                raise EventNotAvailableException(
                    "Available seats cannot exceed total seats"
                )
            event.available_seats = event_data.available_seats

        # Update price
        if event_data.price is not None:
            event.price = event_data.price

        # Apply validated status
        if event_data.status is not None:
            event.status = event_data.status

        # Update category
        if event_data.category_id is not None:
            event.category_id = event_data.category_id

        # Update image
        if event_data.image_url is not None:
            event.image_url = event_data.image_url

        event.updated_at = datetime.now(timezone.utc)
        # DO NOT overwrite created_by

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
        """
        Auto-update event statuses based on current date/time.
        Marks all UPCOMING events whose date has passed as COMPLETED.
        Returns count of updated events.
        """
        now = datetime.now(timezone.utc)

        try:
            updated = db.query(Event).filter(
                Event.event_date < now,
                Event.status == EventStatus.UPCOMING
            ).all()

            count = len(updated)

            if count > 0:
                for event in updated:
                    event.status = EventStatus.COMPLETED
                    event.updated_at = now

                db.commit()
                logger.info(f"Auto-status update: {count} event(s) marked as COMPLETED")

            return count

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to auto-update event statuses: {str(e)}")
            raise
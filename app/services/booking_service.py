from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Tuple, Optional
from datetime import datetime, timezone
from app.models.booking import Booking
from app.models.event import Event
from app.schemas.booking import BookingCreate
from app.core.exceptions import (
    EventNotFoundException,
    EventNotAvailableException,
    InsufficientSeatsException,
    BookingNotFoundException,
    BookingNotOwnedException,
    BookingAlreadyCancelledException
)
from app.core.enums import EventStatus, BookingStatus
from app.pagination import PaginationParams, paginate_query
import logging

logger = logging.getLogger(__name__)


def make_aware(dt: datetime) -> datetime:
    """Convert naive datetime to UTC aware datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class BookingService:

    @staticmethod
    def create_booking(
        db: Session,
        user_id: int,
        booking_data: BookingCreate
    ) -> Booking:
        """Create a new booking"""
        event = db.query(Event).filter(Event.id == booking_data.event_id).first()
        if not event:
            raise EventNotFoundException()

        if event.status != EventStatus.UPCOMING:
            raise EventNotAvailableException(
                "Cannot book this event as it is not upcoming"
            )

        event_date = make_aware(event.event_date)
        if event_date < datetime.now(timezone.utc):
            raise EventNotAvailableException("Cannot book past events")

        if event.available_seats < booking_data.number_of_seats:
            raise InsufficientSeatsException(event.available_seats)

        total_price = event.price * booking_data.number_of_seats

        booking = Booking(
            user_id=user_id,
            event_id=booking_data.event_id,
            number_of_seats=booking_data.number_of_seats,
            total_price=total_price,
            status=BookingStatus.ACTIVE
        )

        event.available_seats -= booking_data.number_of_seats

        db.add(booking)
        db.commit()
        db.refresh(booking)

        return booking

    @staticmethod
    def get_booking_by_id(db: Session, booking_id: int) -> Booking:
        """Get booking by ID"""
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise BookingNotFoundException()
        return booking

    @staticmethod
    def get_user_bookings(
        db: Session,
        user_id: int,
        pagination: PaginationParams,
        status: Optional[BookingStatus] = None
    ) -> Tuple[List[Booking], int, float]:
        """
        Get all bookings for a specific user.
        total_spent always calculated from ALL active bookings.
        """
        base_query = db.query(Booking).filter(Booking.user_id == user_id)

        # Calculate total_spent independently
        total_spent_result = db.query(
            func.coalesce(func.sum(Booking.total_price), 0)
        ).filter(
            Booking.user_id == user_id,
            Booking.status == BookingStatus.ACTIVE
        ).scalar()

        total_spent = float(total_spent_result)

        # Apply status filter
        if status:
            base_query = base_query.filter(Booking.status == status)

        # Order before pagination
        base_query = base_query.order_by(Booking.created_at.desc())

        # Use pagination module
        bookings, total = paginate_query(base_query, pagination)

        return bookings, total, total_spent

    @staticmethod
    def get_all_bookings(
        db: Session,
        pagination: PaginationParams,
        status: Optional[BookingStatus] = None
    ) -> Tuple[List[Booking], int]:
        """Get all bookings (Admin only)"""
        query = db.query(Booking)

        if status:
            query = query.filter(Booking.status == status)

        # Order before pagination
        query = query.order_by(Booking.created_at.desc())

        # Use pagination module
        bookings, total = paginate_query(query, pagination)

        return bookings, total

    @staticmethod
    def cancel_booking(
        db: Session,
        booking_id: int,
        user_id: int,
        is_admin: bool = False
    ) -> Booking:
        """Cancel a booking"""
        booking = BookingService.get_booking_by_id(db, booking_id)

        if not is_admin and booking.user_id != user_id:
            raise BookingNotOwnedException()

        if booking.status == BookingStatus.CANCELLED:
            raise BookingAlreadyCancelledException()

        event = booking.event
        if event.status != EventStatus.UPCOMING:
            raise EventNotAvailableException(
                "Cannot cancel booking for completed or cancelled events"
            )

        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.now(timezone.utc)

        event.available_seats += booking.number_of_seats

        db.commit()
        db.refresh(booking)

        return booking

    @staticmethod
    def get_event_bookings(db: Session, event_id: int) -> List[Booking]:
        """Get all ACTIVE bookings for a specific event (Admin only)"""
        return db.query(Booking).filter(
            Booking.event_id == event_id,
            Booking.status == BookingStatus.ACTIVE
        ).all()

    @staticmethod
    def get_user_booking_summary(db: Session, user_id: int) -> dict:
        """Get booking summary using DB aggregation."""
        active_result = db.query(
            func.count(Booking.id).label("count"),
            func.coalesce(func.sum(Booking.total_price), 0).label("total_spent")
        ).filter(
            Booking.user_id == user_id,
            Booking.status == BookingStatus.ACTIVE
        ).first()

        cancelled_count = db.query(func.count(Booking.id)).filter(
            Booking.user_id == user_id,
            Booking.status == BookingStatus.CANCELLED
        ).scalar()

        return {
            "total_active_bookings": active_result.count if active_result else 0,
            "total_cancelled_bookings": cancelled_count or 0,
            "total_spent": float(active_result.total_spent) if active_result else 0.0
        }
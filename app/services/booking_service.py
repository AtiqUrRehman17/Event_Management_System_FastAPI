from sqlalchemy.orm import Session
from typing import List, Tuple, Optional
from datetime import datetime
from app.models.booking import Booking
from app.models.event import Event
from app.models.user import User
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


class BookingService:
    
    @staticmethod
    def create_booking(db: Session, user_id: int, booking_data: BookingCreate) -> Booking:
        """Create a new booking"""
        # Get event
        event = db.query(Event).filter(Event.id == booking_data.event_id).first()
        if not event:
            raise EventNotFoundException()
        
        # Check if event is available for booking
        if event.status != EventStatus.UPCOMING:
            raise EventNotAvailableException("Cannot book this event as it is not upcoming")
        
        if event.event_date < datetime.utcnow():
            raise EventNotAvailableException("Cannot book past events")
        
        # Check seat availability
        if event.available_seats < booking_data.number_of_seats:
            raise InsufficientSeatsException(event.available_seats)
        
        # Calculate total price
        total_price = event.price * booking_data.number_of_seats
        
        # Create booking
        booking = Booking(
            user_id=user_id,
            event_id=booking_data.event_id,
            number_of_seats=booking_data.number_of_seats,
            total_price=total_price,
            status=BookingStatus.ACTIVE
        )
        
        # Update available seats
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
        page: int = 1,
        limit: int = 10,
        status: Optional[BookingStatus] = None
    ) -> Tuple[List[Booking], int, float]:
        """Get all bookings for a specific user"""
        query = db.query(Booking).filter(Booking.user_id == user_id)
        
        if status:
            query = query.filter(Booking.status == status)
        
        # Get total count and total spent
        total = query.count()
        total_spent = sum([b.total_price for b in query.all() if b.status == BookingStatus.ACTIVE])
        
        # Apply pagination
        offset = (page - 1) * limit
        bookings = query.order_by(Booking.created_at.desc()).offset(offset).limit(limit).all()
        
        return bookings, total, total_spent
    
    @staticmethod
    def get_all_bookings(
        db: Session,
        page: int = 1,
        limit: int = 10,
        status: Optional[BookingStatus] = None
    ) -> Tuple[List[Booking], int]:
        """Get all bookings (Admin only)"""
        query = db.query(Booking)
        
        if status:
            query = query.filter(Booking.status == status)
        
        total = query.count()
        offset = (page - 1) * limit
        bookings = query.order_by(Booking.created_at.desc()).offset(offset).limit(limit).all()
        
        return bookings, total
    
    @staticmethod
    def cancel_booking(db: Session, booking_id: int, user_id: int, is_admin: bool = False) -> Booking:
        """Cancel a booking"""
        booking = BookingService.get_booking_by_id(db, booking_id)
        
        # Check if booking belongs to user (unless admin)
        if not is_admin and booking.user_id != user_id:
            raise BookingNotOwnedException()
        
        # Check if already cancelled
        if booking.status == BookingStatus.CANCELLED:
            raise BookingAlreadyCancelledException()
        
        # Check if event is still upcoming
        event = booking.event
        if event.status != EventStatus.UPCOMING:
            raise EventNotAvailableException("Cannot cancel booking for completed or cancelled events")
        
        # Update booking status
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.utcnow()
        
        # Return seats to event
        event.available_seats += booking.number_of_seats
        
        db.commit()
        db.refresh(booking)
        
        return booking
    
    @staticmethod
    def get_event_bookings(db: Session, event_id: int) -> List[Booking]:
        """Get all bookings for a specific event (Admin only)"""
        return db.query(Booking).filter(
            Booking.event_id == event_id,
            Booking.status == BookingStatus.ACTIVE
        ).all()
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db, get_current_user, get_current_admin
from app.models.user import User
from app.schemas.booking import BookingCreate
from app.services.booking_service import BookingService
from app.services.event_service import EventService
from app.utils.response import success_response, paginated_response
from app.core.enums import BookingStatus, EventStatus

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Book an event for current user
    """
    booking = BookingService.create_booking(db, current_user.id, booking_data)
    
    # Get event details
    event = EventService.get_event_by_id(db, booking.event_id)
    
    return success_response(
        data={
            "id": booking.id,
            "event_id": booking.event_id,
            "event_title": event.title,
            "event_date": event.event_date,
            "event_location": event.location,
            "number_of_seats": booking.number_of_seats,
            "total_price": booking.total_price,
            "status": booking.status,
            "booking_date": booking.booking_date,
            "created_at": booking.created_at,
            "updated_at": booking.updated_at
        },
        message="Booking created successfully",
        status_code=status.HTTP_201_CREATED
    )


@router.get("/me", response_model=dict)
async def get_my_bookings(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[BookingStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's bookings
    """
    bookings, total, total_spent = BookingService.get_user_bookings(
        db, current_user.id, page, limit, status
    )
    
    booking_data = []
    for booking in bookings:
        event = EventService.get_event_by_id(db, booking.event_id)
        booking_data.append({
            "id": booking.id,
            "event_id": booking.event_id,
            "event_title": event.title,
            "event_date": event.event_date,
            "event_location": event.location,
            "number_of_seats": booking.number_of_seats,
            "total_price": booking.total_price,
            "status": booking.status,
            "booking_date": booking.booking_date,
            "cancelled_at": booking.cancelled_at,
            "created_at": booking.created_at,
            "updated_at": booking.updated_at
        })
    
    return paginated_response(
        items=booking_data,
        total=total,
        page=page,
        limit=limit,
        message="Bookings retrieved successfully"
    ) | {"total_spent": total_spent}


@router.get("/", response_model=dict)
async def get_all_bookings(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[BookingStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get all bookings (Admin only)
    """
    bookings, total = BookingService.get_all_bookings(db, page, limit, status)
    
    booking_data = []
    for booking in bookings:
        event = EventService.get_event_by_id(db, booking.event_id)
        booking_data.append({
            "id": booking.id,
            "user_id": booking.user_id,
            "event_id": booking.event_id,
            "event_title": event.title,
            "event_date": event.event_date,
            "number_of_seats": booking.number_of_seats,
            "total_price": booking.total_price,
            "status": booking.status,
            "booking_date": booking.booking_date,
            "cancelled_at": booking.cancelled_at,
            "created_at": booking.created_at,
            "updated_at": booking.updated_at
        })
    
    return paginated_response(
        items=booking_data,
        total=total,
        page=page,
        limit=limit,
        message="All bookings retrieved successfully"
    )


@router.get("/events/{event_id}", response_model=dict)
async def get_event_bookings(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get all bookings for a specific event (Admin only)
    """
    bookings = BookingService.get_event_bookings(db, event_id)
    event = EventService.get_event_by_id(db, event_id)
    
    booking_data = []
    for booking in bookings:
        booking_data.append({
            "id": booking.id,
            "user_id": booking.user_id,
            "number_of_seats": booking.number_of_seats,
            "total_price": booking.total_price,
            "booking_date": booking.booking_date
        })
    
    return success_response(
        data={
            "event_id": event_id,
            "event_title": event.title,
            "total_bookings": len(booking_data),
            "total_seats_booked": sum(b["number_of_seats"] for b in booking_data),
            "bookings": booking_data
        },
        message="Event bookings retrieved successfully"
    )


@router.post("/{booking_id}/cancel", response_model=dict)
async def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a booking (User can cancel own, Admin can cancel any)
    """
    is_admin = current_user.role == "admin"
    booking = BookingService.cancel_booking(db, booking_id, current_user.id, is_admin)
    
    event = EventService.get_event_by_id(db, booking.event_id)
    
    return success_response(
        data={
            "id": booking.id,
            "event_id": booking.event_id,
            "event_title": event.title,
            "number_of_seats": booking.number_of_seats,
            "status": booking.status,
            "cancelled_at": booking.cancelled_at,
            "message": "Booking cancelled successfully"
        },
        message="Booking cancelled successfully"
    )


@router.get("/me/summary", response_model=dict)
async def get_my_booking_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary of current user's bookings
    """
    active_bookings, active_total, active_spent = BookingService.get_user_bookings(
        db, current_user.id, 1, 1000, BookingStatus.ACTIVE
    )
    
    cancelled_bookings, cancelled_total, cancelled_spent = BookingService.get_user_bookings(
        db, current_user.id, 1, 1000, BookingStatus.CANCELLED
    )
    
    return success_response(
        data={
            "total_active_bookings": active_total,
            "total_cancelled_bookings": cancelled_total,
            "total_spent": active_spent,
            "active_bookings_count": len(active_bookings),
            "cancelled_bookings_count": len(cancelled_bookings)
        },
        message="Booking summary retrieved successfully"
    )
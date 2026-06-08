from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import json
from app.dependencies import get_db, get_current_user, get_current_admin
from app.models.user import User
from app.schemas.booking import BookingCreate
from app.services.booking_service import BookingService
from app.services.event_service import EventService
from app.utils.response import success_response, paginated_response
from app.core.enums import BookingStatus, UserRole
from app.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Book an event for current user"""
    booking = BookingService.create_booking(db, current_user.id, booking_data)
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


@router.get("/me/summary", response_model=dict)
async def get_my_booking_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get summary of current user's bookings"""
    summary = BookingService.get_user_booking_summary(db, current_user.id)

    return success_response(
        data=summary,
        message="Booking summary retrieved successfully"
    )


@router.get("/me", response_model=dict)
async def get_my_bookings(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[BookingStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's bookings"""
    bookings, total, total_spent = BookingService.get_user_bookings(
        db, current_user.id, pagination, status
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

    # Build paginated response then add total_spent
    response = paginated_response(
        items=booking_data,
        total=total,
        page=pagination.page,
        limit=pagination.limit,
        message="Bookings retrieved successfully"
    )

    # Add total_spent to response body
    body = json.loads(response.body)
    body["total_spent"] = total_spent

    return JSONResponse(content=body, status_code=response.status_code)


@router.get("/", response_model=dict)
async def get_all_bookings(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[BookingStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Get all bookings (Admin only)"""
    bookings, total = BookingService.get_all_bookings(db, pagination, status)

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
        page=pagination.page,
        limit=pagination.limit,
        message="All bookings retrieved successfully"
    )


@router.get("/events/{event_id}", response_model=dict)
async def get_event_bookings(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Get all active bookings for a specific event (Admin only)"""
    bookings = BookingService.get_event_bookings(db, event_id)
    event = EventService.get_event_by_id(db, event_id)

    booking_data = [
        {
            "id": booking.id,
            "user_id": booking.user_id,
            "number_of_seats": booking.number_of_seats,
            "total_price": booking.total_price,
            "booking_date": booking.booking_date
        }
        for booking in bookings
    ]

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
    """Cancel a booking (Users cancel own, Admin cancels any)"""
    is_admin = current_user.role == UserRole.ADMIN
    booking = BookingService.cancel_booking(db, booking_id, current_user.id, is_admin)
    event = EventService.get_event_by_id(db, booking.event_id)

    return success_response(
        data={
            "id": booking.id,
            "event_id": booking.event_id,
            "event_title": event.title,
            "number_of_seats": booking.number_of_seats,
            "status": booking.status,
            "cancelled_at": booking.cancelled_at
        },
        message="Booking cancelled successfully"
    )
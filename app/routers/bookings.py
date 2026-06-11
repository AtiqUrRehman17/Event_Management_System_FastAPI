from fastapi import APIRouter, Depends, Query, status, Body,Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.dependencies import get_db, get_current_user, get_current_admin
from app.models.user import User
from app.models.event import Event
from app.models.waitlist import Waitlist, WaitlistStatus
from app.schemas.booking import (
    BookingCreate, BookingFilterParams, BookingSortField, BookingSortOrder,
    BookingListResponse, BookingDetailResponse, BookingSummaryResponse,
    BookingHistoryFilterParams
)
from app.services.booking_service import BookingService
from app.services.event_service import EventService
from app.services.waitlist_service import WaitlistService
from app.utils.response import success_response, paginated_response
from app.core.enums import BookingStatus, UserRole, EventStatus
from app.pagination import PaginationParams, get_pagination_params
from app.core.exceptions import EventNotFoundException
import requests
router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_data: BookingCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Book an event for current user.
    If the event is sold out, you will be offered to join the waitlist.
    """
    # Check event availability
    event = db.query(Event).filter(Event.id == booking_data.event_id).first()
    if not event:
        raise EventNotFoundException()
    
    # Check if event is upcoming
    if event.status != EventStatus.UPCOMING:
        return success_response(
            data={
                "event_id": booking_data.event_id,
                "event_title": event.title,
                "message": "This event is no longer available for booking."
            },
            message="Event not available for booking",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # If event is sold out, offer waitlist
    if event.available_seats == 0:
        # Check if user is already on waitlist
        existing = db.query(Waitlist).filter(
            Waitlist.user_id == current_user.id,
            Waitlist.event_id == booking_data.event_id,
            Waitlist.status.in_([WaitlistStatus.WAITING, WaitlistStatus.NOTIFIED])
        ).first()
        
        if existing:
            return success_response(
                data={
                    "waitlist_id": existing.id,
                    "position": existing.position,
                    "event_id": booking_data.event_id,
                    "event_title": event.title,
                    "message": "You are already on the waitlist for this event."
                },
                message="Already on waitlist",
                status_code=status.HTTP_200_OK
            )
        
        # Offer to join waitlist
        return success_response(
            data={
                "event_id": booking_data.event_id,
                "event_title": event.title,
                "available_seats": 0,
                "waitlist_enabled": True,
                "message": "This event is sold out. Would you like to join the waitlist?",
                "action": "POST /api/v1/waitlist/{event_id}/join"
            },
            message="Event sold out - Join waitlist available",
            status_code=status.HTTP_200_OK
        )
    
    # Check if user has enough seats
    if event.available_seats < booking_data.number_of_seats:
        return success_response(
            data={
                "event_id": booking_data.event_id,
                "event_title": event.title,
                "available_seats": event.available_seats,
                "requested_seats": booking_data.number_of_seats,
                "message": f"Only {event.available_seats} seats available."
            },
            message="Insufficient seats available",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Normal booking flow
    booking = BookingService.create_booking(db, current_user.id, booking_data, request)
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
    status: Optional[BookingStatus] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    event_name: Optional[str] = None,
    sort_by: BookingSortField = BookingSortField.BOOKING_DATE,
    sort_order: BookingSortOrder = BookingSortOrder.DESC,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's bookings with advanced filtering and sorting.
    
    Filters available:
    - status: Filter by booking status (active/cancelled)
    - start_date/end_date: Filter by booking date range (ISO format: YYYY-MM-DDTHH:MM:SS)
    - min_price/max_price: Filter by total price range
    - event_name: Search by event name
    - sort_by: Sort by booking_date, event_date, price, or seats
    - sort_order: asc or desc
    """
    # Parse date strings to datetime objects
    start_date_obj = None
    end_date_obj = None
    
    if start_date:
        try:
            start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    filters = BookingFilterParams(
        status=status,
        start_date=start_date_obj,
        end_date=end_date_obj,
        min_price=min_price,
        max_price=max_price,
        event_name=event_name,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit
    )
    
    bookings, total, total_spent = BookingService.get_user_bookings_filtered(
        db, current_user.id, filters
    )
    
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    
    return success_response(
        data={
            "bookings": bookings,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "total_spent": total_spent,
            "filters_applied": {
                "status": status.value if status else None,
                "start_date": start_date,
                "end_date": end_date,
                "min_price": min_price,
                "max_price": max_price,
                "event_name": event_name,
                "sort_by": sort_by.value,
                "sort_order": sort_order.value
            }
        },
        message="Bookings retrieved successfully"
    )


@router.get("/history", response_model=dict)
async def get_booking_history(
    type: Optional[str] = Query(None, description="Filter by type: upcoming, past, cancelled"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    event_name: Optional[str] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get dedicated booking history with categorized bookings.
    Shows upcoming, past, and cancelled bookings separately.
    
    Filters available:
    - type: Filter by booking type (upcoming, past, cancelled)
    - start_date/end_date: Filter by booking date range
    - min_price/max_price: Filter by total price range
    - event_name: Search by event name
    - category_id: Filter by event category
    """
    filters = BookingHistoryFilterParams(
        type=type,
        start_date=start_date,
        end_date=end_date,
        min_price=min_price,
        max_price=max_price,
        event_name=event_name,
        category_id=category_id
    )
    
    history = BookingService.get_booking_history(db, current_user.id, filters)
    
    return success_response(
        data=history,
        message="Booking history retrieved successfully"
    )


@router.get("/statistics", response_model=dict)
async def get_booking_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed booking statistics for user.
    Includes monthly spending, popular categories, and booking patterns.
    """
    stats = BookingService.get_booking_statistics(db, current_user.id)
    
    return success_response(
        data=stats,
        message="Booking statistics retrieved successfully"
    )


@router.get("/me/summary", response_model=dict)
async def get_my_booking_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get enhanced booking summary for dashboard"""
    summary = BookingService.get_booking_summary_stats(db, current_user.id)

    return success_response(
        data=summary,
        message="Booking summary retrieved successfully"
    )


@router.get("/me/timeline", response_model=dict)
async def get_my_booking_timeline(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get booking timeline with upcoming and past events"""
    timeline = BookingService.get_booking_timeline(db, current_user.id)

    return success_response(
        data=timeline,
        message="Booking timeline retrieved successfully"
    )


@router.get("/me/export/csv", response_class=StreamingResponse)
async def export_my_bookings_csv(
    status: Optional[BookingStatus] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    event_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export my bookings to CSV file.
    Applies the same filters as the GET /me endpoint.
    """
    # Parse date strings to datetime objects
    start_date_obj = None
    end_date_obj = None
    
    if start_date:
        try:
            start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    filters = BookingFilterParams(
        status=status,
        start_date=start_date_obj,
        end_date=end_date_obj,
        min_price=min_price,
        max_price=max_price,
        event_name=event_name
    )
    
    return BookingService.export_bookings_to_csv(db, current_user.id, filters)


@router.get("/me/export/pdf", response_class=Response)
async def export_my_bookings_pdf(
    status: Optional[BookingStatus] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    event_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export my bookings to PDF file.
    Applies the same filters as the GET /me endpoint.
    """
    # Parse date strings to datetime objects
    start_date_obj = None
    end_date_obj = None
    
    if start_date:
        try:
            start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    filters = BookingFilterParams(
        status=status,
        start_date=start_date_obj,
        end_date=end_date_obj,
        min_price=min_price,
        max_price=max_price,
        event_name=event_name
    )
    
    return BookingService.export_bookings_to_pdf(db, current_user.id, filters)


@router.get("/{booking_id}", response_model=dict)
async def get_booking_detail(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed booking information with event details"""
    booking = BookingService.get_booking_by_id(db, booking_id)
    
    # Check if user owns this booking or is admin
    if booking.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        from app.core.exceptions import PermissionDeniedException
        raise PermissionDeniedException()
    
    enriched_booking = BookingService._enrich_booking_with_details(booking, db)
    
    return success_response(
        data=enriched_booking,
        message="Booking details retrieved successfully"
    )


@router.post("/{booking_id}/cancel", response_model=dict)
async def cancel_booking(
    booking_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a booking.
    - Users can cancel their own active bookings
    - Admins can cancel any booking
    - When a booking is cancelled, the next person on the waitlist will be notified
    """
    is_admin = current_user.role == UserRole.ADMIN
    booking = BookingService.cancel_booking(db, booking_id, current_user.id, is_admin, request)
    event = EventService.get_event_by_id(db, booking.event_id)

    return success_response(
        data={
            "id": booking.id,
            "event_id": booking.event_id,
            "event_title": event.title,
            "number_of_seats": booking.number_of_seats,
            "status": booking.status,
            "cancelled_at": booking.cancelled_at,
            "message": "Booking cancelled successfully. If there is a waitlist, the next person has been notified."
        },
        message="Booking cancelled successfully"
    )


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
            "user_name": f"{booking.user.first_name} {booking.user.last_name}",
            "user_email": booking.user.email,
            "event_id": booking.event_id,
            "event_title": event.title,
            "event_date": event.event_date,
            "number_of_seats": booking.number_of_seats,
            "total_price": booking.total_price,
            "status": booking.status,
            "booking_date": booking.booking_date,
            "cancelled_at": booking.cancelled_at,
            "created_at": booking.created_at,
            "updated_at": booking.updated_at,
            "payment_status": booking.payment_status,
            "invoice_number": booking.invoice_number
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
            "user_name": f"{booking.user.first_name} {booking.user.last_name}",
            "user_email": booking.user.email,
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
            "total_revenue": sum(b["total_price"] for b in booking_data),
            "bookings": booking_data
        },
        message="Event bookings retrieved successfully"
    )
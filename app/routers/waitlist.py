from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db, get_current_user, get_current_admin
from app.models.user import User
from app.models.event import Event
from app.core.enums import EventStatus
from app.services.waitlist_service import WaitlistService
from app.services.booking_service import BookingService
from app.schemas.waitlist import (
    JoinWaitlistRequest, WaitlistResponse, WaitlistPositionResponse,
    WaitlistSummaryResponse, WaitlistAdminResponse
)
from app.utils.response import success_response
from app.core.exceptions import EventNotFoundException
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])


@router.post("/{event_id}/join", response_model=dict)
async def join_waitlist(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Join the waitlist for a sold-out event.
    You'll be notified when a spot becomes available.
    """
    waitlist_entry = WaitlistService.join_waitlist(db, current_user.id, event_id)
    
    # Get event details
    event = db.query(Event).filter(Event.id == event_id).first()
    
    return success_response(
        data={
            "event_id": event_id,
            "event_title": event.title if event else "Unknown",
            "position": waitlist_entry.position,
            "status": waitlist_entry.status.value,
            "message": f"You have been added to the waitlist at position {waitlist_entry.position}. You will be notified when a spot becomes available."
        },
        message="Successfully joined waitlist",
        status_code=status.HTTP_201_CREATED
    )


@router.get("/{event_id}/position", response_model=dict)
async def get_waitlist_position(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check your current position in the waitlist.
    """
    position_info = WaitlistService.get_user_position(db, current_user.id, event_id)
    
    return success_response(
        data=position_info,
        message="Waitlist position retrieved successfully"
    )


@router.delete("/{event_id}/leave", response_model=dict)
async def leave_waitlist(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Leave the waitlist for an event.
    """
    result = WaitlistService.leave_waitlist(db, current_user.id, event_id)
    
    return success_response(
        data=result,
        message="Successfully left waitlist"
    )


@router.post("/{event_id}/confirm", response_model=dict)
async def confirm_spot(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Confirm that you want the available spot (after receiving notification).
    """
    result = WaitlistService.confirm_spot(db, current_user.id, event_id)
    
    return success_response(
        data=result,
        message="Spot confirmed! You can now book your ticket."
    )


@router.get("/{event_id}/summary", response_model=dict)
async def get_waitlist_summary(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get waitlist summary for an event.
    """
    user_id = current_user.id if current_user else None
    summary = WaitlistService.get_event_waitlist_summary(db, event_id, user_id)
    
    return success_response(
        data=summary,
        message="Waitlist summary retrieved successfully"
    )


@router.get("/admin/{event_id}", response_model=dict)
async def get_waitlist_admin(
    event_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Admin: View all waitlist entries for an event.
    """
    entries, total = WaitlistService.get_event_waitlist_admin(db, event_id, page, limit)
    
    # Enrich entries with user names
    enriched_entries = []
    for entry in entries:
        enriched_entries.append({
            "id": entry.id,
            "user_id": entry.user_id,
            "user_name": f"{entry.user.first_name} {entry.user.last_name}",
            "user_email": entry.user.email,
            "position": entry.position,
            "status": entry.status.value,
            "joined_at": entry.joined_at,
            "notified_at": entry.notified_at,
            "expires_at": entry.expires_at
        })
    
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    
    return success_response(
        data={
            "event_id": event_id,
            "entries": enriched_entries,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        },
        message="Waitlist entries retrieved successfully"
    )
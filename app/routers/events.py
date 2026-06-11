from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.dependencies import get_db, get_current_user, get_current_admin, get_current_user_optional
from app.models.user import User
from app.schemas.event import EventCreate, EventUpdate, EventSearchParams
from app.services.event_service import EventService
from app.services.category_service import CategoryService
from app.utils.response import success_response, paginated_response
from app.core.enums import EventStatus

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Create a new event (Admin only)"""
    event = EventService.create_event(db, event_data, current_user.id, request)

    category_name = None
    if event.category_id:
        category = CategoryService.get_category_by_id(db, event.category_id)
        category_name = category.name

    return success_response(
        data={
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "location": event.location,
            "event_date": event.event_date,
            "total_seats": event.total_seats,
            "available_seats": event.available_seats,
            "price": event.price,
            "status": event.status,
            "category_id": event.category_id,
            "category_name": category_name,
            "image_url": event.image_url,
            "created_at": event.created_at,
            "updated_at": event.updated_at
        },
        message="Event created successfully",
        status_code=status.HTTP_201_CREATED
    )


@router.get("/", response_model=dict)
async def get_all_events(
    search: Optional[str] = Query(None, description="Search in title, description, location"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    location: Optional[str] = Query(None, description="Filter by location"),
    status: Optional[EventStatus] = Query(None, description="Filter by status"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    include_deleted: bool = Query(False, description="Include soft-deleted events (Admin only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Get all events with search/filter/pagination (Public access).
    Soft-deleted events are hidden by default. Admins can see them with include_deleted=true.
    """
    # Only admins can see deleted events
    show_deleted = include_deleted and current_user and current_user.role == "admin"
    
    start_date_obj = None
    end_date_obj = None

    if start_date:
        start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    if end_date:
        end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

    params = EventSearchParams(
        search=search,
        category_id=category_id,
        location=location,
        status=status,
        min_price=min_price,
        max_price=max_price,
        start_date=start_date_obj,
        end_date=end_date_obj,
        page=page,
        limit=limit
    )

    events, total = EventService.get_all_events(db, params, include_deleted=show_deleted)

    event_data = []
    for event in events:
        category_name = None
        if event.category_id:
            category = CategoryService.get_category_by_id(db, event.category_id)
            category_name = category.name

        event_data.append({
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "location": event.location,
            "event_date": event.event_date,
            "total_seats": event.total_seats,
            "available_seats": event.available_seats,
            "price": event.price,
            "status": event.status,
            "is_deleted": event.is_deleted if hasattr(event, 'is_deleted') else False,
            "category_id": event.category_id,
            "category_name": category_name,
            "image_url": event.image_url,
            "created_at": event.created_at,
            "updated_at": event.updated_at
        })

    return paginated_response(
        items=event_data,
        total=total,
        page=page,
        limit=limit,
        message="Events retrieved successfully"
    )


@router.get("/deleted", response_model=dict)
async def get_deleted_events(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get all soft-deleted events (Admin only).
    """
    events, total = EventService.get_deleted_events(db, page, limit)

    event_data = []
    for event in events:
        category_name = None
        if event.category_id:
            category = CategoryService.get_category_by_id(db, event.category_id)
            category_name = category.name
        
        event_data.append({
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "location": event.location,
            "event_date": event.event_date,
            "total_seats": event.total_seats,
            "available_seats": event.available_seats,
            "price": event.price,
            "status": event.status,
            "deleted_at": event.deleted_at,
            "deleted_by": event.deleted_by,
            "category_id": event.category_id,
            "category_name": category_name,
            "image_url": event.image_url,
            "created_at": event.created_at,
            "updated_at": event.updated_at
        })

    total_pages = (total + limit - 1) // limit if total > 0 else 0

    return success_response(
        data={
            "events": event_data,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        },
        message="Deleted events retrieved successfully"
    )


@router.get("/{event_id}", response_model=dict)
async def get_event(
    event_id: int,
    include_deleted: bool = Query(False, description="Include if event is deleted (Admin only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Get event by ID (Public access).
    Soft-deleted events are hidden by default. Admins can see them with include_deleted=true.
    """
    # Only admins can see deleted events
    show_deleted = include_deleted and current_user and current_user.role == "admin"
    
    event = EventService.get_event_by_id(db, event_id, include_deleted=show_deleted)

    category_name = None
    if event.category_id:
        category = CategoryService.get_category_by_id(db, event.category_id)
        category_name = category.name

    response_data = {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "location": event.location,
        "event_date": event.event_date,
        "total_seats": event.total_seats,
        "available_seats": event.available_seats,
        "price": event.price,
        "status": event.status,
        "category_id": event.category_id,
        "category_name": category_name,
        "image_url": event.image_url,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
        "created_by": event.created_by
    }
    
    # Include deletion info for admins
    if current_user and current_user.role == "admin" and hasattr(event, 'is_deleted'):
        response_data["is_deleted"] = event.is_deleted
        if event.is_deleted:
            response_data["deleted_at"] = event.deleted_at
            response_data["deleted_by"] = event.deleted_by

    return success_response(
        data=response_data,
        message="Event retrieved successfully"
    )


@router.put("/{event_id}", response_model=dict)
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Update event (Admin only)"""
    event = EventService.update_event(db, event_id, event_data, current_user.id, request)

    category_name = None
    if event.category_id:
        category = CategoryService.get_category_by_id(db, event.category_id)
        category_name = category.name

    return success_response(
        data={
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "location": event.location,
            "event_date": event.event_date,
            "total_seats": event.total_seats,
            "available_seats": event.available_seats,
            "price": event.price,
            "status": event.status,
            "category_id": event.category_id,
            "category_name": category_name,
            "image_url": event.image_url,
            "created_at": event.created_at,
            "updated_at": event.updated_at
        },
        message="Event updated successfully"
    )


@router.delete("/{event_id}", response_model=dict)
async def delete_event(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Soft delete an event (Admin only).
    The event is marked as deleted but remains in the database.
    Historical booking data is preserved.
    """
    event = EventService.delete_event(db, event_id, current_user.id, request)
    
    return success_response(
        data={
            "event_id": event.id,
            "title": event.title,
            "is_deleted": event.is_deleted,
            "deleted_at": event.deleted_at,
            "message": "Event has been soft deleted. It can be restored if needed."
        },
        message="Event deleted successfully"
    )


@router.post("/{event_id}/restore", response_model=dict)
async def restore_event(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Restore a soft-deleted event (Admin only).
    """
    event = EventService.restore_event(db, event_id, current_user.id, request)
    
    category_name = None
    if event.category_id:
        category = CategoryService.get_category_by_id(db, event.category_id)
        category_name = category.name
    
    return success_response(
        data={
            "event_id": event.id,
            "title": event.title,
            "is_deleted": event.is_deleted,
            "category_name": category_name,
            "event_date": event.event_date,
            "message": "Event has been restored and is now visible to users."
        },
        message="Event restored successfully"
    )


@router.delete("/{event_id}/permanent", response_model=dict)
async def permanent_delete_event(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Permanently hard delete an event (Admin only - USE WITH CAUTION!).
    Only works for events with NO bookings.
    """
    EventService.hard_delete_event(db, event_id, current_user.id, request)
    
    return success_response(
        data={
            "event_id": event_id,
            "message": "Event has been permanently deleted from the database."
        },
        message="Event permanently deleted"
    )
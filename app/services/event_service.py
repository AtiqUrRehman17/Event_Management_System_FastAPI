from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Tuple, Optional
from datetime import datetime
from app.models.event import Event
from app.models.category import Category
from app.schemas.event import EventCreate, EventUpdate, EventSearchParams
from app.core.exceptions import EventNotFoundException, EventNotAvailableException
from app.core.enums import EventStatus


class EventService:
    
    @staticmethod
    def create_event(db: Session, event_data: EventCreate, admin_id: int) -> Event:
        """Create a new event"""
        event = Event(
            title=event_data.title,
            description=event_data.description,
            location=event_data.location,
            event_date=event_data.event_date,
            total_seats=event_data.total_seats,
            available_seats=event_data.total_seats,  # Initially available = total
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
        
        # Apply filters
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
            # By default, show only upcoming events for normal users
            query = query.filter(Event.status == EventStatus.UPCOMING)
        
        if params.min_price is not None:
            query = query.filter(Event.price >= params.min_price)
        
        if params.max_price is not None:
            query = query.filter(Event.price <= params.max_price)
        
        if params.start_date:
            query = query.filter(Event.event_date >= params.start_date)
        
        if params.end_date:
            query = query.filter(Event.event_date <= params.end_date)
        
        # Order by event date
        query = query.order_by(Event.event_date)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (params.page - 1) * params.limit
        events = query.offset(offset).limit(params.limit).all()
        
        return events, total
    
    @staticmethod
    def update_event(db: Session, event_id: int, event_data: EventUpdate, admin_id: int) -> Event:
        """Update event"""
        event = EventService.get_event_by_id(db, event_id)
        
        # Update fields
        if event_data.title is not None:
            event.title = event_data.title
        if event_data.description is not None:
            event.description = event_data.description
        if event_data.location is not None:
            event.location = event_data.location
        if event_data.event_date is not None:
            if event_data.event_date < datetime.utcnow():
                raise EventNotAvailableException("Event date cannot be in the past")
            event.event_date = event_data.event_date
        if event_data.total_seats is not None:
            # Adjust available seats if total seats change
            seats_diff = event_data.total_seats - event.total_seats
            event.total_seats = event_data.total_seats
            event.available_seats += seats_diff
        if event_data.available_seats is not None:
            event.available_seats = event_data.available_seats
        if event_data.price is not None:
            event.price = event_data.price
        if event_data.status is not None:
            event.status = event_data.status
        if event_data.category_id is not None:
            event.category_id = event_data.category_id
        if event_data.image_url is not None:
            event.image_url = event_data.image_url
        
        event.updated_at = datetime.utcnow()
        event.created_by = admin_id
        
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
    def update_event_status(db: Session) -> None:
        """Auto-update event statuses based on date"""
        now = datetime.utcnow()
        
        # Update completed events
        db.query(Event).filter(
            Event.event_date < now,
            Event.status == EventStatus.UPCOMING
        ).update({Event.status: EventStatus.COMPLETED})
        
        db.commit()
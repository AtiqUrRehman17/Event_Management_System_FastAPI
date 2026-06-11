from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import Optional, List
from app.core.enums import EventStatus


class EventBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    location: str = Field(..., min_length=3, max_length=255)
    event_date: datetime
    total_seats: int = Field(..., gt=0)
    price: float = Field(..., ge=0)
    category_id: Optional[int] = None
    image_url: Optional[str] = Field(None, max_length=500)


class EventCreate(EventBase):
    @field_validator('event_date')
    @classmethod
    def validate_event_date(cls, v: datetime) -> datetime:
        """Validate that event date is not in the past"""
        # Get current UTC time as naive datetime for comparison
        now = datetime.utcnow()
        
        # Convert input to naive if it has timezone
        if v.tzinfo is not None:
            v = v.replace(tzinfo=None)
        
        if v < now:
            raise ValueError('Event date cannot be in the past')
        return v
    
    @field_validator('total_seats')
    @classmethod
    def validate_seats(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('Total seats must be greater than 0')
        return v


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = Field(None, min_length=3, max_length=255)
    event_date: Optional[datetime] = None
    total_seats: Optional[int] = Field(None, gt=0)
    available_seats: Optional[int] = Field(None, ge=0)
    price: Optional[float] = Field(None, ge=0)
    status: Optional[EventStatus] = None
    category_id: Optional[int] = None
    image_url: Optional[str] = Field(None, max_length=500)
    
    @field_validator('event_date')
    @classmethod
    def validate_event_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            now = datetime.utcnow()
            if v.tzinfo is not None:
                v = v.replace(tzinfo=None)
            if v < now:
                raise ValueError('Event date cannot be in the past')
        return v


class EventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    location: str
    event_date: datetime
    total_seats: int
    available_seats: int
    price: float
    status: EventStatus
    image_url: Optional[str]
    category_id: Optional[int]
    category_name: Optional[str] = None
    category_icon: Optional[str] = None
    category_color: Optional[str] = None
    category_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int]
    
    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    events: List[EventResponse]
    total: int
    page: int
    limit: int


class EventSearchParams(BaseModel):
    search: Optional[str] = Field(None, description="Search in title and description")
    category_id: Optional[int] = None
    location: Optional[str] = None
    status: Optional[EventStatus] = None
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=100)
    
    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v is not None:
            start_date = info.data.get('start_date')
            if start_date is not None:
                # Convert to naive for comparison
                v_naive = v.replace(tzinfo=None) if v.tzinfo is not None else v
                start_naive = start_date.replace(tzinfo=None) if start_date.tzinfo is not None else start_date
                if v_naive < start_naive:
                    raise ValueError('End date must be after start date')
        return v
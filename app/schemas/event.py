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
    def validate_event_date(cls, v):
        if v < datetime.now(timezone.utc):
            raise ValueError('Event date cannot be in the past')
        return v
    
    @field_validator('total_seats')
    def validate_seats(cls, v):
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
    def validate_event_date(cls, v):
        if v and v < datetime.now(timezone.utc):
            raise ValueError('Event date cannot be in the past')
        return v
    
    @field_validator('available_seats')
    def validate_available_seats(cls, v, values):
        if v is not None and 'total_seats' in values and values['total_seats'] is not None:
            if v > values['total_seats']:
                raise ValueError('Available seats cannot exceed total seats')
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
    def validate_dates(cls, v, values):
        if v and 'start_date' in values and values['start_date']:
            if v < values['start_date']:
                raise ValueError('End date must be after start date')
        return v
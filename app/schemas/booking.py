from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import Optional, List
from app.core.enums import BookingStatus


class BookingBase(BaseModel):
    event_id: int
    number_of_seats: int = Field(..., gt=0)


class BookingCreate(BookingBase):
    @field_validator('number_of_seats')
    def validate_seats(cls, v):
        if v <= 0:
            raise ValueError('Number of seats must be greater than 0')
        return v


class BookingResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    event_title: Optional[str] = None
    event_date: Optional[datetime] = None
    event_location: Optional[str] = None
    number_of_seats: int
    total_price: float
    status: BookingStatus
    booking_date: datetime
    cancelled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BookingListResponse(BaseModel):
    bookings: List[BookingResponse]
    total: int
    page: int
    limit: int


class BookingCancelResponse(BaseModel):
    id: int
    event_id: int
    event_title: str
    number_of_seats: int
    status: BookingStatus
    cancelled_at: datetime
    message: str = "Booking cancelled successfully"


class UserBookingsResponse(BaseModel):
    bookings: List[BookingResponse]
    total: int
    total_spent: float
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum
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


class BookingSortField(str, Enum):
    BOOKING_DATE = "booking_date"
    EVENT_DATE = "event_date"
    PRICE = "price"
    SEATS = "number_of_seats"


class BookingSortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class BookingFilterParams(BaseModel):
    """Filter parameters for booking history"""
    status: Optional[BookingStatus] = Field(None, description="Filter by booking status")
    start_date: Optional[datetime] = Field(None, description="Filter bookings from this date")
    end_date: Optional[datetime] = Field(None, description="Filter bookings until this date")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum total price")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum total price")
    event_name: Optional[str] = Field(None, description="Search by event name")
    sort_by: BookingSortField = Field(BookingSortField.BOOKING_DATE, description="Sort field")
    sort_order: BookingSortOrder = Field(BookingSortOrder.DESC, description="Sort order")
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(10, ge=1, le=100, description="Items per page")
    
    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v: Optional[datetime], info: ValidationInfo) -> Optional[datetime]:
        """Validate that end_date is after start_date"""
        if v is not None:
            start_date = info.data.get('start_date')
            if start_date is not None and v < start_date:
                raise ValueError('End date must be after start date')
        return v


class BookingResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    event_title: Optional[str] = None
    event_description: Optional[str] = None
    event_location: Optional[str] = None
    event_date: Optional[datetime] = None
    event_image_url: Optional[str] = None
    number_of_seats: int
    total_price: float
    status: BookingStatus
    booking_date: datetime
    cancelled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BookingDetailResponse(BookingResponse):
    """Detailed booking response with additional event information"""
    event_category_name: Optional[str] = None
    event_category_icon: Optional[str] = None
    event_category_color: Optional[str] = None
    days_until_event: Optional[int] = None
    is_upcoming: bool = False
    can_cancel: bool = False
    cancellation_deadline: Optional[datetime] = None


class BookingListResponse(BaseModel):
    bookings: List[BookingResponse]
    total: int
    page: int
    limit: int
    total_pages: int
    total_spent: float
    filters_applied: dict


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


class BookingSummaryResponse(BaseModel):
    """Booking summary for dashboard"""
    total_bookings: int
    active_bookings: int
    cancelled_bookings: int
    total_spent: float
    upcoming_events_count: int
    past_events_count: int
    average_booking_value: float
    most_active_month: Optional[str] = None
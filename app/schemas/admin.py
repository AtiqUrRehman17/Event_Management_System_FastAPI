from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum


class PeriodType(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    CUSTOM = "custom"


class RevenuePeriod(str, Enum):
    TODAY = "today"
    THIS_WEEK = "this_week"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_YEAR = "this_year"
    ALL_TIME = "all_time"


class DashboardStatsResponse(BaseModel):
    """Main dashboard statistics response"""
    total_users: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    active_users: int
    total_events: int
    upcoming_events: int
    completed_events: int
    cancelled_events: int
    total_bookings: int
    active_bookings: int
    cancelled_bookings: int
    revenue_today: float
    revenue_this_week: float
    revenue_this_month: float
    revenue_this_year: float
    total_revenue: float
    average_booking_value: float
    conversion_rate: float
    popular_categories: List[Dict[str, Any]]
    recent_bookings: List[Dict[str, Any]]
    top_events: List[Dict[str, Any]]
    recent_users: List[Dict[str, Any]]


class UserActivityResponse(BaseModel):
    """User activity statistics"""
    total_users: int
    active_users_today: int
    active_users_this_week: int
    active_users_this_month: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    users_by_role: Dict[str, int]
    users_by_join_date: List[Dict[str, Any]]
    top_active_users: List[Dict[str, Any]]
    login_frequency: Dict[str, int]


class EventAnalyticsResponse(BaseModel):
    """Event performance analytics"""
    total_events: int
    events_by_status: Dict[str, int]
    events_by_category: List[Dict[str, Any]]
    upcoming_events_count: int
    average_price_per_event: float
    total_capacity: int
    average_fill_rate: float
    top_performing_events: List[Dict[str, Any]]
    worst_performing_events: List[Dict[str, Any]]
    events_by_month: List[Dict[str, Any]]


class BookingReportResponse(BaseModel):
    """Booking report response"""
    total_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    bookings_by_status: Dict[str, int]
    bookings_by_category: List[Dict[str, Any]]
    bookings_by_event: List[Dict[str, Any]]
    recent_bookings: List[Dict[str, Any]]
    peak_booking_hours: List[Dict[str, Any]]
    average_booking_value: float


class RevenueReportResponse(BaseModel):
    """Revenue report response"""
    total_revenue: float
    revenue_today: float
    revenue_this_week: float
    revenue_this_month: float
    revenue_this_year: float
    revenue_by_category: List[Dict[str, Any]]
    revenue_by_event: List[Dict[str, Any]]
    revenue_by_month: List[Dict[str, Any]]
    revenue_by_day: List[Dict[str, Any]]
    projected_revenue: float


class DateRangeRequest(BaseModel):
    """Date range for reports"""
    start_date: date
    end_date: date
    period: Optional[PeriodType] = PeriodType.DAY


class ExportFormat(str, Enum):
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "excel"
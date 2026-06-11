from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from app.dependencies import get_db, get_current_admin
from app.models.user import User
from app.schemas.admin import (
    DashboardStatsResponse, UserActivityResponse, EventAnalyticsResponse,
    BookingReportResponse, RevenueReportResponse, DateRangeRequest, ExportFormat
)
from app.services.admin_service import AdminService
from app.utils.response import success_response

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard/stats", response_model=dict)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get main dashboard statistics.
    Requires admin privileges.
    """
    stats = AdminService.get_dashboard_stats(db)
    
    return success_response(
        data=stats,
        message="Dashboard statistics retrieved successfully"
    )


@router.get("/users/activity", response_model=dict)
async def get_user_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get user activity statistics including active users and login frequency.
    Requires admin privileges.
    """
    activity = AdminService.get_user_activity(db)
    
    return success_response(
        data=activity,
        message="User activity statistics retrieved successfully"
    )


@router.get("/events/analytics", response_model=dict)
async def get_event_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get event performance analytics including fill rates and top events.
    Requires admin privileges.
    """
    analytics = AdminService.get_event_analytics(db)
    
    return success_response(
        data=analytics,
        message="Event analytics retrieved successfully"
    )


@router.get("/reports/bookings", response_model=dict)
async def get_booking_report(
    start_date: Optional[date] = Query(None, description="Start date for report (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for report (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get booking report with optional date range.
    Requires admin privileges.
    """
    report = AdminService.get_booking_report(db, start_date, end_date)
    
    return success_response(
        data=report,
        message="Booking report retrieved successfully"
    )


@router.get("/reports/revenue", response_model=dict)
async def get_revenue_report(
    period: str = Query("all_time", description="Report period: today, this_week, this_month, this_year, all_time"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get revenue report for different time periods.
    Requires admin privileges.
    """
    report = AdminService.get_revenue_report(db, period)
    
    return success_response(
        data=report,
        message="Revenue report retrieved successfully"
    )


@router.get("/reports/bookings/export/csv")
async def export_bookings_csv(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Export booking report as CSV file.
    Requires admin privileges.
    """
    return AdminService.export_bookings_report_csv(db, start_date, end_date)


@router.get("/reports/revenue/export/csv")
async def export_revenue_csv(
    period: str = Query("all_time", description="Report period"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Export revenue report as CSV file.
    Requires admin privileges.
    """
    return AdminService.export_revenue_report_csv(db, period)
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract, desc
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from app.models.user import User
from app.models.event import Event
from app.models.booking import Booking
from app.models.category import Category
from app.core.enums import UserRole, EventStatus, BookingStatus
from app.utils.datetime_utils import get_current_utc
import logging
import csv
import io
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


class AdminService:
    
    @staticmethod
    def get_dashboard_stats(db: Session) -> Dict[str, Any]:
        """Get main dashboard statistics"""
        
        now = get_current_utc()
        today_start = datetime(now.year, now.month, now.day)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = datetime(now.year, now.month, 1)
        year_start = datetime(now.year, 1, 1)
        
        # User statistics
        total_users = db.query(User).count()
        new_users_today = db.query(User).filter(User.created_at >= today_start).count()
        new_users_this_week = db.query(User).filter(User.created_at >= week_start).count()
        new_users_this_month = db.query(User).filter(User.created_at >= month_start).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        
        # Event statistics
        total_events = db.query(Event).count()
        upcoming_events = db.query(Event).filter(Event.status == EventStatus.UPCOMING).count()
        completed_events = db.query(Event).filter(Event.status == EventStatus.COMPLETED).count()
        cancelled_events = db.query(Event).filter(Event.status == EventStatus.CANCELLED).count()
        
        # Booking statistics
        total_bookings = db.query(Booking).count()
        active_bookings = db.query(Booking).filter(Booking.status == BookingStatus.ACTIVE).count()
        cancelled_bookings = db.query(Booking).filter(Booking.status == BookingStatus.CANCELLED).count()
        
        # Revenue calculations
        revenue_today = db.query(func.sum(Booking.total_price)).filter(
            Booking.status == BookingStatus.ACTIVE,
            Booking.booking_date >= today_start
        ).scalar() or 0
        
        revenue_this_week = db.query(func.sum(Booking.total_price)).filter(
            Booking.status == BookingStatus.ACTIVE,
            Booking.booking_date >= week_start
        ).scalar() or 0
        
        revenue_this_month = db.query(func.sum(Booking.total_price)).filter(
            Booking.status == BookingStatus.ACTIVE,
            Booking.booking_date >= month_start
        ).scalar() or 0
        
        revenue_this_year = db.query(func.sum(Booking.total_price)).filter(
            Booking.status == BookingStatus.ACTIVE,
            Booking.booking_date >= year_start
        ).scalar() or 0
        
        total_revenue = db.query(func.sum(Booking.total_price)).filter(
            Booking.status == BookingStatus.ACTIVE
        ).scalar() or 0
        
        # Average booking value
        average_booking_value = total_revenue / total_bookings if total_bookings > 0 else 0
        
        # Conversion rate (bookings / unique users)
        unique_users_booked = db.query(Booking.user_id).distinct().count()
        conversion_rate = (unique_users_booked / total_users * 100) if total_users > 0 else 0
        
        # Popular categories
        popular_categories = db.query(
            Category.id,
            Category.name,
            Category.icon,
            Category.color,
            func.count(Booking.id).label("booking_count"),
            func.sum(Booking.total_price).label("revenue")
        ).join(Event, Event.category_id == Category.id)\
         .join(Booking, Booking.event_id == Event.id)\
         .filter(Booking.status == BookingStatus.ACTIVE)\
         .group_by(Category.id)\
         .order_by(func.count(Booking.id).desc())\
         .limit(5).all()
        
        popular_categories_data = [
            {
                "id": c.id,
                "name": c.name,
                "icon": c.icon,
                "color": c.color,
                "booking_count": c.booking_count,
                "revenue": float(c.revenue) if c.revenue else 0
            }
            for c in popular_categories
        ]
        
        # Recent bookings
        recent_bookings = db.query(
            Booking.id,
            Booking.user_id,
            User.username,
            User.first_name,
            User.last_name,
            Booking.event_id,
            Event.title.label("event_title"),
            Booking.number_of_seats,
            Booking.total_price,
            Booking.status,
            Booking.booking_date
        ).join(User, Booking.user_id == User.id)\
         .join(Event, Booking.event_id == Event.id)\
         .order_by(Booking.booking_date.desc())\
         .limit(10).all()
        
        recent_bookings_data = [
            {
                "id": b.id,
                "user_id": b.user_id,
                "user_name": f"{b.first_name} {b.last_name}",
                "username": b.username,
                "event_id": b.event_id,
                "event_title": b.event_title,
                "seats": b.number_of_seats,
                "total_price": float(b.total_price),
                "status": b.status.value,
                "booking_date": b.booking_date
            }
            for b in recent_bookings
        ]
        
        # Top events
        top_events = db.query(
            Event.id,
            Event.title,
            Category.name.label("category_name"),
            func.count(Booking.id).label("booking_count"),
            func.sum(Booking.total_price).label("revenue"),
            Event.total_seats,
            Event.available_seats
        ).join(Category, Event.category_id == Category.id, isouter=True)\
         .join(Booking, Booking.event_id == Event.id, isouter=True)\
         .filter(Booking.status == BookingStatus.ACTIVE)\
         .group_by(Event.id)\
         .order_by(func.count(Booking.id).desc())\
         .limit(5).all()
        
        top_events_data = [
            {
                "id": e.id,
                "title": e.title,
                "category": e.category_name,
                "booking_count": e.booking_count or 0,
                "revenue": float(e.revenue) if e.revenue else 0,
                "total_seats": e.total_seats,
                "available_seats": e.available_seats,
                "fill_rate": ((e.total_seats - e.available_seats) / e.total_seats * 100) if e.total_seats > 0 else 0
            }
            for e in top_events
        ]
        
        # Recent users
        recent_users = db.query(
            User.id,
            User.username,
            User.email,
            User.first_name,
            User.last_name,
            User.role,
            User.is_active,
            User.created_at,
            func.count(Booking.id).label("booking_count")
        ).outerjoin(Booking, Booking.user_id == User.id)\
         .group_by(User.id)\
         .order_by(User.created_at.desc())\
         .limit(10).all()
        
        recent_users_data = [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": f"{u.first_name} {u.last_name}",
                "role": u.role.value,
                "is_active": u.is_active,
                "joined_at": u.created_at,
                "booking_count": u.booking_count or 0
            }
            for u in recent_users
        ]
        
        return {
            "total_users": total_users,
            "new_users_today": new_users_today,
            "new_users_this_week": new_users_this_week,
            "new_users_this_month": new_users_this_month,
            "active_users": active_users,
            "total_events": total_events,
            "upcoming_events": upcoming_events,
            "completed_events": completed_events,
            "cancelled_events": cancelled_events,
            "total_bookings": total_bookings,
            "active_bookings": active_bookings,
            "cancelled_bookings": cancelled_bookings,
            "revenue_today": float(revenue_today),
            "revenue_this_week": float(revenue_this_week),
            "revenue_this_month": float(revenue_this_month),
            "revenue_this_year": float(revenue_this_year),
            "total_revenue": float(total_revenue),
            "average_booking_value": float(average_booking_value),
            "conversion_rate": round(conversion_rate, 2),
            "popular_categories": popular_categories_data,
            "recent_bookings": recent_bookings_data,
            "top_events": top_events_data,
            "recent_users": recent_users_data
        }
    
    @staticmethod
    def get_user_activity(db: Session) -> Dict[str, Any]:
        """Get user activity statistics"""
        
        now = get_current_utc()
        today_start = datetime(now.year, now.month, now.day)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = datetime(now.year, now.month, 1)
        
        total_users = db.query(User).count()
        
        # Active users (users with bookings in period)
        active_users_today = db.query(Booking.user_id).filter(
            Booking.booking_date >= today_start
        ).distinct().count()
        
        active_users_this_week = db.query(Booking.user_id).filter(
            Booking.booking_date >= week_start
        ).distinct().count()
        
        active_users_this_month = db.query(Booking.user_id).filter(
            Booking.booking_date >= month_start
        ).distinct().count()
        
        # New users
        new_users_today = db.query(User).filter(User.created_at >= today_start).count()
        new_users_this_week = db.query(User).filter(User.created_at >= week_start).count()
        new_users_this_month = db.query(User).filter(User.created_at >= month_start).count()
        
        # Users by role
        users_by_role = {
            "admin": db.query(User).filter(User.role == UserRole.ADMIN).count(),
            "user": db.query(User).filter(User.role == UserRole.USER).count()
        }
        
        # Users by join date (last 30 days)
        users_by_join_date = []
        for i in range(30):
            day_start = today_start - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            count = db.query(User).filter(
                User.created_at >= day_start,
                User.created_at < day_end
            ).count()
            users_by_join_date.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "count": count
            })
        
        # Top active users (most bookings)
        top_active_users = db.query(
            User.id,
            User.username,
            User.first_name,
            User.last_name,
            User.email,
            func.count(Booking.id).label("booking_count"),
            func.sum(Booking.total_price).label("total_spent")
        ).join(Booking, Booking.user_id == User.id)\
         .filter(Booking.status == BookingStatus.ACTIVE)\
         .group_by(User.id)\
         .order_by(func.count(Booking.id).desc())\
         .limit(10).all()
        
        top_active_users_data = [
            {
                "id": u.id,
                "username": u.username,
                "full_name": f"{u.first_name} {u.last_name}",
                "email": u.email,
                "booking_count": u.booking_count,
                "total_spent": float(u.total_spent) if u.total_spent else 0
            }
            for u in top_active_users
        ]
        
        # Login frequency simulation (based on booking patterns)
        booking_days = db.query(
            func.date(Booking.booking_date).label("booking_date"),
            func.count(Booking.id).label("count")
        ).filter(
            Booking.booking_date >= month_start
        ).group_by(func.date(Booking.booking_date)).all()
        
        login_frequency = {
            "daily_active": len([b for b in booking_days if b.count >= 10]),
            "weekly_active": len(set([b.booking_date for b in booking_days if b.count >= 5])),
            "monthly_active": len(booking_days)
        }
        
        return {
            "total_users": total_users,
            "active_users_today": active_users_today,
            "active_users_this_week": active_users_this_week,
            "active_users_this_month": active_users_this_month,
            "new_users_today": new_users_today,
            "new_users_this_week": new_users_this_week,
            "new_users_this_month": new_users_this_month,
            "users_by_role": users_by_role,
            "users_by_join_date": users_by_join_date,
            "top_active_users": top_active_users_data,
            "login_frequency": login_frequency
        }
    
    @staticmethod
    def get_event_analytics(db: Session) -> Dict[str, Any]:
        """Get event performance analytics"""
        
        now = get_current_utc()
        
        # Event counts by status
        events_by_status = {
            "upcoming": db.query(Event).filter(Event.status == EventStatus.UPCOMING).count(),
            "completed": db.query(Event).filter(Event.status == EventStatus.COMPLETED).count(),
            "cancelled": db.query(Event).filter(Event.status == EventStatus.CANCELLED).count()
        }
        
        # Events by category
        events_by_category = db.query(
            Category.id,
            Category.name,
            Category.icon,
            Category.color,
            func.count(Event.id).label("event_count"),
            func.sum(Event.total_seats).label("total_capacity")
        ).join(Event, Event.category_id == Category.id, isouter=True)\
         .group_by(Category.id)\
         .order_by(func.count(Event.id).desc()).all()
        
        events_by_category_data = [
            {
                "id": c.id,
                "name": c.name,
                "icon": c.icon,
                "color": c.color,
                "event_count": c.event_count,
                "total_capacity": c.total_capacity or 0
            }
            for c in events_by_category
        ]
        
        total_events = db.query(Event).count()
        upcoming_events_count = db.query(Event).filter(
            Event.status == EventStatus.UPCOMING,
            Event.event_date > now
        ).count()
        
        # Average price per event
        avg_price = db.query(func.avg(Event.price)).scalar() or 0
        
        # Total capacity and fill rate
        total_capacity = db.query(func.sum(Event.total_seats)).scalar() or 0
        total_booked_seats = db.query(func.sum(Booking.number_of_seats)).filter(
            Booking.status == BookingStatus.ACTIVE
        ).scalar() or 0
        average_fill_rate = (total_booked_seats / total_capacity * 100) if total_capacity > 0 else 0
        
        # Top performing events (most bookings)
        top_performing = db.query(
            Event.id,
            Event.title,
            Category.name.label("category_name"),
            func.count(Booking.id).label("booking_count"),
            func.sum(Booking.total_price).label("revenue"),
            ((Event.total_seats - Event.available_seats) / Event.total_seats * 100).label("fill_rate")
        ).join(Category, Event.category_id == Category.id, isouter=True)\
         .join(Booking, Booking.event_id == Event.id, isouter=True)\
         .filter(Booking.status == BookingStatus.ACTIVE)\
         .group_by(Event.id)\
         .order_by(func.count(Booking.id).desc())\
         .limit(10).all()
        
        top_performing_data = [
            {
                "id": e.id,
                "title": e.title,
                "category": e.category_name,
                "booking_count": e.booking_count or 0,
                "revenue": float(e.revenue) if e.revenue else 0,
                "fill_rate": round(float(e.fill_rate), 2) if e.fill_rate else 0
            }
            for e in top_performing
        ]
        
        # Worst performing events
        worst_performing = db.query(
            Event.id,
            Event.title,
            Category.name.label("category_name"),
            Event.total_seats,
            Event.available_seats,
            ((Event.total_seats - Event.available_seats) / Event.total_seats * 100).label("fill_rate")
        ).join(Category, Event.category_id == Category.id, isouter=True)\
         .filter(Event.status == EventStatus.UPCOMING)\
         .order_by(((Event.total_seats - Event.available_seats) / Event.total_seats * 100).asc())\
         .limit(10).all()
        
        worst_performing_data = [
            {
                "id": e.id,
                "title": e.title,
                "category": e.category_name,
                "total_seats": e.total_seats,
                "available_seats": e.available_seats,
                "fill_rate": round(float(e.fill_rate), 2) if e.fill_rate else 0
            }
            for e in worst_performing
        ]
        
        # Events by month
        events_by_month = db.query(
            extract('year', Event.created_at).label('year'),
            extract('month', Event.created_at).label('month'),
            func.count(Event.id).label('count')
        ).group_by('year', 'month').order_by('year', 'month').all()
        
        events_by_month_data = [
            {
                "year": int(e.year),
                "month": int(e.month),
                "month_name": datetime(int(e.year), int(e.month), 1).strftime("%B"),
                "count": e.count
            }
            for e in events_by_month
        ]
        
        return {
            "total_events": total_events,
            "events_by_status": events_by_status,
            "events_by_category": events_by_category_data,
            "upcoming_events_count": upcoming_events_count,
            "average_price_per_event": float(avg_price),
            "total_capacity": total_capacity,
            "average_fill_rate": round(average_fill_rate, 2),
            "top_performing_events": top_performing_data,
            "worst_performing_events": worst_performing_data,
            "events_by_month": events_by_month_data
        }
    
    @staticmethod
    def get_booking_report(db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, Any]:
        """Get booking report with optional date range"""
        
        query = db.query(Booking)
        
        if start_date:
            query = query.filter(Booking.booking_date >= start_date)
        if end_date:
            query = query.filter(Booking.booking_date <= end_date)
        
        total_bookings = query.count()
        completed_bookings = query.filter(Booking.status == BookingStatus.ACTIVE).count()
        cancelled_bookings = query.filter(Booking.status == BookingStatus.CANCELLED).count()
        
        # Bookings by status
        bookings_by_status = {
            "active": completed_bookings,
            "cancelled": cancelled_bookings
        }
        
        # Bookings by category
        bookings_by_category = db.query(
            Category.id,
            Category.name,
            func.count(Booking.id).label("booking_count"),
            func.sum(Booking.total_price).label("revenue")
        ).join(Event, Event.category_id == Category.id)\
         .join(Booking, Booking.event_id == Event.id)\
         .group_by(Category.id)\
         .order_by(func.count(Booking.id).desc()).all()
        
        bookings_by_category_data = [
            {
                "id": c.id,
                "name": c.name,
                "booking_count": c.booking_count,
                "revenue": float(c.revenue) if c.revenue else 0
            }
            for c in bookings_by_category
        ]
        
        # Bookings by event
        bookings_by_event = db.query(
            Event.id,
            Event.title,
            func.count(Booking.id).label("booking_count"),
            func.sum(Booking.total_price).label("revenue"),
            Event.total_seats,
            Event.available_seats
        ).join(Booking, Booking.event_id == Event.id)\
         .group_by(Event.id)\
         .order_by(func.count(Booking.id).desc())\
         .limit(20).all()
        
        bookings_by_event_data = [
            {
                "id": e.id,
                "title": e.title,
                "booking_count": e.booking_count,
                "revenue": float(e.revenue) if e.revenue else 0,
                "fill_rate": ((e.total_seats - e.available_seats) / e.total_seats * 100) if e.total_seats > 0 else 0
            }
            for e in bookings_by_event
        ]
        
        # Recent bookings
        recent_bookings = query.order_by(Booking.booking_date.desc()).limit(20).all()
        recent_bookings_data = [
            {
                "id": b.id,
                "user_id": b.user_id,
                "event_id": b.event_id,
                "seats": b.number_of_seats,
                "total_price": float(b.total_price),
                "status": b.status.value,
                "booking_date": b.booking_date
            }
            for b in recent_bookings
        ]
        
        # Peak booking hours
        peak_hours = db.query(
            extract('hour', Booking.booking_date).label('hour'),
            func.count(Booking.id).label('count')
        ).group_by('hour').order_by(func.count(Booking.id).desc()).limit(5).all()
        
        peak_booking_hours = [
            {"hour": int(h.hour), "count": h.count}
            for h in peak_hours
        ]
        
        # Average booking value
        total_revenue = db.query(func.sum(Booking.total_price)).filter(
            Booking.status == BookingStatus.ACTIVE
        ).scalar() or 0
        average_booking_value = total_revenue / completed_bookings if completed_bookings > 0 else 0
        
        return {
            "total_bookings": total_bookings,
            "completed_bookings": completed_bookings,
            "cancelled_bookings": cancelled_bookings,
            "bookings_by_status": bookings_by_status,
            "bookings_by_category": bookings_by_category_data,
            "bookings_by_event": bookings_by_event_data,
            "recent_bookings": recent_bookings_data,
            "peak_booking_hours": peak_booking_hours,
            "average_booking_value": float(average_booking_value)
        }
    
    @staticmethod
    def get_revenue_report(db: Session, period: str = "all_time") -> Dict[str, Any]:
        """Get revenue report for different periods"""
        
        now = get_current_utc()
        today_start = datetime(now.year, now.month, now.day)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = datetime(now.year, now.month, 1)
        year_start = datetime(now.year, 1, 1)
        
        # Revenue calculations
        revenue_today = db.query(func.sum(Booking.total_price)).filter(
            Booking.status == BookingStatus.ACTIVE,
            Booking.booking_date >= today_start
        ).scalar() or 0
        
        revenue_this_week = db.query(func.sum(Booking.total_price)).filter(
            Booking.status == BookingStatus.ACTIVE,
            Booking.booking_date >= week_start
        ).scalar() or 0
        
        revenue_this_month = db.query(func.sum(Booking.total_price)).filter(
            Booking.status == BookingStatus.ACTIVE,
            Booking.booking_date >= month_start
        ).scalar() or 0
        
        revenue_this_year = db.query(func.sum(Booking.total_price)).filter(
            Booking.status == BookingStatus.ACTIVE,
            Booking.booking_date >= year_start
        ).scalar() or 0
        
        total_revenue = db.query(func.sum(Booking.total_price)).filter(
            Booking.status == BookingStatus.ACTIVE
        ).scalar() or 0
        
        # Revenue by category
        revenue_by_category = db.query(
            Category.id,
            Category.name,
            Category.icon,
            Category.color,
            func.sum(Booking.total_price).label("revenue"),
            func.count(Booking.id).label("booking_count")
        ).join(Event, Event.category_id == Category.id)\
         .join(Booking, Booking.event_id == Event.id)\
         .filter(Booking.status == BookingStatus.ACTIVE)\
         .group_by(Category.id)\
         .order_by(func.sum(Booking.total_price).desc()).all()
        
        revenue_by_category_data = [
            {
                "id": c.id,
                "name": c.name,
                "icon": c.icon,
                "color": c.color,
                "revenue": float(c.revenue) if c.revenue else 0,
                "booking_count": c.booking_count
            }
            for c in revenue_by_category
        ]
        
        # Revenue by event (top 20)
        revenue_by_event = db.query(
            Event.id,
            Event.title,
            func.sum(Booking.total_price).label("revenue"),
            func.count(Booking.id).label("booking_count")
        ).join(Booking, Booking.event_id == Event.id)\
         .filter(Booking.status == BookingStatus.ACTIVE)\
         .group_by(Event.id)\
         .order_by(func.sum(Booking.total_price).desc())\
         .limit(20).all()
        
        revenue_by_event_data = [
            {
                "id": e.id,
                "title": e.title,
                "revenue": float(e.revenue) if e.revenue else 0,
                "booking_count": e.booking_count
            }
            for e in revenue_by_event
        ]
        
        # Revenue by month (last 12 months)
        revenue_by_month = []
        for i in range(12):
            month_date = today_start - timedelta(days=30 * i)
            month_start_date = datetime(month_date.year, month_date.month, 1)
            next_month = month_start_date.replace(day=28) + timedelta(days=4)
            month_end_date = next_month - timedelta(days=next_month.day)
            
            revenue = db.query(func.sum(Booking.total_price)).filter(
                Booking.status == BookingStatus.ACTIVE,
                Booking.booking_date >= month_start_date,
                Booking.booking_date <= month_end_date
            ).scalar() or 0
            
            revenue_by_month.append({
                "month": month_start_date.strftime("%Y-%m"),
                "month_name": month_start_date.strftime("%B %Y"),
                "revenue": float(revenue)
            })
        
        # Projected revenue (based on current month's performance)
        days_in_month = (month_start.replace(month=month_start.month % 12 + 1, day=1) - timedelta(days=1)).day
        days_passed = (now - month_start).days
        current_month_revenue = revenue_this_month
        projected_revenue = (current_month_revenue / days_passed) * days_in_month if days_passed > 0 else 0
        
        return {
            "total_revenue": float(total_revenue),
            "revenue_today": float(revenue_today),
            "revenue_this_week": float(revenue_this_week),
            "revenue_this_month": float(revenue_this_month),
            "revenue_this_year": float(revenue_this_year),
            "revenue_by_category": revenue_by_category_data,
            "revenue_by_event": revenue_by_event_data,
            "revenue_by_month": revenue_by_month,
            "projected_revenue": float(projected_revenue)
        }
    
    @staticmethod
    def export_bookings_report_csv(db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None) -> StreamingResponse:
        """Export booking report as CSV"""
        
        query = db.query(
            Booking.id,
            Booking.user_id,
            User.username,
            User.email,
            Booking.event_id,
            Event.title.label("event_title"),
            Booking.number_of_seats,
            Booking.total_price,
            Booking.status,
            Booking.booking_date
        ).join(User, Booking.user_id == User.id)\
         .join(Event, Booking.event_id == Event.id)
        
        if start_date:
            query = query.filter(Booking.booking_date >= start_date)
        if end_date:
            query = query.filter(Booking.booking_date <= end_date)
        
        bookings = query.order_by(Booking.booking_date.desc()).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            "Booking ID", "User ID", "Username", "Email", "Event ID", 
            "Event Title", "Number of Seats", "Total Price", "Status", "Booking Date"
        ])
        
        for booking in bookings:
            writer.writerow([
                booking.id,
                booking.user_id,
                booking.username,
                booking.email,
                booking.event_id,
                booking.event_title,
                booking.number_of_seats,
                f"${float(booking.total_price):.2f}",
                booking.status.value,
                booking.booking_date.strftime("%Y-%m-%d %H:%M:%S")
            ])
        
        output.seek(0)
        filename = f"bookings_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue().encode('utf-8')]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    @staticmethod
    def export_revenue_report_csv(db: Session, period: str = "all_time") -> StreamingResponse:
        """Export revenue report as CSV"""
        
        report = AdminService.get_revenue_report(db, period)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Revenue summary
        writer.writerow(["REVENUE REPORT SUMMARY"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Revenue", f"${report['total_revenue']:.2f}"])
        writer.writerow(["Revenue Today", f"${report['revenue_today']:.2f}"])
        writer.writerow(["Revenue This Week", f"${report['revenue_this_week']:.2f}"])
        writer.writerow(["Revenue This Month", f"${report['revenue_this_month']:.2f}"])
        writer.writerow(["Revenue This Year", f"${report['revenue_this_year']:.2f}"])
        writer.writerow([])
        
        # Revenue by category
        writer.writerow(["REVENUE BY CATEGORY"])
        writer.writerow(["Category ID", "Category Name", "Booking Count", "Revenue"])
        for cat in report["revenue_by_category"]:
            writer.writerow([cat["id"], cat["name"], cat["booking_count"], f"${cat['revenue']:.2f}"])
        
        writer.writerow([])
        
        # Revenue by month
        writer.writerow(["REVENUE BY MONTH"])
        writer.writerow(["Month", "Revenue"])
        for month in report["revenue_by_month"]:
            writer.writerow([month["month_name"], f"${month['revenue']:.2f}"])
        
        output.seek(0)
        filename = f"revenue_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue().encode('utf-8')]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
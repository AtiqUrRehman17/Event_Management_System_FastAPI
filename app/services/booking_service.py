from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timedelta
import csv
import io
from fastapi.responses import StreamingResponse, Response
from app.models.booking import Booking
from app.models.event import Event
from app.models.user import User
from app.models.category import Category
from app.schemas.booking import BookingCreate, BookingFilterParams, BookingSortField, BookingSortOrder
from app.core.exceptions import (
    EventNotFoundException,
    EventNotAvailableException,
    InsufficientSeatsException,
    BookingNotFoundException,
    BookingNotOwnedException,
    BookingAlreadyCancelledException
)
from app.core.enums import EventStatus, BookingStatus
from app.pagination import PaginationParams, paginate_query
from app.utils.datetime_utils import get_current_utc
import logging

logger = logging.getLogger(__name__)


class BookingService:

    @staticmethod
    def create_booking(
        db: Session,
        user_id: int,
        booking_data: BookingCreate
    ) -> Booking:
        """Create a new booking"""
        event = db.query(Event).filter(Event.id == booking_data.event_id).first()
        if not event:
            raise EventNotFoundException()

        if event.status != EventStatus.UPCOMING:
            raise EventNotAvailableException(
                "Cannot book this event as it is not upcoming"
            )

        now = get_current_utc()
        event_date = event.event_date
        
        if hasattr(event_date, 'tzinfo') and event_date.tzinfo is not None:
            event_date = event_date.replace(tzinfo=None)
        
        if event_date < now:
            raise EventNotAvailableException("Cannot book past events")

        if event.available_seats < booking_data.number_of_seats:
            raise InsufficientSeatsException(event.available_seats)

        total_price = event.price * booking_data.number_of_seats

        booking = Booking(
            user_id=user_id,
            event_id=booking_data.event_id,
            number_of_seats=booking_data.number_of_seats,
            total_price=total_price,
            status=BookingStatus.ACTIVE,
            payment_status="pending",  # Initialize payment status
            tax_rate=0.0,
            tax_amount=0.0
        )

        event.available_seats -= booking_data.number_of_seats

        db.add(booking)
        db.commit()
        db.refresh(booking)

        logger.info(f"Booking created: User {user_id} booked {booking_data.number_of_seats} seat(s) for event {booking_data.event_id}")

        return booking

    @staticmethod
    def get_booking_by_id(db: Session, booking_id: int) -> Booking:
        """Get booking by ID"""
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise BookingNotFoundException()
        return booking

    @staticmethod
    def get_user_bookings(
        db: Session,
        user_id: int,
        pagination: PaginationParams,
        status: Optional[BookingStatus] = None
    ) -> Tuple[List[Booking], int, float]:
        """
        Get all bookings for a specific user.
        Returns: (bookings, total_count, total_spent)
        """
        base_query = db.query(Booking).filter(Booking.user_id == user_id)

        total_spent_result = db.query(
            func.coalesce(func.sum(Booking.total_price), 0)
        ).filter(
            Booking.user_id == user_id,
            Booking.status == BookingStatus.ACTIVE
        ).scalar()

        total_spent = float(total_spent_result)

        if status:
            base_query = base_query.filter(Booking.status == status)

        base_query = base_query.order_by(Booking.created_at.desc())

        bookings, total = paginate_query(base_query, pagination)

        return bookings, total, total_spent

    @staticmethod
    def get_all_bookings(
        db: Session,
        pagination: PaginationParams,
        status: Optional[BookingStatus] = None
    ) -> Tuple[List[Booking], int]:
        """Get all bookings (Admin only)"""
        query = db.query(Booking)

        if status:
            query = query.filter(Booking.status == status)

        query = query.order_by(Booking.created_at.desc())

        bookings, total = paginate_query(query, pagination)

        return bookings, total

    @staticmethod
    def cancel_booking(
        db: Session,
        booking_id: int,
        user_id: int,
        is_admin: bool = False
    ) -> Booking:
        """Cancel a booking and notify next user in waitlist"""
        booking = BookingService.get_booking_by_id(db, booking_id)

        if not is_admin and booking.user_id != user_id:
            raise BookingNotOwnedException()

        if booking.status == BookingStatus.CANCELLED:
            raise BookingAlreadyCancelledException()

        event = booking.event
        
        if event.status != EventStatus.UPCOMING:
            raise EventNotAvailableException(
                "Cannot cancel booking for completed or cancelled events"
            )

        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = get_current_utc()

        event.available_seats += booking.number_of_seats

        db.commit()
        db.refresh(booking)

        logger.info(f"Booking cancelled: Booking {booking_id} by User {user_id} (Admin: {is_admin})")
        
        # Process waitlist for this event
        from app.services.waitlist_service import WaitlistService
        WaitlistService.process_cancellation(db, event.id)

        return booking

    @staticmethod
    def get_event_bookings(db: Session, event_id: int) -> List[Booking]:
        """Get all ACTIVE bookings for a specific event (Admin only)"""
        return db.query(Booking).filter(
            Booking.event_id == event_id,
            Booking.status == BookingStatus.ACTIVE
        ).all()

    @staticmethod
    def get_user_booking_summary(db: Session, user_id: int) -> dict:
        """Get booking summary for user dashboard"""
        active_result = db.query(
            func.count(Booking.id).label("count"),
            func.coalesce(func.sum(Booking.total_price), 0).label("total_spent")
        ).filter(
            Booking.user_id == user_id,
            Booking.status == BookingStatus.ACTIVE
        ).first()

        cancelled_count = db.query(func.count(Booking.id)).filter(
            Booking.user_id == user_id,
            Booking.status == BookingStatus.CANCELLED
        ).scalar()

        return {
            "total_active_bookings": active_result.count if active_result else 0,
            "total_cancelled_bookings": cancelled_count or 0,
            "total_spent": float(active_result.total_spent) if active_result else 0.0
        }

    @staticmethod
    def get_user_bookings_filtered(
        db: Session,
        user_id: int,
        filters: BookingFilterParams
    ) -> Tuple[List[Dict[str, Any]], int, float]:
        """
        Get user's bookings with advanced filtering, sorting, and pagination.
        """
        query = db.query(Booking).filter(Booking.user_id == user_id)
        query = query.join(Event, Booking.event_id == Event.id)
        
        if filters.status:
            query = query.filter(Booking.status == filters.status)
        
        if filters.start_date:
            query = query.filter(Booking.booking_date >= filters.start_date)
        if filters.end_date:
            query = query.filter(Booking.booking_date <= filters.end_date)
        
        if filters.min_price is not None:
            query = query.filter(Booking.total_price >= filters.min_price)
        if filters.max_price is not None:
            query = query.filter(Booking.total_price <= filters.max_price)
        
        if filters.event_name:
            query = query.filter(Event.title.ilike(f"%{filters.event_name}%"))
        
        sort_field = filters.sort_by.value
        sort_order = filters.sort_order.value
        
        if sort_field == "booking_date":
            order_col = Booking.booking_date
        elif sort_field == "event_date":
            order_col = Event.event_date
        elif sort_field == "price":
            order_col = Booking.total_price
        elif sort_field == "number_of_seats":
            order_col = Booking.number_of_seats
        else:
            order_col = Booking.booking_date
        
        if sort_order == "desc":
            query = query.order_by(order_col.desc())
        else:
            query = query.order_by(order_col.asc())
        
        total_spent_result = db.query(
            func.coalesce(func.sum(Booking.total_price), 0)
        ).filter(
            Booking.user_id == user_id,
            Booking.status == BookingStatus.ACTIVE
        ).scalar()
        total_spent = float(total_spent_result)
        
        total = query.count()
        
        offset = (filters.page - 1) * filters.limit
        bookings = query.offset(offset).limit(filters.limit).all()
        
        enriched_bookings = []
        for booking in bookings:
            enriched = BookingService._enrich_booking_with_details(booking, db)
            enriched_bookings.append(enriched)
        
        return enriched_bookings, total, total_spent
    
    @staticmethod
    def _enrich_booking_with_details(booking: Booking, db: Session) -> Dict[str, Any]:
        """Add detailed event information to booking"""
        event = booking.event
        now = get_current_utc()
        event_date = event.event_date
        
        days_until = None
        is_upcoming = False
        if event_date:
            if hasattr(event_date, 'tzinfo') and event_date.tzinfo is not None:
                event_date_naive = event_date.replace(tzinfo=None)
            else:
                event_date_naive = event_date
            
            days_until = (event_date_naive - now).days
            is_upcoming = days_until > 0 and event.status == EventStatus.UPCOMING
        
        can_cancel = (
            booking.status == BookingStatus.ACTIVE and 
            is_upcoming and
            event.status == EventStatus.UPCOMING
        )
        
        category_name = None
        category_icon = None
        category_color = None
        if event.category_id:
            category = db.query(Category).filter(Category.id == event.category_id).first()
            if category:
                category_name = category.name
                category_icon = category.icon
                category_color = category.color
        
        return {
            "id": booking.id,
            "user_id": booking.user_id,
            "event_id": event.id,
            "event_title": event.title,
            "event_description": event.description,
            "event_location": event.location,
            "event_date": event.event_date,
            "event_image_url": event.image_url,
            "event_category_name": category_name,
            "event_category_icon": category_icon,
            "event_category_color": category_color,
            "number_of_seats": booking.number_of_seats,
            "total_price": booking.total_price,
            "status": booking.status,
            "booking_date": booking.booking_date,
            "cancelled_at": booking.cancelled_at,
            "created_at": booking.created_at,
            "updated_at": booking.updated_at,
            "days_until_event": days_until,
            "is_upcoming": is_upcoming,
            "can_cancel": can_cancel,
            "cancellation_deadline": event.event_date - timedelta(days=1) if event.event_date else None
        }
    
    @staticmethod
    def get_booking_summary_stats(db: Session, user_id: int) -> Dict[str, Any]:
        """Get enhanced booking statistics for dashboard"""
        now = get_current_utc()
        
        bookings = db.query(Booking).filter(Booking.user_id == user_id).all()
        
        total_bookings = len(bookings)
        active_bookings = sum(1 for b in bookings if b.status == BookingStatus.ACTIVE)
        cancelled_bookings = sum(1 for b in bookings if b.status == BookingStatus.CANCELLED)
        total_spent = sum(float(b.total_price) for b in bookings if b.status == BookingStatus.ACTIVE)
        
        upcoming_events_count = 0
        past_events_count = 0
        
        for booking in bookings:
            if booking.status == BookingStatus.ACTIVE and booking.event:
                event_date = booking.event.event_date
                if hasattr(event_date, 'tzinfo') and event_date.tzinfo is not None:
                    event_date = event_date.replace(tzinfo=None)
                
                if event_date > now:
                    upcoming_events_count += 1
                else:
                    past_events_count += 1
        
        average_booking_value = total_spent / active_bookings if active_bookings > 0 else 0
        
        monthly_counts = {}
        for booking in bookings:
            month_key = booking.booking_date.strftime("%Y-%m")
            monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
        
        most_active_month = max(monthly_counts, key=monthly_counts.get) if monthly_counts else None
        
        return {
            "total_bookings": total_bookings,
            "active_bookings": active_bookings,
            "cancelled_bookings": cancelled_bookings,
            "total_spent": round(total_spent, 2),
            "upcoming_events_count": upcoming_events_count,
            "past_events_count": past_events_count,
            "average_booking_value": round(average_booking_value, 2),
            "most_active_month": most_active_month
        }
    
    @staticmethod
    def get_booking_timeline(db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Get booking timeline for user (chronological order)"""
        now = get_current_utc()
        
        future_bookings = db.query(Booking).join(Event).filter(
            Booking.user_id == user_id,
            Booking.status == BookingStatus.ACTIVE,
            Event.event_date > now
        ).order_by(Event.event_date.asc()).all()
        
        past_bookings = db.query(Booking).join(Event).filter(
            Booking.user_id == user_id,
            Booking.status == BookingStatus.ACTIVE,
            Event.event_date <= now
        ).order_by(Event.event_date.desc()).limit(10).all()
        
        timeline = []
        
        for booking in future_bookings:
            enriched = BookingService._enrich_booking_with_details(booking, db)
            enriched["timeline_type"] = "upcoming"
            timeline.append(enriched)
        
        for booking in past_bookings:
            enriched = BookingService._enrich_booking_with_details(booking, db)
            enriched["timeline_type"] = "past"
            timeline.append(enriched)
        
        return timeline
    
    @staticmethod
    def export_bookings_to_csv(db: Session, user_id: int, filters: BookingFilterParams = None) -> StreamingResponse:
        """Export user's bookings to CSV file"""
        if filters:
            bookings, total, _ = BookingService.get_user_bookings_filtered(db, user_id, filters)
        else:
            query = db.query(Booking).filter(
                Booking.user_id == user_id,
                Booking.status == BookingStatus.ACTIVE
            ).join(Event).order_by(Booking.booking_date.desc())
            bookings = query.all()
            enriched_bookings = []
            for booking in bookings:
                enriched_bookings.append(BookingService._enrich_booking_with_details(booking, db))
            bookings = enriched_bookings
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            "Booking ID", "Event Name", "Event Date", "Event Location", 
            "Number of Seats", "Total Price", "Status", "Booking Date", 
            "Cancelled Date", "Days Until Event"
        ])
        
        for booking in bookings:
            writer.writerow([
                booking["id"],
                booking["event_title"],
                booking["event_date"].strftime("%Y-%m-%d %H:%M") if booking["event_date"] else "",
                booking["event_location"],
                booking["number_of_seats"],
                f"${booking['total_price']:.2f}",
                booking["status"].value,
                booking["booking_date"].strftime("%Y-%m-%d %H:%M"),
                booking["cancelled_at"].strftime("%Y-%m-%d %H:%M") if booking["cancelled_at"] else "",
                booking["days_until_event"] if booking["days_until_event"] else ""
            ])
        
        output.seek(0)
        filename = f"bookings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue().encode('utf-8')]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    @staticmethod
    def export_bookings_to_pdf(db: Session, user_id: int, filters: BookingFilterParams = None) -> Response:
        """Export user's bookings to PDF file"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import inch
        except ImportError:
            raise ImportError("reportlab is required for PDF export. Install with: pip install reportlab")
        
        # Get bookings
        if filters:
            bookings, total, _ = BookingService.get_user_bookings_filtered(db, user_id, filters)
        else:
            query = db.query(Booking).filter(
                Booking.user_id == user_id,
                Booking.status == BookingStatus.ACTIVE
            ).join(Event).order_by(Booking.booking_date.desc())
            bookings = query.all()
            enriched_bookings = []
            for booking in bookings:
                enriched_bookings.append(BookingService._enrich_booking_with_details(booking, db))
            bookings = enriched_bookings
        
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30
        )
        
        # Story/content
        story = []
        
        # Title
        story.append(Paragraph("My Bookings Report", title_style))
        story.append(Spacer(1, 12))
        
        # Add generation date
        from datetime import datetime
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Summary
        summary = BookingService.get_booking_summary_stats(db, user_id)
        story.append(Paragraph(f"Total Bookings: {summary['total_bookings']}", styles['Normal']))
        story.append(Paragraph(f"Active Bookings: {summary['active_bookings']}", styles['Normal']))
        story.append(Paragraph(f"Cancelled Bookings: {summary['cancelled_bookings']}", styles['Normal']))
        story.append(Paragraph(f"Total Spent: ${summary['total_spent']:.2f}", styles['Normal']))
        story.append(Paragraph(f"Average Booking Value: ${summary['average_booking_value']:.2f}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Table data
        table_data = [["Booking ID", "Event", "Date", "Seats", "Price", "Status"]]
        
        for booking in bookings:
            event_title = booking["event_title"]
            if len(event_title) > 30:
                event_title = event_title[:27] + "..."
            
            event_date = ""
            if booking["event_date"]:
                event_date = booking["event_date"].strftime("%Y-%m-%d")
            
            table_data.append([
                str(booking["id"]),
                event_title,
                event_date,
                str(booking["number_of_seats"]),
                f"${booking['total_price']:.2f}",
                booking["status"].value
            ])
        
        # Create table
        table = Table(table_data, colWidths=[60, 180, 80, 50, 60, 70])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        story.append(table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        filename = f"bookings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
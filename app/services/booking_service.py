from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timedelta
import csv
import io
import time
import logging
from fastapi.responses import StreamingResponse, Response
from app.models.booking import Booking
from app.models.event import Event
from app.models.user import User
from app.models.category import Category
from app.models.payment import Payment
from app.schemas.booking import BookingCreate, BookingFilterParams, BookingSortField, BookingSortOrder, BookingHistoryFilterParams
from app.core.exceptions import (
    EventNotFoundException,
    EventNotAvailableException,
    InsufficientSeatsException,
    BookingNotFoundException,
    BookingNotOwnedException,
    BookingAlreadyCancelledException
)
from app.core.enums import EventStatus, BookingStatus, PaymentStatus
from app.pagination import PaginationParams, paginate_query
from app.utils.datetime_utils import get_current_utc
from app.services.notification_service import NotificationService
from app.services.audit_service import AuditService
from app.models.audit_log import AuditActionType, AuditActionCategory

logger = logging.getLogger(__name__)


class BookingService:

    @staticmethod
    def create_booking_with_retry(
        db: Session,
        user_id: int,
        booking_data: BookingCreate,
        request=None,
        max_retries: int = 3,
        retry_delay: float = 0.1
    ) -> Booking:
        """
        Create booking with automatic retry on concurrency conflicts.
        Retries on both database deadlocks and optimistic locking failures.
        """
        for attempt in range(max_retries):
            try:
                return BookingService.create_booking(db, user_id, booking_data, request)
            except OperationalError as e:
                error_msg = str(e).lower()
                if ("deadlock" in error_msg or "lock" in error_msg) and attempt < max_retries - 1:
                    logger.warning(f"Database lock detected, retrying booking... (attempt {attempt + 2}/{max_retries})")
                    db.rollback()
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                raise
            except InsufficientSeatsException as e:
                # Check if this is a concurrency conflict (not actual insufficient seats)
                error_msg = str(e)
                if "availability changed" in error_msg and attempt < max_retries - 1:
                    logger.warning(f"Concurrency conflict detected, retrying booking... (attempt {attempt + 2}/{max_retries})")
                    db.rollback()
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                raise
            except SQLAlchemyError as e:
                db.rollback()
                logger.error(f"Database error during booking: {str(e)}")
                raise

    @staticmethod
    def create_booking(
        db: Session,
        user_id: int,
        booking_data: BookingCreate,
        request=None
    ) -> Booking:
        """
        Create a new booking with optimistic locking to prevent overselling.
        Uses version column for concurrency control - works on SQLite and other databases.
        """
        # First, read the event to get current version and check availability
        event = db.query(Event).filter(
            Event.id == booking_data.event_id
        ).first()
        
        if not event:
            raise EventNotFoundException()

        # Check if event is upcoming
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

        # Check seat availability
        if event.available_seats < booking_data.number_of_seats:
            raise InsufficientSeatsException(event.available_seats)

        # Calculate total price with proper decimal precision
        # Round to 2 decimal places to handle fractional prices correctly
        total_price = round(event.price * booking_data.number_of_seats, 2)

        # Atomic update with optimistic locking:
        # UPDATE events SET available_seats = available_seats - ?, version = version + 1
        # WHERE id = ? AND available_seats >= ? AND version = ?
        # This ensures we don't oversell and detects concurrent modifications
        rows_updated = db.query(Event).filter(
            Event.id == booking_data.event_id,
            Event.available_seats >= booking_data.number_of_seats,
            Event.version == event.version
        ).update({
            Event.available_seats: Event.available_seats - booking_data.number_of_seats,
            Event.version: Event.version + 1
        }, synchronize_session=False)
        
        if rows_updated == 0:
            # Another transaction modified the event - retry
            db.rollback()
            raise InsufficientSeatsException(
                "Seat availability changed, please try again"
            )

        # Create booking
        booking = Booking(
            user_id=user_id,
            event_id=booking_data.event_id,
            number_of_seats=booking_data.number_of_seats,
            total_price=total_price,
            status=BookingStatus.ACTIVE,
            payment_status="pending",
            tax_rate=0.0,
            tax_amount=0.0
        )

        db.add(booking)
        db.commit()
        db.refresh(booking)

        # Refresh event to get updated version
        db.refresh(event)

        logger.info(f"Booking created: User {user_id} booked {booking_data.number_of_seats} seat(s) for event {booking_data.event_id}, Total: ${total_price:.2f}")
        
        # Audit log: Booking created
        AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditActionType.BOOKING_CREATE,
            category=AuditActionCategory.BOOKING,
            request=request,
            entity_type="booking",
            entity_id=booking.id,
            new_value={
                "event_id": booking.event_id,
                "seats": booking.number_of_seats,
                "total_price": float(total_price)
            }
        )
        
        # Create associated payment record
        payment = Payment(
            booking_id=booking.id,
            amount=round(total_price, 2),
            currency="USD",
            status=PaymentStatus.PENDING,
            method=None,
            transaction_id=f"txn_{booking.id}_{get_current_utc().strftime('%Y%m%d%H%M%S')}",
            initiated_at=get_current_utc()
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        logger.info(f"Payment record created: Payment {payment.id} for Booking {booking.id}")

        # Send booking confirmation notification
        try:
            NotificationService.send_booking_confirmation(db, booking.id)
        except Exception as e:
            logger.error(f"Failed to send booking confirmation notification: {str(e)}")

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
        is_admin: bool = False,
        request=None
    ) -> Booking:
        """
        Cancel a booking.
        
        - Regular users: Can only cancel their own ACTIVE bookings for UPCOMING events
        - Admin users: Can cancel ANY booking (regardless of event status or booking status)
        """
        booking = BookingService.get_booking_by_id(db, booking_id)

        # Check ownership (unless admin)
        if not is_admin and booking.user_id != user_id:
            raise BookingNotOwnedException()

        # Check if already cancelled
        if booking.status == BookingStatus.CANCELLED:
            raise BookingAlreadyCancelledException()

        event = booking.event
        
        # For regular users: Check if event is still upcoming
        if not is_admin:
            if event.status != EventStatus.UPCOMING:
                raise EventNotAvailableException(
                    "Cannot cancel booking for completed or cancelled events"
                )
        
        # Store old status for audit
        old_status = booking.status.value
        
        # Update booking status
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = get_current_utc()

        # Return seats to event (only if event is still upcoming)
        # If event is completed/cancelled, seats don't need to be returned
        if event.status == EventStatus.UPCOMING:
            event.available_seats += booking.number_of_seats
            logger.info(f"Returned {booking.number_of_seats} seat(s) to event {event.id}")
        else:
            logger.info(f"Booking cancelled for {event.status} event - seats not returned")

        db.commit()
        db.refresh(booking)

        logger.info(f"Booking cancelled: Booking {booking_id} by User {user_id} (Admin: {is_admin})")
        
        # Audit log: Booking cancelled
        action = AuditActionType.BOOKING_ADMIN_CANCEL if is_admin else AuditActionType.BOOKING_CANCEL
        AuditService.log_action(
            db=db,
            user_id=user_id,
            action=action,
            category=AuditActionCategory.BOOKING,
            request=request,
            entity_type="booking",
            entity_id=booking_id,
            old_value={"status": old_status},
            new_value={"status": "cancelled"},
            details={
                "cancelled_by_admin": is_admin, 
                "original_user_id": booking.user_id if is_admin else None,
                "event_status": event.status.value
            }
        )
        
        # Send booking cancellation notification (only for active bookings)
        try:
            NotificationService.send_booking_cancellation(db, booking.id)
        except Exception as e:
            logger.error(f"Failed to send booking cancellation notification: {str(e)}")
        
        # Process waitlist for this event (only if event is still upcoming)
        if event.status == EventStatus.UPCOMING:
            from app.services.waitlist_service import WaitlistService
            try:
                WaitlistService.process_cancellation(db, event.id)
            except Exception as e:
                logger.error(f"Failed to process waitlist after cancellation: {str(e)}")

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
            "cancellation_deadline": event.event_date - timedelta(days=1) if event.event_date else None,
            "invoice_number": booking.invoice_number,
            "payment_status": booking.payment_status
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
            "Cancelled Date", "Days Until Event", "Invoice Number", "Payment Status"
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
                booking["days_until_event"] if booking["days_until_event"] else "",
                booking["invoice_number"] or "",
                booking["payment_status"] or ""
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
    
    # ==================== Booking History Methods ====================
    
    @staticmethod
    def get_booking_history(
        db: Session,
        user_id: int,
        filters: BookingHistoryFilterParams = None
    ) -> Dict[str, Any]:
        """
        Get dedicated booking history with upcoming, past, and cancelled bookings.
        """
        now = get_current_utc()
        
        # Base query for user's bookings
        base_query = db.query(Booking).filter(Booking.user_id == user_id)
        
        # Apply common filters
        if filters:
            if filters.start_date:
                base_query = base_query.filter(Booking.booking_date >= filters.start_date)
            if filters.end_date:
                base_query = base_query.filter(Booking.booking_date <= filters.end_date)
            if filters.min_price:
                base_query = base_query.filter(Booking.total_price >= filters.min_price)
            if filters.max_price:
                base_query = base_query.filter(Booking.total_price <= filters.max_price)
        
        # Get all bookings
        all_bookings = base_query.all()
        
        # Categorize bookings
        upcoming_bookings = []
        past_bookings = []
        cancelled_bookings = []
        
        for booking in all_bookings:
            # Get event details
            event = booking.event
            if not event:
                continue
            
            event_date = event.event_date
            if hasattr(event_date, 'tzinfo') and event_date.tzinfo is not None:
                event_date = event_date.replace(tzinfo=None)
            
            days_until = (event_date - now).days
            is_upcoming = days_until > 0 and booking.status == BookingStatus.ACTIVE
            is_past = days_until <= 0 and booking.status == BookingStatus.ACTIVE
            is_cancelled = booking.status == BookingStatus.CANCELLED
            
            # Apply event name filter
            if filters and filters.event_name:
                if filters.event_name.lower() not in event.title.lower():
                    continue
            
            # Apply category filter
            if filters and filters.category_id:
                if event.category_id != filters.category_id:
                    continue
            
            # Apply type filter
            if filters and filters.type:
                if filters.type == "upcoming" and not is_upcoming:
                    continue
                if filters.type == "past" and not is_past:
                    continue
                if filters.type == "cancelled" and not is_cancelled:
                    continue
            
            # Get category info
            category_name = None
            category_icon = None
            if event.category_id:
                category = db.query(Category).filter(Category.id == event.category_id).first()
                if category:
                    category_name = category.name
                    category_icon = category.icon
            
            history_item = {
                "id": booking.id,
                "booking_date": booking.booking_date,
                "event_id": event.id,
                "event_title": event.title,
                "event_date": event.event_date,
                "event_location": event.location,
                "event_image_url": event.image_url,
                "category_name": category_name,
                "category_icon": category_icon,
                "number_of_seats": booking.number_of_seats,
                "total_price": booking.total_price,
                "status": booking.status,
                "cancelled_at": booking.cancelled_at,
                "days_until_event": days_until,
                "is_past": is_past,
                "is_upcoming": is_upcoming,
                "can_cancel": is_upcoming and booking.status == BookingStatus.ACTIVE,
                "invoice_number": booking.invoice_number,
                "payment_status": booking.payment_status
            }
            
            if is_upcoming:
                upcoming_bookings.append(history_item)
            elif is_past:
                past_bookings.append(history_item)
            elif is_cancelled:
                cancelled_bookings.append(history_item)
        
        # Sort upcoming by event date (ascending)
        upcoming_bookings.sort(key=lambda x: x["event_date"])
        
        # Sort past by event date (descending)
        past_bookings.sort(key=lambda x: x["event_date"], reverse=True)
        
        # Sort cancelled by cancellation date (descending)
        cancelled_bookings.sort(key=lambda x: x["cancelled_at"] or x["booking_date"], reverse=True)
        
        # Calculate summary
        total_bookings = len(all_bookings)
        total_active = len([b for b in all_bookings if b.status == BookingStatus.ACTIVE])
        total_cancelled = len(cancelled_bookings)
        total_spent = sum(float(b.total_price) for b in all_bookings if b.status == BookingStatus.ACTIVE)
        upcoming_count = len(upcoming_bookings)
        past_count = len(past_bookings)
        
        summary = {
            "total_bookings": total_bookings,
            "active_bookings": total_active,
            "cancelled_bookings": total_cancelled,
            "total_spent": round(total_spent, 2),
            "upcoming_count": upcoming_count,
            "past_count": past_count,
            "average_booking_value": round(total_spent / total_active, 2) if total_active > 0 else 0
        }
        
        # Pagination info
        pagination = {
            "total_upcoming": len(upcoming_bookings),
            "total_past": len(past_bookings),
            "total_cancelled": len(cancelled_bookings),
            "items_per_page": 10
        }
        
        return {
            "upcoming_bookings": upcoming_bookings,
            "past_bookings": past_bookings,
            "cancelled_bookings": cancelled_bookings,
            "summary": summary,
            "pagination": pagination
        }
    
    @staticmethod
    def get_booking_statistics(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Get detailed booking statistics for user dashboard.
        """
        # Get all user's bookings
        bookings = db.query(Booking).filter(Booking.user_id == user_id).all()
        
        # Monthly spending
        monthly_spending = {}
        for booking in bookings:
            if booking.status == BookingStatus.ACTIVE:
                month_key = booking.booking_date.strftime("%Y-%m")
                monthly_spending[month_key] = monthly_spending.get(month_key, 0) + float(booking.total_price)
        
        # Most popular categories
        category_counts = {}
        for booking in bookings:
            if booking.event and booking.event.category_id:
                cat_id = booking.event.category_id
                category_counts[cat_id] = category_counts.get(cat_id, 0) + booking.number_of_seats
        
        # Get category names
        popular_categories = []
        for cat_id, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            category = db.query(Category).filter(Category.id == cat_id).first()
            if category:
                popular_categories.append({
                    "id": category.id,
                    "name": category.name,
                    "icon": category.icon,
                    "booking_count": count
                })
        
        # Calculate average days before event that user books
        booking_lead_times = []
        for booking in bookings:
            if booking.event and booking.event.event_date:
                lead_time = (booking.event.event_date - booking.booking_date).days
                if lead_time >= 0:
                    booking_lead_times.append(lead_time)
        
        average_lead_time = sum(booking_lead_times) / len(booking_lead_times) if booking_lead_times else 0
        
        # Most active months (booking frequency)
        booking_months = {}
        for booking in bookings:
            month_key = booking.booking_date.strftime("%Y-%m")
            booking_months[month_key] = booking_months.get(month_key, 0) + 1
        
        most_active_month = max(booking_months, key=booking_months.get) if booking_months else None
        
        return {
            "total_spent": round(sum(float(b.total_price) for b in bookings if b.status == BookingStatus.ACTIVE), 2),
            "total_bookings": len(bookings),
            "active_bookings": len([b for b in bookings if b.status == BookingStatus.ACTIVE]),
            "cancelled_bookings": len([b for b in bookings if b.status == BookingStatus.CANCELLED]),
            "average_booking_value": round(sum(float(b.total_price) for b in bookings if b.status == BookingStatus.ACTIVE) / len([b for b in bookings if b.status == BookingStatus.ACTIVE]), 2) if [b for b in bookings if b.status == BookingStatus.ACTIVE] else 0,
            "average_lead_time_days": round(average_lead_time, 1),
            "most_active_month": most_active_month,
            "monthly_spending": [{"month": k, "amount": v} for k, v in sorted(monthly_spending.items())[-6:]],
            "popular_categories": popular_categories,
            "booking_timeline": [
                {"month": k, "count": v} for k, v in sorted(booking_months.items())[-6:]
            ]
        }
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import io
import qrcode
import base64
from fastapi import Response
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from app.models.booking import Booking
from app.models.user import User
from app.models.event import Event
from app.schemas.invoice import InvoiceData, InvoiceAddress, InvoiceItem
from app.core.exceptions import BookingNotFoundException, PermissionDeniedException
from app.core.enums import BookingStatus
from app.utils.datetime_utils import get_current_utc
import logging

logger = logging.getLogger(__name__)


class InvoiceService:
    
    @staticmethod
    def generate_invoice_number(booking_id: int) -> str:
        """Generate unique invoice number"""
        year = datetime.now().strftime("%Y")
        month = datetime.now().strftime("%m")
        return f"INV-{year}{month}-{booking_id:06d}"
    
    @staticmethod
    def calculate_tax(amount: float, tax_rate: float) -> Dict[str, float]:
        """Calculate tax amount"""
        tax_amount = amount * (tax_rate / 100)
        total_amount = amount + tax_amount
        return {
            "subtotal": round(amount, 2),
            "tax_amount": round(tax_amount, 2),
            "total_amount": round(total_amount, 2)
        }
    
    @staticmethod
    def get_invoice_data(
        db: Session, 
        booking_id: int, 
        tax_rate: float = 0.0,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> InvoiceData:
        """Get complete invoice data for a booking"""
        
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise BookingNotFoundException()
        
        # Check permissions
        if not is_admin and user_id and booking.user_id != user_id:
            raise PermissionDeniedException()
        
        event = booking.event
        user = booking.user
        
        # Calculate tax
        tax_calculation = InvoiceService.calculate_tax(booking.total_price, tax_rate)
        
        # Generate invoice number if not exists
        if not booking.invoice_number:
            booking.invoice_number = InvoiceService.generate_invoice_number(booking_id)
            booking.subtotal = booking.total_price
            booking.tax_rate = tax_rate
            booking.tax_amount = tax_calculation["tax_amount"]
            booking.total_amount = tax_calculation["total_amount"]
            booking.invoice_generated_at = get_current_utc()
            db.commit()
        
        # Create invoice items
        items = [
            InvoiceItem(
                description=f"{event.title} - {event.event_date.strftime('%B %d, %Y at %I:%M %p')}",
                quantity=booking.number_of_seats,
                unit_price=event.price,
                total=booking.number_of_seats * event.price
            )
        ]
        
        # Add service fee if applicable
        if tax_rate > 0:
            items.append(
                InvoiceItem(
                    description=f"Tax ({tax_rate}%)",
                    quantity=1,
                    unit_price=tax_calculation["tax_amount"],
                    total=tax_calculation["tax_amount"]
                )
            )
        
        # Create customer address
        customer = InvoiceAddress(
            full_name=f"{user.first_name} {user.last_name}",
            email=user.email,
            phone=user.phone,
            address_line1=user.bio  # Placeholder - you can add proper address fields
        )
        
        # Generate QR code (optional)
        qr_code_url = InvoiceService.generate_qr_code(booking.invoice_number, booking.total_amount)
        
        return InvoiceData(
            invoice_number=booking.invoice_number,
            invoice_date=booking.invoice_generated_at or booking.booking_date,
            due_date=booking.invoice_generated_at + timedelta(days=30) if booking.invoice_generated_at else None,
            booking_id=booking.id,
            booking_date=booking.booking_date,
            event_id=event.id,
            event_title=event.title,
            event_date=event.event_date,
            event_location=event.location,
            event_image_url=event.image_url,
            customer=customer,
            subtotal=tax_calculation["subtotal"],
            tax_rate=tax_rate,
            tax_amount=tax_calculation["tax_amount"],
            total_amount=tax_calculation["total_amount"],
            currency="USD",
            payment_status=booking.payment_status or "pending",
            payment_method=booking.payment_method,
            payment_date=booking.paid_at,
            transaction_id=booking.payment_transaction_id,
            items=items,
            notes="Thank you for your booking!",
            terms="Tickets are non-refundable within 7 days of the event.",
            qr_code_url=qr_code_url
        )
    
    @staticmethod
    def generate_qr_code(invoice_number: str, amount: float) -> Optional[str]:
        """Generate QR code as base64 string"""
        try:
            import qrcode
            qr_data = f"Invoice: {invoice_number}\nAmount: ${amount:.2f}"
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"
        except Exception as e:
            logger.warning(f"QR code generation failed: {str(e)}")
            return None
    
    @staticmethod
    def generate_pdf_invoice(db: Session, booking_id: int, tax_rate: float = 0.0, user_id: Optional[int] = None, is_admin: bool = False) -> Response:
        """Generate PDF invoice for download"""
        
        invoice_data = InvoiceService.get_invoice_data(db, booking_id, tax_rate, user_id, is_admin)
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=1  # Center
        )
        
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey
        )
        
        story = []
        
        # Header
        story.append(Paragraph("INVOICE", title_style))
        story.append(Spacer(1, 12))
        
        # Invoice Info
        info_data = [
            [Paragraph(f"<b>Invoice Number:</b> {invoice_data.invoice_number}", styles['Normal']),
             Paragraph(f"<b>Date:</b> {invoice_data.invoice_date.strftime('%B %d, %Y')}", styles['Normal'])],
            [Paragraph(f"<b>Booking ID:</b> {invoice_data.booking_id}", styles['Normal']),
             Paragraph(f"<b>Due Date:</b> {invoice_data.due_date.strftime('%B %d, %Y') if invoice_data.due_date else 'N/A'}", styles['Normal'])],
        ]
        
        info_table = Table(info_data, colWidths=[250, 250])
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Bill To Section
        story.append(Paragraph("<b>Bill To:</b>", styles['Normal']))
        story.append(Paragraph(f"{invoice_data.customer.full_name}", styles['Normal']))
        story.append(Paragraph(f"{invoice_data.customer.email}", styles['Normal']))
        if invoice_data.customer.phone:
            story.append(Paragraph(f"{invoice_data.customer.phone}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Event Details
        story.append(Paragraph("<b>Event Details:</b>", styles['Normal']))
        story.append(Paragraph(f"<b>Event:</b> {invoice_data.event_title}", styles['Normal']))
        story.append(Paragraph(f"<b>Date:</b> {invoice_data.event_date.strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
        story.append(Paragraph(f"<b>Location:</b> {invoice_data.event_location}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Items Table
        table_data = [["Description", "Qty", "Unit Price", "Total"]]
        for item in invoice_data.items:
            table_data.append([
                item.description,
                str(item.quantity),
                f"${item.unit_price:.2f}",
                f"${item.total:.2f}"
            ])
        
        # Add totals
        table_data.append(["", "", "", ""])
        table_data.append(["", "", "<b>Subtotal:</b>", f"<b>${invoice_data.subtotal:.2f}</b>"])
        if invoice_data.tax_amount > 0:
            table_data.append(["", "", f"<b>Tax ({invoice_data.tax_rate}%):</b>", f"<b>${invoice_data.tax_amount:.2f}</b>"])
        table_data.append(["", "", "<b>Total:</b>", f"<b>${invoice_data.total_amount:.2f}</b>"])
        
        items_table = Table(table_data, colWidths=[300, 50, 100, 100])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -4), colors.beige),
            ('GRID', (0, 0), (-1, -4), 1, colors.grey),
            ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 30))
        
        # Payment Status
        status_color = "#27ae60" if invoice_data.payment_status == "paid" else "#e74c3c"
        story.append(Paragraph(f"<b>Payment Status:</b> <font color='{status_color}'>{invoice_data.payment_status.upper()}</font>", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Notes and Terms
        if invoice_data.notes:
            story.append(Paragraph("<b>Notes:</b>", styles['Normal']))
            story.append(Paragraph(invoice_data.notes, header_style))
            story.append(Spacer(1, 10))
        
        if invoice_data.terms:
            story.append(Paragraph("<b>Terms & Conditions:</b>", styles['Normal']))
            story.append(Paragraph(invoice_data.terms, header_style))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph("Thank you for your business!", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        
        filename = f"invoice_{invoice_data.invoice_number}.pdf"
        
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    @staticmethod
    def update_payment_status(
        db: Session,
        booking_id: int,
        payment_status: str,
        payment_method: str = None,
        transaction_id: str = None
    ) -> Booking:
        """Update booking payment status"""
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise BookingNotFoundException()
        
        booking.payment_status = payment_status
        if payment_method:
            booking.payment_method = payment_method
        if transaction_id:
            booking.payment_transaction_id = transaction_id
        
        if payment_status == "paid":
            booking.paid_at = get_current_utc()
        
        db.commit()
        db.refresh(booking)
        
        return booking
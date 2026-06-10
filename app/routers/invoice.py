from fastapi import APIRouter, Depends, Query, Body, Response
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db, get_current_user, get_current_admin
from app.models.user import User
from app.schemas.invoice import InvoiceData, InvoiceResponse, InvoiceGenerateRequest
from app.services.invoice_service import InvoiceService
from app.utils.response import success_response
from app.core.enums import UserRole

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("/{booking_id}", response_model=dict)
async def get_invoice_json(
    booking_id: int,
    tax_rate: float = Query(0.0, ge=0, le=100, description="Tax rate percentage"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get invoice data as JSON for a booking.
    Users can view their own invoices, admins can view any.
    """
    is_admin = current_user.role == UserRole.ADMIN
    invoice_data = InvoiceService.get_invoice_data(
        db, booking_id, tax_rate, current_user.id, is_admin
    )
    
    return success_response(
        data=invoice_data.model_dump(),
        message="Invoice retrieved successfully"
    )


@router.get("/{booking_id}/pdf", response_class=Response)
async def get_invoice_pdf(
    booking_id: int,
    tax_rate: float = Query(0.0, ge=0, le=100, description="Tax rate percentage"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download invoice as PDF for a booking.
    Users can download their own invoices, admins can download any.
    """
    is_admin = current_user.role == UserRole.ADMIN
    return InvoiceService.generate_pdf_invoice(
        db, booking_id, tax_rate, current_user.id, is_admin
    )


@router.post("/{booking_id}/payment", response_model=dict)
async def update_payment_status(
    booking_id: int,
    payment_status: str = Query(..., description="Payment status: pending, paid, failed, refunded"),
    payment_method: Optional[str] = Query(None, description="Payment method: credit_card, paypal, etc."),
    transaction_id: Optional[str] = Query(None, description="Payment transaction ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Update payment status for a booking (Admin only).
    """
    booking = InvoiceService.update_payment_status(
        db, booking_id, payment_status, payment_method, transaction_id
    )
    
    return success_response(
        data={
            "booking_id": booking.id,
            "payment_status": booking.payment_status,
            "payment_method": booking.payment_method,
            "transaction_id": booking.payment_transaction_id,
            "paid_at": booking.paid_at
        },
        message=f"Payment status updated to {payment_status}"
    )


@router.post("/generate", response_model=dict)
async def generate_invoice(
    request: InvoiceGenerateRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Generate/regenerate invoice for a booking (Admin only).
    """
    invoice_data = InvoiceService.get_invoice_data(
        db, request.booking_id, request.tax_rate, None, True
    )
    
    # Generate PDF as well
    pdf_response = InvoiceService.generate_pdf_invoice(
        db, request.booking_id, request.tax_rate, None, True
    )
    
    return success_response(
        data={
            "invoice": invoice_data.model_dump(),
            "message": "Invoice generated successfully"
        },
        message="Invoice generated successfully"
    )
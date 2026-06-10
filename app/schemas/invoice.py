from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal


class InvoiceItem(BaseModel):
    """Individual item on invoice"""
    description: str
    quantity: int
    unit_price: float
    total: float


class InvoiceAddress(BaseModel):
    """Billing address information"""
    full_name: str
    email: str
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class InvoiceData(BaseModel):
    """Complete invoice data structure"""
    # Invoice identification
    invoice_number: str
    invoice_date: datetime
    due_date: Optional[datetime] = None
    
    # Booking reference
    booking_id: int
    booking_date: datetime
    
    # Event details
    event_id: int
    event_title: str
    event_date: datetime
    event_location: str
    event_image_url: Optional[str] = None
    
    # Customer information
    customer: InvoiceAddress
    
    # Financial details
    subtotal: float
    tax_rate: float
    tax_amount: float
    total_amount: float
    currency: str = "USD"
    
    # Payment information
    payment_status: str
    payment_method: Optional[str] = None
    payment_date: Optional[datetime] = None
    transaction_id: Optional[str] = None
    
    # Items
    items: List[InvoiceItem]
    
    # Additional info
    notes: Optional[str] = None
    terms: Optional[str] = None
    qr_code_url: Optional[str] = None


class InvoiceResponse(BaseModel):
    """Response for invoice endpoints"""
    success: bool
    data: InvoiceData
    message: str


class InvoiceGenerateRequest(BaseModel):
    """Request to generate invoice"""
    booking_id: int
    tax_rate: float = Field(0.0, ge=0, le=100, description="Tax rate percentage")
    notes: Optional[str] = None
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.core.enums import PaymentStatus, PaymentMethod


class PaymentInitiateRequest(BaseModel):
    booking_id: int = Field(..., description="Booking ID to pay for")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    return_url: Optional[str] = Field(None, description="URL to redirect after payment")


class PaymentSimulateWebhookRequest(BaseModel):
    payment_id: int = Field(..., description="Payment ID")
    success: bool = Field(..., description="Whether payment succeeded")
    gateway_transaction_id: Optional[str] = Field(None, description="Gateway transaction ID")
    failure_reason: Optional[str] = Field(None, description="Reason for failure if not successful")


class PaymentRefundRequest(BaseModel):
    payment_id: int = Field(..., description="Payment ID to refund")
    amount: Optional[float] = Field(None, description="Amount to refund (partial refund), None for full")
    reason: Optional[str] = Field(None, description="Reason for refund")


class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    amount: float
    currency: str
    status: PaymentStatus
    method: Optional[PaymentMethod] = None
    transaction_id: Optional[str] = None
    gateway_transaction_id: Optional[str] = None
    failure_reason: Optional[str] = None
    initiated_at: datetime
    processed_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentInitiateResponse(BaseModel):
    payment: PaymentResponse
    payment_url: Optional[str] = None
    message: str


class PaymentSimulateResponse(BaseModel):
    payment: PaymentResponse
    booking_payment_status: PaymentStatus
    message: str


class PaymentListResponse(BaseModel):
    payments: list[PaymentResponse]
    total: int
    page: int
    limit: int
    total_pages: int
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.payment import (
    PaymentInitiateRequest, PaymentSimulateWebhookRequest, PaymentRefundRequest,
    PaymentResponse, PaymentInitiateResponse, PaymentSimulateResponse,
    PaymentListResponse
)
from app.services.payment_service import PaymentService
from app.utils.response import success_response, paginated_response

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/initiate", response_model=dict, status_code=status.HTTP_201_CREATED)
async def initiate_payment(
    request: PaymentInitiateRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Initiate payment for a booking.
    Creates a payment record and returns payment URL for redirection.
    """
    payment, payment_url = PaymentService.initiate_payment(
        db=db,
        user_id=current_user.id,
        booking_id=request.booking_id,
        payment_method=request.payment_method,
        return_url=request.return_url
    )

    return success_response(
        data={
            "payment": PaymentResponse.model_validate(payment).model_dump(),
            "payment_url": payment_url,
            "message": "Payment initiated successfully"
        },
        message="Payment initiated successfully",
        status_code=status.HTTP_201_CREATED
    )


@router.post("/simulate", response_model=dict)
async def simulate_payment(
    request: PaymentSimulateWebhookRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Simulate payment webhook (success/failure).
    This simulates a payment gateway callback.
    """
    payment, booking_payment_status = PaymentService.simulate_payment_webhook(
        db=db,
        user_id=current_user.id,
        payment_id=request.payment_id,
        success=request.success,
        gateway_transaction_id=request.gateway_transaction_id,
        failure_reason=request.failure_reason
    )

    return success_response(
        data={
            "payment": PaymentResponse.model_validate(payment).model_dump(),
            "booking_payment_status": booking_payment_status,
            "message": "Payment simulated successfully"
        },
        message="Payment simulated successfully"
    )


@router.post("/{payment_id}/refund", response_model=dict)
async def request_refund(
    payment_id: int,
    request: PaymentRefundRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Request a refund for a payment.
    Can be full or partial refund.
    """
    payment = PaymentService.process_refund(
        db=db,
        user_id=current_user.id,
        payment_id=payment_id,
        amount=request.amount,
        reason=request.reason
    )

    return success_response(
        data=PaymentResponse.model_validate(payment).model_dump(),
        message="Refund processed successfully"
    )


@router.get("/{payment_id}", response_model=dict)
async def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get payment details by ID.
    Users can only view their own payments.
    """
    payment = PaymentService.get_payment_by_id(db, payment_id, current_user.id)

    return success_response(
        data=PaymentResponse.model_validate(payment).model_dump(),
        message="Payment retrieved successfully"
    )


@router.get("/booking/{booking_id}", response_model=dict)
async def get_payments_by_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all payments for a specific booking.
    Users can only view payments for their own bookings.
    """
    payments = PaymentService.get_payments_by_booking(db, booking_id, current_user.id)

    return success_response(
        data=[PaymentResponse.model_validate(p).model_dump() for p in payments],
        message="Payments retrieved successfully"
    )


@router.get("/", response_model=dict)
async def get_my_payments(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    status: Optional[str] = Query(None, description="Filter by payment status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's payments with pagination and optional status filter.
    """
    payments, total = PaymentService.get_user_payments(
        db=db,
        user_id=current_user.id,
        page=page,
        limit=limit,
        status=status
    )

    total_pages = (total + limit - 1) // limit if total > 0 else 0

    return paginated_response(
        items=[PaymentResponse.model_validate(p).model_dump() for p in payments],
        total=total,
        page=page,
        limit=limit,
        message="Payments retrieved successfully"
    )

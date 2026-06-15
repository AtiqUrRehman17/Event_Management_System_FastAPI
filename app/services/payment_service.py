from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Tuple, Optional
from datetime import datetime
import secrets
import logging
from fastapi import HTTPException, status
from app.models.payment import Payment
from app.models.booking import Booking
from app.models.event import Event
from app.core.enums import PaymentStatus, PaymentMethod, BookingStatus, EventStatus
from app.core.exceptions import (
    BookingNotFoundException,
    PaymentNotFoundException,
    PermissionDeniedException
)
from app.utils.datetime_utils import get_current_utc
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.models.audit_log import AuditActionType, AuditActionCategory
from app.models.notification import NotificationType

logger = logging.getLogger(__name__)


class PaymentService:

    @staticmethod
    def _generate_transaction_id() -> str:
        """Generate unique transaction ID"""
        return f"txn_{secrets.token_urlsafe(16)}"

    @staticmethod
    def _generate_payment_url(payment_id: int, transaction_id: str) -> str:
        """Generate payment URL for simulation"""
        return f"/api/v1/payments/simulate?payment_id={payment_id}&transaction_id={transaction_id}"

    @staticmethod
    def initiate_payment(
        db: Session,
        user_id: int,
        booking_id: int,
        payment_method: PaymentMethod,
        return_url: Optional[str] = None
    ) -> Tuple[Payment, str]:
        """
        Initiate payment for a booking.
        Creates a payment record with PENDING status.
        """
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise BookingNotFoundException()

        if booking.user_id != user_id:
            raise PermissionDeniedException()

        event = booking.event
        if not event or event.status != EventStatus.UPCOMING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot pay for this event"
            )

        if booking.status != BookingStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot pay for cancelled booking"
            )

        existing_payment = db.query(Payment).filter(
            Payment.booking_id == booking_id,
            Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.PROCESSING, PaymentStatus.PAID])
        ).first()

        if existing_payment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment already exists for this booking"
            )

        transaction_id = PaymentService._generate_transaction_id()
        payment_url = PaymentService._generate_payment_url(existing_payment.id if existing_payment else 0, transaction_id)

        payment = Payment(
            booking_id=booking_id,
            amount=round(booking.total_price, 2),
            currency="USD",
            status=PaymentStatus.PENDING,
            method=payment_method,
            transaction_id=transaction_id,
            initiated_at=get_current_utc()
        )

        db.add(payment)
        db.commit()
        db.refresh(payment)

        payment_url = PaymentService._generate_payment_url(payment.id, transaction_id)

        AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditActionType.PAYMENT_CREATE,
            category=AuditActionCategory.PAYMENT,
            entity_type="payment",
            entity_id=payment.id,
            new_value={
                "booking_id": booking_id,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "method": payment.method.value if payment.method else None,
                "status": payment.status.value
            }
        )

        logger.info(f"Payment initiated: Payment {payment.id} for Booking {booking_id} by User {user_id}")

        return payment, payment_url

    @staticmethod
    def simulate_payment_webhook(
        db: Session,
        user_id: int,
        payment_id: int,
        success: bool,
        gateway_transaction_id: Optional[str] = None,
        failure_reason: Optional[str] = None
    ) -> Tuple[Payment, PaymentStatus]:
        """
        Simulate payment gateway webhook callback.
        Updates payment status and triggers notifications.
        """
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise PaymentNotFoundException()

        booking = db.query(Booking).filter(Booking.id == payment.booking_id).first()
        if not booking:
            raise BookingNotFoundException()

        if booking.user_id != user_id:
            raise PermissionDeniedException()

        if payment.status == PaymentStatus.PAID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment already completed"
            )

        old_status = payment.status

        if success:
            payment.status = PaymentStatus.PAID
            payment.processed_at = get_current_utc()
            payment.gateway_transaction_id = gateway_transaction_id or PaymentService._generate_transaction_id()

            booking.payment_status = PaymentStatus.PAID
            booking.payment_method = payment.method
            booking.payment_transaction_id = payment.gateway_transaction_id
            booking.paid_at = get_current_utc()

            NotificationService.create_notification(
                db=db,
                user_id=user_id,
                notification_type=NotificationType.PAYMENT_SUCCESSFUL,
                title="Payment Successful",
                message=f"Your payment of ${payment.amount:.2f} for booking #{booking.id} has been confirmed.",
                channel=NotificationType.PAYMENT_SUCCESSFUL,
                extra_data={"payment_id": payment.id, "booking_id": booking.id}
            )
        else:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = failure_reason or "Payment failed"
            payment.gateway_transaction_id = gateway_transaction_id

            booking.payment_status = PaymentStatus.FAILED

            NotificationService.create_notification(
                db=db,
                user_id=user_id,
                notification_type=NotificationType.PAYMENT_FAILED,
                title="Payment Failed",
                message=f"Your payment of ${payment.amount:.2f} for booking #{booking.id} has failed. Reason: {failure_reason or 'Unknown'}",
                channel=NotificationType.PAYMENT_FAILED,
                extra_data={"payment_id": payment.id, "booking_id": booking.id}
            )

        payment.updated_at = get_current_utc()
        db.commit()
        db.refresh(payment)

        AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditActionType.PAYMENT_UPDATE,
            category=AuditActionCategory.PAYMENT,
            entity_type="payment",
            entity_id=payment.id,
            old_value={"status": old_status.value},
            new_value={
                "status": payment.status.value,
                "gateway_transaction_id": payment.gateway_transaction_id,
                "failure_reason": payment.failure_reason
            }
        )

        logger.info(f"Payment simulated: Payment {payment_id} -> {payment.status.value} by User {user_id}")

        return payment, booking.payment_status

    @staticmethod
    def process_refund(
        db: Session,
        user_id: int,
        payment_id: int,
        amount: Optional[float] = None,
        reason: Optional[str] = None
    ) -> Payment:
        """
        Process refund for a payment.
        Can be full or partial refund.
        """
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise PaymentNotFoundException()

        booking = db.query(Booking).filter(Booking.id == payment.booking_id).first()
        if not booking:
            raise BookingNotFoundException()

        if booking.user_id != user_id:
            raise PermissionDeniedException()

        if payment.status != PaymentStatus.PAID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only refund paid payments"
            )

        if payment.refunded_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment already refunded"
            )

        refund_amount = amount if amount is not None else payment.amount
        if refund_amount > payment.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refund amount cannot exceed payment amount"
            )

        old_status = payment.status

        if refund_amount >= payment.amount:
            payment.status = PaymentStatus.REFUNDED
            booking.payment_status = PaymentStatus.REFUNDED
        else:
            payment.status = PaymentStatus.PARTIALLY_REFUNDED
            booking.payment_status = PaymentStatus.PARTIALLY_REFUNDED

        payment.refunded_at = get_current_utc()
        payment.failure_reason = reason
        payment.updated_at = get_current_utc()

        db.commit()
        db.refresh(payment)

        AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditActionType.PAYMENT_REFUND,
            category=AuditActionCategory.PAYMENT,
            entity_type="payment",
            entity_id=payment.id,
            old_value={"status": old_status.value},
            new_value={
                "status": payment.status.value,
                "refund_amount": refund_amount,
                "reason": reason
            }
        )

        logger.info(f"Refund processed: Payment {payment_id} -> {payment.status.value} by User {user_id}")

        return payment

    @staticmethod
    def get_payment_by_id(db: Session, payment_id: int, user_id: Optional[int] = None) -> Payment:
        """Get payment by ID with optional user ownership check"""
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise PaymentNotFoundException()

        if user_id is not None:
            booking = db.query(Booking).filter(Booking.id == payment.booking_id).first()
            if booking and booking.user_id != user_id:
                raise PermissionDeniedException()

        return payment

    @staticmethod
    def get_payments_by_booking(db: Session, booking_id: int, user_id: Optional[int] = None) -> List[Payment]:
        """Get all payments for a booking"""
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise BookingNotFoundException()

        if user_id is not None and booking.user_id != user_id:
            raise PermissionDeniedException()

        return db.query(Payment).filter(Payment.booking_id == booking_id).order_by(Payment.created_at.desc()).all()

    @staticmethod
    def get_user_payments(
        db: Session,
        user_id: int,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None
    ) -> Tuple[List[Payment], int]:
        """Get user's payments with pagination and optional status filter"""
        query = db.query(Payment).join(Booking).filter(Booking.user_id == user_id)

        if status:
            try:
                payment_status = PaymentStatus(status)
                query = query.filter(Payment.status == payment_status)
            except ValueError:
                pass

        total = query.count()
        offset = (page - 1) * limit
        payments = query.order_by(Payment.created_at.desc()).offset(offset).limit(limit).all()

        return payments, total

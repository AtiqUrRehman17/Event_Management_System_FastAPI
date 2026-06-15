from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import PaymentStatus, PaymentMethod
from app.utils.datetime_utils import get_current_utc


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    method = Column(SQLEnum(PaymentMethod), nullable=True)
    
    transaction_id = Column(String(255), unique=True, nullable=True, index=True)
    gateway_transaction_id = Column(String(255), nullable=True)
    gateway_response = Column(Text, nullable=True)
    
    failure_reason = Column(String(500), nullable=True)
    
    initiated_at = Column(DateTime, default=get_current_utc, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=get_current_utc, nullable=False)
    updated_at = Column(DateTime, default=get_current_utc, onupdate=get_current_utc, nullable=False)

    booking = relationship("Booking", backref="payments")

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, booking_id={self.booking_id}, amount={self.amount}, status={self.status})>"
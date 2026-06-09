from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import BookingStatus
from app.utils.datetime_utils import get_current_utc


class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    number_of_seats = Column(Integer, nullable=False)
    total_price = Column(Integer, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.ACTIVE, nullable=False, index=True)
    booking_date = Column(DateTime, default=get_current_utc, nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_current_utc, nullable=False)
    updated_at = Column(DateTime, default=get_current_utc, onupdate=get_current_utc, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="bookings")
    event = relationship("Event", back_populates="bookings")
    
    def __repr__(self) -> str:
        return f"<Booking(id={self.id}, user_id={self.user_id}, event_id={self.event_id}, seats={self.number_of_seats}, status={self.status})>"
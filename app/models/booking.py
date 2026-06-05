from datetime import datetime,timezone
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum, Integer as SQLInteger
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import BookingStatus


class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    number_of_seats = Column(Integer, nullable=False)
    total_price = Column(Integer, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.ACTIVE, nullable=False, index=True)
    booking_date = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="bookings")
    event = relationship("Event", back_populates="bookings")
    
    def __repr__(self) -> str:
        return f"<Booking(id={self.id}, user_id={self.user_id}, event_id={self.event_id}, seats={self.number_of_seats}, status={self.status})>"
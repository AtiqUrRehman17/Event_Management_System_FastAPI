from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import EventStatus
from app.utils.datetime_utils import get_current_utc


class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=False)
    event_date = Column(DateTime, nullable=False, index=True)
    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    price = Column(Float, nullable=False, default=0.0)
    status = Column(Enum(EventStatus), default=EventStatus.UPCOMING, nullable=False, index=True)
    image_url = Column(String(500), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=get_current_utc, nullable=False)
    updated_at = Column(DateTime, default=get_current_utc, onupdate=get_current_utc, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Soft delete fields
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    category = relationship("Category", back_populates="events")
    bookings = relationship("Booking", back_populates="event", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])
    deleter = relationship("User", foreign_keys=[deleted_by])
    
    def __repr__(self) -> str:
        return f"<Event(id={self.id}, title={self.title}, status={self.status}, available_seats={self.available_seats}, is_deleted={self.is_deleted})>"
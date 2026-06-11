from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.utils.datetime_utils import get_current_utc
import enum


class WaitlistStatus(str, enum.Enum):
    WAITING = "waiting"      # User is waiting for a spot
    NOTIFIED = "notified"    # User has been notified of available spot
    CONFIRMED = "confirmed"  # User confirmed and booked
    EXPIRED = "expired"      # User didn't confirm in time
    CANCELLED = "cancelled"  # User left the waitlist


class Waitlist(Base):
    __tablename__ = "waitlist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False)
    status = Column(SQLEnum(WaitlistStatus), default=WaitlistStatus.WAITING, nullable=False)
    joined_at = Column(DateTime, default=get_current_utc, nullable=False)
    notified_at = Column(DateTime, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # When the notification expires
    
    # Relationships
    user = relationship("User", backref="waitlist_entries")
    event = relationship("Event", backref="waitlist_entries")
    
    def __repr__(self) -> str:
        return f"<Waitlist(id={self.id}, user_id={self.user_id}, event_id={self.event_id}, position={self.position}, status={self.status})>"
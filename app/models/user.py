from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import UserRole


def get_utc_now():
    """Return current UTC datetime"""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # For email verification
    
    # New profile fields
    phone = Column(String(20), nullable=True)
    bio = Column(Text, nullable=True)
    timezone = Column(String(50), nullable=True, default="UTC")
    profile_picture = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationships
    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email}, role={self.role})>"
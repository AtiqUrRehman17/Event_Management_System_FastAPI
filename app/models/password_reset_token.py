from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.utils.datetime_utils import get_current_utc


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=get_current_utc, nullable=False)

    # Use back_populates to match User model
    user = relationship("User", back_populates="password_reset_tokens")

    @property
    def is_expired(self) -> bool:
        """Check if token has expired"""
        return get_current_utc() > self.expires_at

    def __repr__(self) -> str:
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base
from app.utils.datetime_utils import get_current_utc


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    blacklisted_at = Column(DateTime, default=get_current_utc, nullable=False)

    def __repr__(self) -> str:
        return f"<TokenBlacklist(id={self.id}, expires_at={self.expires_at})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the blacklisted token itself has expired"""
        return get_current_utc() > self.expires_at
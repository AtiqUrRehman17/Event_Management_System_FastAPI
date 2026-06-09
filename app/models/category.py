from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.utils.datetime_utils import get_current_utc


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_current_utc, nullable=False)
    updated_at = Column(DateTime, default=get_current_utc, onupdate=get_current_utc, nullable=False)
    
    # Relationships
    events = relationship("Event", back_populates="category")
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name})>"
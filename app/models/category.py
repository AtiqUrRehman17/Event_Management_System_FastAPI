from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.utils.datetime_utils import get_current_utc


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Phase 1 fields
    icon = Column(String(50), nullable=True, default="fa-tag")
    color = Column(String(7), nullable=True, default="#3498db")
    
    # Phase 2 fields
    image_url = Column(String(500), nullable=True, default=None)
    
    # Phase 4 fields - Hierarchical categories
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    level = Column(Integer, default=0, nullable=False)  # 0 = root, 1 = child, 2 = grandchild, etc.
    path = Column(String(255), nullable=True)  # Store hierarchy path like "1/5/12" for quick queries
    
    created_at = Column(DateTime, default=get_current_utc, nullable=False)
    updated_at = Column(DateTime, default=get_current_utc, onupdate=get_current_utc, nullable=False)
    
    # Relationships
    events = relationship("Event", back_populates="category")
    
    # Self-referential relationship for hierarchy
    parent = relationship("Category", remote_side=[id], backref="children", foreign_keys=[parent_id])
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name}, level={self.level}, parent_id={self.parent_id})>"
    
    @property
    def is_parent(self) -> bool:
        """Check if category has children"""
        return len(self.children) > 0
    
    @property
    def has_parent(self) -> bool:
        """Check if category has a parent"""
        return self.parent_id is not None
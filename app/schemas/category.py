from pydantic import BaseModel, Field, field_validator, HttpUrl
from datetime import datetime
from typing import Optional, List
import re


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    icon: Optional[str] = Field(default="fa-tag", max_length=50, description="Font Awesome icon class")
    color: Optional[str] = Field(default="#3498db", pattern=r'^#([A-Fa-f0-9]{6})$', description="Hex color code")
    image_url: Optional[str] = Field(None, max_length=500, description="URL to category image")
    
    # Phase 4: Hierarchical fields
    parent_id: Optional[int] = Field(None, description="Parent category ID for hierarchical organization")
    
    @field_validator('color')
    def validate_color(cls, v):
        if v and not re.match(r'^#([A-Fa-f0-9]{6})$', v):
            raise ValueError('Color must be a valid hex code (e.g., #3498db)')
        return v
    
    @field_validator('icon')
    def validate_icon(cls, v):
        if v and len(v) > 50:
            raise ValueError('Icon name too long (max 50 characters)')
        return v
    
    @field_validator('image_url')
    def validate_image_url(cls, v):
        if v and len(v) > 500:
            raise ValueError('Image URL too long (max 500 characters)')
        return v
    
    @field_validator('parent_id')
    def validate_parent_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError('parent_id must be a positive integer or null')
        return v


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, pattern=r'^#([A-Fa-f0-9]{6})$')
    image_url: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[int] = Field(None, description="Parent category ID")
    
    @field_validator('color')
    def validate_color(cls, v):
        if v and not re.match(r'^#([A-Fa-f0-9]{6})$', v):
            raise ValueError('Color must be a valid hex code (e.g., #3498db)')
        return v
    
    @field_validator('image_url')
    def validate_image_url(cls, v):
        if v and len(v) > 500:
            raise ValueError('Image URL too long (max 500 characters)')
        return v


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    icon: Optional[str] = "fa-tag"
    color: Optional[str] = "#3498db"
    image_url: Optional[str] = None
    parent_id: Optional[int] = None
    level: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CategoryTreeNode(CategoryResponse):
    """Category response with children for tree structure"""
    children: List['CategoryTreeNode'] = []
    events_count: int = 0
    total_bookings: int = 0


class CategoryListResponse(BaseModel):
    categories: list[CategoryResponse]
    total: int


class CategoryTreeResponse(BaseModel):
    """Response for category tree/hierarchy"""
    id: int
    name: str
    icon: Optional[str]
    color: Optional[str]
    image_url: Optional[str]
    level: int
    children: List['CategoryTreeResponse']
    events_count: int = 0
    total_bookings: int = 0


class CategoryBreadcrumbResponse(BaseModel):
    """Breadcrumb navigation for a category"""
    id: int
    name: str
    slug: Optional[str] = None


class PopularCategoryResponse(BaseModel):
    """Response for popular categories on dashboard"""
    id: int
    name: str
    icon: Optional[str] = "fa-tag"
    color: Optional[str] = "#3498db"
    image_url: Optional[str] = None
    events_count: int
    total_bookings: int = 0
    total_seats_booked: int = 0
    revenue: float = 0.0
    parent_name: Optional[str] = None


class CategoryStatsResponse(BaseModel):
    """Detailed stats for a category including children"""
    id: int
    name: str
    icon: Optional[str]
    color: Optional[str]
    image_url: Optional[str]
    parent_id: Optional[int]
    parent_name: Optional[str]
    level: int
    total_events: int
    upcoming_events: int
    completed_events: int
    total_bookings: int
    total_seats_booked: int
    total_revenue: float
    children_count: int


# Forward reference for recursive models
CategoryTreeNode.model_rebuild()
CategoryTreeResponse.model_rebuild()
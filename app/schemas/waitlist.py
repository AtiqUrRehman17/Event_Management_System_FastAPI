from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class WaitlistStatusEnum(str, Enum):
    WAITING = "waiting"
    NOTIFIED = "notified"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class JoinWaitlistRequest(BaseModel):
    """Request to join waitlist"""
    event_id: int


class WaitlistResponse(BaseModel):
    """Waitlist entry response"""
    id: int
    user_id: int
    event_id: int
    event_title: Optional[str] = None
    position: int
    status: WaitlistStatusEnum
    joined_at: datetime
    notified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    ahead_count: int = 0  # Number of people ahead in waitlist
    
    class Config:
        from_attributes = True


class WaitlistPositionResponse(BaseModel):
    """User's position in waitlist"""
    position: int
    total_waiting: int
    status: WaitlistStatusEnum
    estimated_chance: str  # e.g., "High", "Medium", "Low"
    message: str


class WaitlistSummaryResponse(BaseModel):
    """Event waitlist summary"""
    event_id: int
    event_title: str
    total_waiting: int
    total_notified: int
    total_confirmed: int
    total_expired: int
    your_position: Optional[int] = None
    your_status: Optional[WaitlistStatusEnum] = None


class WaitlistAdminResponse(BaseModel):
    """Admin view of waitlist"""
    entries: list[WaitlistResponse]
    total: int
    page: int
    limit: int
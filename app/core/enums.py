from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class EventStatus(str, Enum):
    UPCOMING = "upcoming"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BookingStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
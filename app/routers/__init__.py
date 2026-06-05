from .auth import router as auth_router
from .users import router as users_router
from .categories import router as categories_router
from .events import router as events_router
from .bookings import router as bookings_router

__all__ = [
    "auth_router",
    "users_router",
    "categories_router",
    "events_router",
    "bookings_router",
]
from .auth import router as auth_router
from .users import router as users_router
from .categories import router as categories_router
from .events import router as events_router
from .bookings import router as bookings_router
from .oauth import router as oauth_router
from .invoice import router as invoice_router
from .waitlist import router as waitlist_router
from .notifications import router as notifications_router
from .admin import router as admin_router
from .audit import router as audit_router
from .upload import router as upload_router

__all__ = [
    "auth_router",
    "users_router",
    "categories_router",
    "events_router",
    "bookings_router",
    "oauth_router",
    "invoice_router",
    "waitlist_router",
    "notifications_router",
    "admin_router",
    "audit_router",
    "upload_router",
]
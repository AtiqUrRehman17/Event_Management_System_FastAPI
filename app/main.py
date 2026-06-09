import warnings
warnings.filterwarnings("ignore")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

from app.core import settings
from app.core.database import engine, Base, SessionLocal
from app.core.seed import seed_admin
from app.routers import (
    auth_router,
    users_router,
    categories_router,
    events_router,
    bookings_router
)
from app.routers.oauth import router as oauth_router  # Add this import
from app.utils import register_error_handlers
from app.services.event_service import EventService
from app.services.auth_service import AuthService
from app.models.email_verification_token import EmailVerificationToken
from datetime import timedelta
from app.utils.datetime_utils import get_current_utc

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)


def run_event_status_update():
    """Scheduler job: auto-update event statuses every hour"""
    db = SessionLocal()
    try:
        count = EventService.update_event_status(db)
        if count > 0:
            logger.info(f"Scheduler: {count} event(s) marked as COMPLETED")
    except Exception as e:
        logger.error(f"Scheduler: Event status update failed - {str(e)}")
    finally:
        db.close()


def run_cleanup_expired_tokens():
    """Scheduler job: clean up expired blacklisted tokens every 24 hours"""
    db = SessionLocal()
    try:
        count = AuthService.cleanup_expired_tokens(db)
        if count > 0:
            logger.info(f"Scheduler: Cleaned up {count} expired blacklisted token(s)")
    except Exception as e:
        logger.error(f"Scheduler: Token cleanup failed - {str(e)}")
    finally:
        db.close()


def run_cleanup_reset_tokens():
    """Scheduler job: clean up expired reset tokens every 12 hours"""
    db = SessionLocal()
    try:
        count = AuthService.cleanup_expired_reset_tokens(db)
        if count > 0:
            logger.info(f"Scheduler: Cleaned up {count} expired/used reset token(s)")
    except Exception as e:
        logger.error(f"Scheduler: Reset token cleanup failed - {str(e)}")
    finally:
        db.close()


def run_cleanup_verification_tokens():
    """Scheduler job: clean up expired verification tokens every 24 hours"""
    db = SessionLocal()
    try:
        now = get_current_utc()
        expired = db.query(EmailVerificationToken).filter(
            EmailVerificationToken.expires_at < now
        ).all()
        
        one_day_ago = now - timedelta(hours=24)
        used_old = db.query(EmailVerificationToken).filter(
            EmailVerificationToken.is_used == True,
            EmailVerificationToken.created_at < one_day_ago
        ).all()
        
        total = len(expired) + len(used_old)
        
        for token in expired + used_old:
            db.delete(token)
        
        if total > 0:
            db.commit()
            logger.info(f"Scheduler: Cleaned up {total} expired/used verification token(s)")
    except Exception as e:
        logger.error(f"Scheduler: Verification token cleanup failed - {str(e)}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Event Management System...")

    db = SessionLocal()
    try:
        seed_admin(db)
    finally:
        db.close()

    logger.info("Running initial event status update...")
    run_event_status_update()

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_event_status_update,
        trigger=IntervalTrigger(hours=1),
        id="event_status_update",
        replace_existing=True
    )
    scheduler.add_job(
        run_cleanup_expired_tokens,
        trigger=IntervalTrigger(hours=24),
        id="cleanup_expired_tokens",
        replace_existing=True
    )
    scheduler.add_job(
        run_cleanup_reset_tokens,
        trigger=IntervalTrigger(hours=12),
        id="cleanup_reset_tokens",
        replace_existing=True
    )
    scheduler.add_job(
        run_cleanup_verification_tokens,
        trigger=IntervalTrigger(hours=24),
        id="cleanup_verification_tokens",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started with 4 jobs")
    logger.info("Event Management System is ready!")

    yield

    logger.info("Shutting down scheduler...")
    scheduler.shutdown(wait=False)
    logger.info("Application shutdown complete.")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    swagger_ui_parameters={
        "persistAuthorization": False,
    }
)

# Register error handlers
register_error_handlers(app)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description="Event Management System API - Login first to access protected endpoints",
        routes=app.routes,
    )

    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Login via /api/v1/auth/login to get token. Then enter token here."
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}


# Include routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(oauth_router, prefix=settings.API_PREFIX)  # Add OAuth router
app.include_router(users_router, prefix=settings.API_PREFIX)
app.include_router(categories_router, prefix=settings.API_PREFIX)
app.include_router(events_router, prefix=settings.API_PREFIX)
app.include_router(bookings_router, prefix=settings.API_PREFIX)

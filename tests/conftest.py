# conftest.py (root level)
import os
import pytest
from dotenv import load_dotenv

# ── Load test environment FIRST before any app imports ──
load_dotenv(".env.test", override=True)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.dependencies.db import get_db
from app.main import app
from app.core.config import settings
from app.core.enums import UserRole, EventStatus, BookingStatus
from app.utils.auth_utils import hash_password
from app.core.security import Security
from datetime import datetime, timedelta


# ================================================================
# TEST DATABASE SETUP
# ================================================================

# Use in-memory SQLite for tests (fast, isolated)
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Same connection for all threads (required for in-memory SQLite)
)

TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


def override_get_db():
    """Override get_db dependency to use test database"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================================================================
# TEST CLIENT SETUP
# ================================================================

@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine and tables once per session"""
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db(db_engine):
    """
    Provide a clean database session for each test.
    Rolls back all changes after each test (isolation).
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    """
    Provide test client with overridden database dependency.
    Each test gets a fresh client with clean database.
    """
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ================================================================
# USER FIXTURES
# ================================================================

@pytest.fixture(scope="function")
def test_user_data():
    """Raw data for creating a test user"""
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "TestPass@123",
        "first_name": "Test",
        "last_name": "User"
    }


@pytest.fixture(scope="function")
def test_admin_data():
    """Raw data for creating a test admin"""
    return {
        "username": "testadmin",
        "email": "testadmin@example.com",
        "password": "TestAdmin@123",
        "first_name": "Test",
        "last_name": "Admin"
    }


@pytest.fixture(scope="function")
def test_user(db):
    """
    Create a test user directly in the database.
    Returns the User model instance.
    """
    from app.models.user import User

    user = User(
        username="testuser",
        email="testuser@example.com",
        password_hash=hash_password("TestPass@123"),
        first_name="Test",
        last_name="User",
        role=UserRole.USER,
        is_active=True,
        is_verified=True,  # Pre-verified for easy testing
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_admin(db):
    """
    Create a test admin directly in the database.
    Returns the User model instance.
    """
    from app.models.user import User

    admin = User(
        username="testadmin",
        email="testadmin@example.com",
        password_hash=hash_password("TestAdmin@123"),
        first_name="Test",
        last_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture(scope="function")
def inactive_user(db):
    """Create an inactive test user"""
    from app.models.user import User

    user = User(
        username="inactiveuser",
        email="inactive@example.com",
        password_hash=hash_password("TestPass@123"),
        first_name="Inactive",
        last_name="User",
        role=UserRole.USER,
        is_active=False,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def unverified_user(db):
    """Create an unverified test user"""
    from app.models.user import User

    user = User(
        username="unverifieduser",
        email="unverified@example.com",
        password_hash=hash_password("TestPass@123"),
        first_name="Unverified",
        last_name="User",
        role=UserRole.USER,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ================================================================
# TOKEN FIXTURES
# ================================================================

@pytest.fixture(scope="function")
def user_token(test_user):
    """Generate a valid JWT access token for test user"""
    user_info = {
        "username": test_user.username,
        "email": test_user.email,
        "role": test_user.role.value
    }
    token = Security.create_access_token(
        data={"sub": str(test_user.id)},
        user_info=user_info
    )
    return token


@pytest.fixture(scope="function")
def admin_token(test_admin):
    """Generate a valid JWT access token for test admin"""
    user_info = {
        "username": test_admin.username,
        "email": test_admin.email,
        "role": test_admin.role.value
    }
    token = Security.create_access_token(
        data={"sub": str(test_admin.id)},
        user_info=user_info
    )
    return token


@pytest.fixture(scope="function")
def user_refresh_token(test_user):
    """Generate a valid JWT refresh token for test user"""
    user_info = {
        "username": test_user.username,
        "email": test_user.email,
        "role": test_user.role.value
    }
    token = Security.create_refresh_token(
        data={"sub": str(test_user.id)},
        user_info=user_info
    )
    return token


@pytest.fixture(scope="function")
def user_auth_headers(user_token):
    """Authorization headers for test user"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(scope="function")
def admin_auth_headers(admin_token):
    """Authorization headers for test admin"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="function")
def expired_token(test_user):
    """Generate an expired JWT token for testing"""
    user_info = {
        "username": test_user.username,
        "email": test_user.email,
        "role": test_user.role.value
    }
    token = Security.create_access_token(
        data={"sub": str(test_user.id)},
        user_info=user_info,
        expires_delta=timedelta(seconds=-1)  # Already expired
    )
    return token


# ================================================================
# CATEGORY FIXTURES
# ================================================================

@pytest.fixture(scope="function")
def test_category(db):
    """Create a test category"""
    from app.models.category import Category

    category = Category(
        name="Test Category",
        description="A test category",
        icon="fa-test",
        color="#3498db",
        is_active=True,
        level=0
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@pytest.fixture(scope="function")
def test_child_category(db, test_category):
    """Create a test child category"""
    from app.models.category import Category

    child = Category(
        name="Test Child Category",
        description="A test child category",
        icon="fa-child",
        color="#2ecc71",
        is_active=True,
        parent_id=test_category.id,
        level=1,
        path=f"{test_category.id}"
    )
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


# ================================================================
# EVENT FIXTURES
# ================================================================

@pytest.fixture(scope="function")
def test_event(db, test_admin, test_category):
    """Create a test event"""
    from app.models.event import Event

    event = Event(
        title="Test Event",
        description="A test event description",
        location="Test Location, Test City",
        event_date=datetime.utcnow() + timedelta(days=30),
        total_seats=100,
        available_seats=100,
        price=50.00,
        status=EventStatus.UPCOMING,
        category_id=test_category.id,
        created_by=test_admin.id,
        is_deleted=False
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture(scope="function")
def test_event_sold_out(db, test_admin, test_category):
    """Create a sold out test event"""
    from app.models.event import Event

    event = Event(
        title="Sold Out Event",
        description="A sold out event",
        location="Test Location",
        event_date=datetime.utcnow() + timedelta(days=30),
        total_seats=10,
        available_seats=0,  # Sold out
        price=50.00,
        status=EventStatus.UPCOMING,
        category_id=test_category.id,
        created_by=test_admin.id,
        is_deleted=False
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture(scope="function")
def test_event_free(db, test_admin, test_category):
    """Create a free test event"""
    from app.models.event import Event

    event = Event(
        title="Free Test Event",
        description="A free test event",
        location="Online",
        event_date=datetime.utcnow() + timedelta(days=15),
        total_seats=50,
        available_seats=50,
        price=0.00,
        status=EventStatus.UPCOMING,
        category_id=test_category.id,
        created_by=test_admin.id,
        is_deleted=False
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture(scope="function")
def test_event_cancelled(db, test_admin, test_category):
    """Create a cancelled test event"""
    from app.models.event import Event

    event = Event(
        title="Cancelled Event",
        description="A cancelled event",
        location="Test Location",
        event_date=datetime.utcnow() + timedelta(days=10),
        total_seats=100,
        available_seats=100,
        price=50.00,
        status=EventStatus.CANCELLED,
        category_id=test_category.id,
        created_by=test_admin.id,
        is_deleted=False
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture(scope="function")
def test_event_completed(db, test_admin, test_category):
    """Create a completed test event"""
    from app.models.event import Event

    event = Event(
        title="Completed Event",
        description="A completed event",
        location="Test Location",
        event_date=datetime.utcnow() - timedelta(days=5),  # Past date
        total_seats=100,
        available_seats=80,
        price=50.00,
        status=EventStatus.COMPLETED,
        category_id=test_category.id,
        created_by=test_admin.id,
        is_deleted=False
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture(scope="function")
def test_deleted_event(db, test_admin, test_category):
    """Create a soft-deleted test event"""
    from app.models.event import Event

    event = Event(
        title="Deleted Event",
        description="A soft deleted event",
        location="Test Location",
        event_date=datetime.utcnow() + timedelta(days=20),
        total_seats=100,
        available_seats=100,
        price=50.00,
        status=EventStatus.CANCELLED,
        category_id=test_category.id,
        created_by=test_admin.id,
        is_deleted=True,
        deleted_at=datetime.utcnow(),
        deleted_by=test_admin.id
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


# ================================================================
# BOOKING FIXTURES
# ================================================================

@pytest.fixture(scope="function")
def test_booking(db, test_user, test_event):
    """Create a test booking"""
    from app.models.booking import Booking

    # Reduce available seats
    test_event.available_seats -= 2

    booking = Booking(
        user_id=test_user.id,
        event_id=test_event.id,
        number_of_seats=2,
        total_price=100.00,
        status=BookingStatus.ACTIVE,
        payment_status="pending",
        tax_rate=0.0,
        tax_amount=0.0
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@pytest.fixture(scope="function")
def test_booking_cancelled(db, test_user, test_event):
    """Create a cancelled test booking"""
    from app.models.booking import Booking

    booking = Booking(
        user_id=test_user.id,
        event_id=test_event.id,
        number_of_seats=1,
        total_price=50.00,
        status=BookingStatus.CANCELLED,
        payment_status="refunded",
        cancelled_at=datetime.utcnow(),
        tax_rate=0.0,
        tax_amount=0.0
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


# ================================================================
# WAITLIST FIXTURES
# ================================================================

@pytest.fixture(scope="function")
def test_waitlist_entry(db, test_user, test_event_sold_out):
    """Create a test waitlist entry"""
    from app.models.waitlist import Waitlist, WaitlistStatus

    entry = Waitlist(
        user_id=test_user.id,
        event_id=test_event_sold_out.id,
        position=1,
        status=WaitlistStatus.WAITING,
        joined_at=datetime.utcnow()
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ================================================================
# NOTIFICATION FIXTURES
# ================================================================

@pytest.fixture(scope="function")
def test_notification(db, test_user):
    """Create a test notification"""
    from app.models.notification import (
        Notification, NotificationType,
        NotificationChannel, NotificationStatus
    )

    notification = Notification(
        user_id=test_user.id,
        type=NotificationType.BOOKING_CONFIRMED,
        title="Test Notification",
        message="This is a test notification",
        channel=NotificationChannel.IN_APP,
        status=NotificationStatus.SENT,
        is_read=False
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


@pytest.fixture(scope="function")
def test_notification_preferences(db, test_user):
    """Create test notification preferences"""
    from app.models.notification import NotificationPreference

    prefs = NotificationPreference(
        user_id=test_user.id,
        email_enabled=True,
        sms_enabled=False,
        push_enabled=False,
        in_app_enabled=True
    )
    db.add(prefs)
    db.commit()
    db.refresh(prefs)
    return prefs


# ================================================================
# HELPER FIXTURES
# ================================================================

@pytest.fixture(scope="function")
def api_prefix():
    """Return the API prefix"""
    return settings.API_PREFIX


@pytest.fixture(scope="function")
def auth_url(api_prefix):
    """Return base auth URL"""
    return f"{api_prefix}/auth"


@pytest.fixture(scope="function")
def events_url(api_prefix):
    """Return base events URL"""
    return f"{api_prefix}/events"


@pytest.fixture(scope="function")
def bookings_url(api_prefix):
    """Return base bookings URL"""
    return f"{api_prefix}/bookings"


@pytest.fixture(scope="function")
def users_url(api_prefix):
    """Return base users URL"""
    return f"{api_prefix}/users"


@pytest.fixture(scope="function")
def categories_url(api_prefix):
    """Return base categories URL"""
    return f"{api_prefix}/categories"


@pytest.fixture(scope="function")
def waitlist_url(api_prefix):
    """Return base waitlist URL"""
    return f"{api_prefix}/waitlist"


@pytest.fixture(scope="function")
def notifications_url(api_prefix):
    """Return base notifications URL"""
    return f"{api_prefix}/notifications"


@pytest.fixture(scope="function")
def admin_url(api_prefix):
    """Return base admin URL"""
    return f"{api_prefix}/admin"


@pytest.fixture(scope="function")
def audit_url(api_prefix):
    """Return base audit URL"""
    return f"{api_prefix}/audit"


@pytest.fixture(scope="function")
def invoices_url(api_prefix):
    """Return base invoices URL"""
    return f"{api_prefix}/invoices"
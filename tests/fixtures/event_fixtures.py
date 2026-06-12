# tests/fixtures/event_fixtures.py
from datetime import datetime, timedelta


def get_valid_event_data(category_id: int = None):
    """Valid event creation data"""
    return {
        "title": "Fixture Test Event",
        "description": "A test event created from fixtures",
        "location": "Test City, Test Country",
        "event_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "total_seats": 100,
        "price": 50.00,
        "category_id": category_id
    }


def get_valid_free_event_data(category_id: int = None):
    """Valid free event data"""
    return {
        "title": "Free Fixture Event",
        "description": "A free test event",
        "location": "Online",
        "event_date": (datetime.utcnow() + timedelta(days=15)).isoformat(),
        "total_seats": 200,
        "price": 0.00,
        "category_id": category_id
    }


def get_valid_large_event_data(category_id: int = None):
    """Valid large capacity event data"""
    return {
        "title": "Large Fixture Event",
        "description": "A large capacity test event",
        "location": "Stadium, Test City",
        "event_date": (datetime.utcnow() + timedelta(days=60)).isoformat(),
        "total_seats": 1000,
        "price": 150.00,
        "category_id": category_id
    }


def get_event_data_past_date():
    """Event data with past date (invalid)"""
    return {
        "title": "Past Event",
        "description": "An event in the past",
        "location": "Test Location",
        "event_date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "total_seats": 50,
        "price": 25.00
    }


def get_event_data_missing_title():
    """Event data with missing title (invalid)"""
    return {
        "description": "Missing title event",
        "location": "Test Location",
        "event_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "total_seats": 50,
        "price": 25.00
    }


def get_event_data_missing_location():
    """Event data with missing location (invalid)"""
    return {
        "title": "Missing Location Event",
        "description": "Test description",
        "event_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "total_seats": 50,
        "price": 25.00
    }


def get_event_data_negative_price():
    """Event data with negative price (invalid)"""
    return {
        "title": "Negative Price Event",
        "description": "Test description",
        "location": "Test Location",
        "event_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "total_seats": 50,
        "price": -10.00
    }


def get_event_data_zero_seats():
    """Event data with zero seats (invalid)"""
    return {
        "title": "Zero Seats Event",
        "description": "Test description",
        "location": "Test Location",
        "event_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "total_seats": 0,
        "price": 25.00
    }


def get_event_update_data():
    """Valid event update data"""
    return {
        "title": "Updated Event Title",
        "description": "Updated description",
        "price": 75.00
    }


def get_event_update_location():
    """Event update with new location"""
    return {
        "location": "New Location, New City"
    }


def get_event_update_status_cancelled():
    """Event status update to cancelled"""
    return {
        "status": "cancelled"
    }


def get_event_search_params():
    """Common search parameters"""
    return {
        "page": 1,
        "limit": 10
    }


def get_event_search_with_filters(category_id: int = None):
    """Search parameters with filters"""
    params = {
        "page": 1,
        "limit": 10,
        "min_price": 0,
        "max_price": 200
    }
    if category_id:
        params["category_id"] = category_id
    return params


def get_multiple_events_data(category_id: int = None):
    """List of multiple valid events data"""
    base_date = datetime.utcnow()
    return [
        {
            "title": "Event One",
            "description": "First test event",
            "location": "Location One",
            "event_date": (base_date + timedelta(days=10)).isoformat(),
            "total_seats": 50,
            "price": 25.00,
            "category_id": category_id
        },
        {
            "title": "Event Two",
            "description": "Second test event",
            "location": "Location Two",
            "event_date": (base_date + timedelta(days=20)).isoformat(),
            "total_seats": 100,
            "price": 50.00,
            "category_id": category_id
        },
        {
            "title": "Event Three",
            "description": "Third test event",
            "location": "Location Three",
            "event_date": (base_date + timedelta(days=30)).isoformat(),
            "total_seats": 200,
            "price": 100.00,
            "category_id": category_id
        }
    ]
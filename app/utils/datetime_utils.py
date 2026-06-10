from datetime import datetime, timezone
from typing import Optional


def get_current_utc() -> datetime:
    """
    Get current UTC datetime as timezone-naive.
    This is the ONLY function that should be used for getting current time.
    """
    return datetime.utcnow()


def make_naive(dt: datetime) -> datetime:
    """
    Convert any datetime to timezone-naive.
    """
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def make_aware(dt: datetime, tz: timezone = timezone.utc) -> datetime:
    """
    Convert a timezone-naive datetime to timezone-aware.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt


def get_utc_now() -> datetime:
    """
    Alias for get_current_utc()
    """
    return get_current_utc()
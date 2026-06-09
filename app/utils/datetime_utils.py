from datetime import datetime, timezone
from typing import Optional


def get_current_utc() -> datetime:
    """
    Get current UTC datetime as timezone-naive.
    This is the recommended replacement for deprecated datetime.utcnow()
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def make_naive(dt: datetime) -> datetime:
    """
    Convert a timezone-aware datetime to timezone-naive.
    Useful when storing datetime in SQLite.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def make_aware(dt: datetime, tz: timezone = timezone.utc) -> datetime:
    """
    Convert a timezone-naive datetime to timezone-aware.
    Useful when reading from SQLite.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt


def get_utc_now() -> datetime:
    """
    Alias for get_current_utc()
    """
    return get_current_utc()
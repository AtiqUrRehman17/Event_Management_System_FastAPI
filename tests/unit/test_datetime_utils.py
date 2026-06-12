import pytest
from datetime import datetime, timezone
from app.utils.datetime_utils import (
    get_current_utc,
    make_naive,
    make_aware,
    get_utc_now
)


@pytest.mark.unit
class TestGetCurrentUtc:

    def test_returns_datetime(self):
        """Should return a datetime object"""
        result = get_current_utc()
        assert isinstance(result, datetime)

    def test_returns_naive_datetime(self):
        """Should return timezone-naive datetime"""
        result = get_current_utc()
        assert result.tzinfo is None

    def test_returns_recent_time(self):
        """Should return current time (within 5 seconds)"""
        before = datetime.utcnow()
        result = get_current_utc()
        after = datetime.utcnow()
        assert before <= result <= after


@pytest.mark.unit
class TestMakeNaive:

    def test_removes_timezone_from_aware(self):
        """Should strip timezone from aware datetime"""
        aware_dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = make_naive(aware_dt)
        assert result.tzinfo is None

    def test_keeps_naive_datetime_unchanged(self):
        """Should return naive datetime as-is"""
        naive_dt = datetime(2024, 1, 15, 10, 0, 0)
        result = make_naive(naive_dt)
        assert result.tzinfo is None
        assert result == naive_dt

    def test_preserves_date_values(self):
        """Should preserve the actual date/time values"""
        aware_dt = datetime(2024, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        result = make_naive(aware_dt)
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15
        assert result.hour == 12
        assert result.minute == 30


@pytest.mark.unit
class TestMakeAware:

    def test_adds_timezone_to_naive(self):
        """Should add UTC timezone to naive datetime"""
        naive_dt = datetime(2024, 1, 15, 10, 0, 0)
        result = make_aware(naive_dt)
        assert result.tzinfo is not None

    def test_keeps_aware_datetime_unchanged(self):
        """Should return already aware datetime as-is"""
        aware_dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = make_aware(aware_dt)
        assert result.tzinfo is not None
        assert result == aware_dt

    def test_preserves_date_values(self):
        """Should preserve the actual date/time values"""
        naive_dt = datetime(2024, 6, 15, 12, 30, 0)
        result = make_aware(naive_dt)
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15
        assert result.hour == 12
        assert result.minute == 30


@pytest.mark.unit
class TestGetUtcNow:

    def test_returns_datetime(self):
        """Should return a datetime object"""
        result = get_utc_now()
        assert isinstance(result, datetime)

    def test_same_as_get_current_utc(self):
        """Should return same result as get_current_utc"""
        result1 = get_current_utc()
        result2 = get_utc_now()
        # Both should be very close in time (within 1 second)
        diff = abs((result2 - result1).total_seconds())
        assert diff < 1
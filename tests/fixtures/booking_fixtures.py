# tests/fixtures/booking_fixtures.py


def get_valid_booking_data(event_id: int):
    """Valid booking creation data"""
    return {
        "event_id": event_id,
        "number_of_seats": 2
    }


def get_single_seat_booking_data(event_id: int):
    """Booking for single seat"""
    return {
        "event_id": event_id,
        "number_of_seats": 1
    }


def get_large_booking_data(event_id: int):
    """Booking for many seats"""
    return {
        "event_id": event_id,
        "number_of_seats": 10
    }


def get_booking_data_zero_seats(event_id: int):
    """Invalid booking with zero seats"""
    return {
        "event_id": event_id,
        "number_of_seats": 0
    }


def get_booking_data_negative_seats(event_id: int):
    """Invalid booking with negative seats"""
    return {
        "event_id": event_id,
        "number_of_seats": -1
    }


def get_booking_data_nonexistent_event():
    """Booking for non-existent event"""
    return {
        "event_id": 99999,
        "number_of_seats": 1
    }


def get_booking_filter_params():
    """Default booking filter parameters"""
    return {
        "page": 1,
        "limit": 10
    }


def get_booking_filter_active():
    """Filter for active bookings"""
    return {
        "status": "active",
        "page": 1,
        "limit": 10
    }


def get_booking_filter_cancelled():
    """Filter for cancelled bookings"""
    return {
        "status": "cancelled",
        "page": 1,
        "limit": 10
    }


def get_booking_filter_by_price():
    """Filter bookings by price range"""
    return {
        "min_price": 0,
        "max_price": 500,
        "page": 1,
        "limit": 10
    }


def get_booking_filter_by_event_name(event_name: str):
    """Filter bookings by event name"""
    return {
        "event_name": event_name,
        "page": 1,
        "limit": 10
    }


def get_payment_status_paid():
    """Payment status update to paid"""
    return {
        "payment_status": "paid",
        "payment_method": "credit_card",
        "transaction_id": "txn_test_123456"
    }


def get_payment_status_refunded():
    """Payment status update to refunded"""
    return {
        "payment_status": "refunded",
        "payment_method": "credit_card",
        "transaction_id": "txn_test_refund_123"
    }


def get_payment_status_failed():
    """Payment status update to failed"""
    return {
        "payment_status": "failed",
        "payment_method": "credit_card",
        "transaction_id": "txn_test_failed_123"
    }


def calculate_expected_price(price_per_seat: float, num_seats: int) -> float:
    """Helper to calculate expected booking total price"""
    return round(price_per_seat * num_seats, 2)


def calculate_expected_tax(subtotal: float, tax_rate: float) -> dict:
    """Helper to calculate expected tax amounts"""
    tax_amount = round(subtotal * (tax_rate / 100), 2)
    total = round(subtotal + tax_amount, 2)
    return {
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "total_amount": total
    }
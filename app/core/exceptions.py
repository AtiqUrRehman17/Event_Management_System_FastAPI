from fastapi import HTTPException, status


class CustomHTTPException(HTTPException):
    """Base custom exception class"""
    def __init__(self, status_code: int, detail: str, error_code: str = None):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


# Authentication Exceptions
class InvalidCredentialsException(CustomHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            error_code="INVALID_CREDENTIALS"
        )


class TokenExpiredException(CustomHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            error_code="TOKEN_EXPIRED"
        )


class InvalidTokenException(CustomHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            error_code="INVALID_TOKEN"
        )


class UserNotFoundException(CustomHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            error_code="USER_NOT_FOUND"
        )


class EmailAlreadyExistsException(CustomHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
            error_code="EMAIL_ALREADY_EXISTS"
        )


class UsernameAlreadyExistsException(CustomHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
            error_code="USERNAME_ALREADY_EXISTS"
        )


# Event Exceptions
class EventNotFoundException(CustomHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
            error_code="EVENT_NOT_FOUND"
        )


class EventNotAvailableException(CustomHTTPException):
    def __init__(self, detail: str = "Event is not available for booking"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="EVENT_NOT_AVAILABLE"
        )


class InsufficientSeatsException(CustomHTTPException):
    def __init__(self, available_seats: int):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {available_seats} seats available",
            error_code="INSUFFICIENT_SEATS"
        )


class InvalidStatusTransitionException(CustomHTTPException):
    """Raised when an invalid event status transition is attempted"""
    def __init__(self, from_status: str, to_status: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition event status from '{from_status}' to '{to_status}'",
            error_code="INVALID_STATUS_TRANSITION"
        )


# Booking Exceptions
class BookingNotFoundException(CustomHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
            error_code="BOOKING_NOT_FOUND"
        )


class BookingNotOwnedException(CustomHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own bookings",
            error_code="BOOKING_NOT_OWNED"
        )


class BookingAlreadyCancelledException(CustomHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already cancelled",
            error_code="BOOKING_ALREADY_CANCELLED"
        )


# Payment Exceptions
class PaymentNotFoundException(CustomHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
            error_code="PAYMENT_NOT_FOUND"
        )


# Category Exceptions
class CategoryNotFoundException(CustomHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
            error_code="CATEGORY_NOT_FOUND"
        )


class CategoryAlreadyExistsException(CustomHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category already exists",
            error_code="CATEGORY_ALREADY_EXISTS"
        )


# Permission Exceptions
class PermissionDeniedException(CustomHTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to perform this action",
            error_code="PERMISSION_DENIED"
        )
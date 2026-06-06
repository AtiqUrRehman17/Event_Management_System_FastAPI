from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import jwt
from jwt.exceptions import PyJWTError
import logging
from typing import Union

from app.core.exceptions import (
    CustomHTTPException,
    InvalidCredentialsException,
    TokenExpiredException,
    InvalidTokenException,
    UserNotFoundException,
    EmailAlreadyExistsException,
    EventNotFoundException,
    EventNotAvailableException,
    InsufficientSeatsException,
    BookingNotFoundException,
    BookingNotOwnedException,
    BookingAlreadyCancelledException,
    CategoryNotFoundException,
    CategoryAlreadyExistsException,
    PermissionDeniedException,
    InvalidStatusTransitionException,  # new
)
from app.utils.response import error_response

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI):
    """
    Register all error handlers for the FastAPI application
    """

    @app.exception_handler(CustomHTTPException)
    async def custom_http_exception_handler(request: Request, exc: CustomHTTPException):
        logger.warning(f"CustomHTTPException: {exc.detail} - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(f"HTTPException: {exc.detail} - Path: {request.url.path}")
        return error_response(
            message=str(exc.detail),
            status_code=exc.status_code,
            error_code="HTTP_EXCEPTION"
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            error_detail = {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            }
            errors.append(error_detail)

        logger.warning(f"Validation Error: {errors} - Path: {request.url.path}")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": "Request validation failed",
                "error_code": "VALIDATION_ERROR",
                "details": errors
            }
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.error(f"Database Integrity Error: {str(exc)} - Path: {request.url.path}")
        return error_response(
            message="Database constraint violation. Please check your data.",
            status_code=status.HTTP_409_CONFLICT,
            error_code="DATABASE_INTEGRITY_ERROR"
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        logger.error(f"SQLAlchemy Error: {str(exc)} - Path: {request.url.path}")
        return error_response(
            message="Database error occurred. Please try again later.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR"
        )

    @app.exception_handler(PyJWTError)
    async def jwt_error_handler(request: Request, exc: PyJWTError):
        logger.warning(f"JWT Error: {str(exc)} - Path: {request.url.path}")
        return error_response(
            message="Invalid or malformed token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="JWT_ERROR"
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        logger.warning(f"Value Error: {str(exc)} - Path: {request.url.path}")
        return error_response(
            message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALUE_ERROR"
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Unhandled Exception: {str(exc)} - Path: {request.url.path}",
            exc_info=True
        )
        return error_response(
            message="An unexpected error occurred. Please try again later.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR"
        )

    @app.exception_handler(InvalidCredentialsException)
    async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsException):
        logger.warning(f"Invalid credentials attempt - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(TokenExpiredException)
    async def token_expired_handler(request: Request, exc: TokenExpiredException):
        logger.warning(f"Token expired - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(InvalidTokenException)
    async def invalid_token_handler(request: Request, exc: InvalidTokenException):
        logger.warning(f"Invalid token used - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(PermissionDeniedException)
    async def permission_denied_handler(request: Request, exc: PermissionDeniedException):
        logger.warning(f"Permission denied - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(EmailAlreadyExistsException)
    async def email_exists_handler(request: Request, exc: EmailAlreadyExistsException):
        logger.warning(f"Email already exists - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(UserNotFoundException)
    async def user_not_found_handler(request: Request, exc: UserNotFoundException):
        logger.warning(f"User not found - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(EventNotFoundException)
    async def event_not_found_handler(request: Request, exc: EventNotFoundException):
        logger.warning(f"Event not found - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(InsufficientSeatsException)
    async def insufficient_seats_handler(request: Request, exc: InsufficientSeatsException):
        logger.warning(f"Insufficient seats - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(BookingNotFoundException)
    async def booking_not_found_handler(request: Request, exc: BookingNotFoundException):
        logger.warning(f"Booking not found - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(BookingNotOwnedException)
    async def booking_not_owned_handler(request: Request, exc: BookingNotOwnedException):
        logger.warning(f"Booking not owned - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(BookingAlreadyCancelledException)
    async def booking_already_cancelled_handler(
        request: Request, exc: BookingAlreadyCancelledException
    ):
        logger.warning(f"Booking already cancelled - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(EventNotAvailableException)
    async def event_not_available_handler(request: Request, exc: EventNotAvailableException):
        logger.warning(f"Event not available - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(CategoryNotFoundException)
    async def category_not_found_handler(request: Request, exc: CategoryNotFoundException):
        logger.warning(f"Category not found - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(CategoryAlreadyExistsException)
    async def category_exists_handler(request: Request, exc: CategoryAlreadyExistsException):
        logger.warning(f"Category already exists - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )

    @app.exception_handler(InvalidStatusTransitionException)
    async def invalid_status_transition_handler(
        request: Request, exc: InvalidStatusTransitionException
    ):
        logger.warning(f"Invalid status transition - Path: {request.url.path}")
        return error_response(
            message=exc.detail,
            status_code=exc.status_code,
            error_code=exc.error_code
        )
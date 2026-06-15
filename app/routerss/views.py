# from fastapi import APIRouter, Request
# from fastapi.responses import HTMLResponse
# from fastapi.templating import Jinja2Templates

# # Initialize templates
# templates = Jinja2Templates(directory="app/templates")

# # Create router
# router = APIRouter(tags=["Views"])


# # ── Public Pages ─────────────────────────────

# @router.get("/", response_class=HTMLResponse)
# async def home_page(request: Request):
#     """Homepage - Landing page"""
#     return templates.TemplateResponse("home.html", {"request": request})


# @router.get("/login", response_class=HTMLResponse)
# async def login_page(request: Request):
#     """Login page"""
#     return templates.TemplateResponse("login.html", {"request": request})


# @router.get("/register", response_class=HTMLResponse)
# async def register_page(request: Request):
#     """Registration page"""
#     return templates.TemplateResponse("register.html", {"request": request})


# # ── Event Pages ──────────────────────────────

# @router.get("/events", response_class=HTMLResponse)
# async def events_page(request: Request):
#     """Browse all events page"""
#     return templates.TemplateResponse("events.html", {"request": request})


# @router.get("/events/{event_id}", response_class=HTMLResponse)
# async def event_detail_page(request: Request, event_id: int):
#     """Single event detail page"""
#     return templates.TemplateResponse("event_detail.html", {
#         "request": request,
#         "event_id": event_id
#     })


# # ── Authenticated User Pages ─────────────────

# @router.get("/my-bookings", response_class=HTMLResponse)
# async def my_bookings_page(request: Request):
#     """User's bookings page"""
#     return templates.TemplateResponse("my_bookings.html", {"request": request})


# @router.get("/profile", response_class=HTMLResponse)
# async def profile_page(request: Request):
#     """User profile page"""
#     return templates.TemplateResponse("profile.html", {"request": request})


# # ── Admin Pages ──────────────────────────────

# @router.get("/admin", response_class=HTMLResponse)
# async def admin_dashboard_page(request: Request):
#     """Admin dashboard page"""
#     return templates.TemplateResponse("admin_dashboard.html", {"request": request})


# # ── Error Pages ──────────────────────────────

# @router.get("/404", response_class=HTMLResponse)
# async def not_found_page(request: Request):
#     """404 error page"""
#     return templates.TemplateResponse("errors/404.html", {
#         "request": request
#     }, status_code=404)

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.services.auth_service import AuthService
from app.core.exceptions import InvalidTokenException, TokenExpiredException, UserNotFoundException

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

# Create router
router = APIRouter(tags=["Views"])


# ── Public Pages ─────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Homepage - Landing page"""
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page"""
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email_page(
    request: Request,
    token: str,
    db: Session = Depends(get_db)
):
    """
    Email verification page - User clicks link from email
    This handles the one-click verification and shows result page
    """
    # The token is passed as query parameter
    # We'll render the page and let JavaScript handle the API call
    # This avoids CORS issues and gives better user experience
    
    return templates.TemplateResponse("verify_email.html", {
        "request": request,
        "token": token
    })


@router.get("/resend-verification", response_class=HTMLResponse)
async def resend_verification_page(request: Request):
    """Page to request resend verification email"""
    return templates.TemplateResponse("resend_verification.html", {"request": request})


# ── Event Pages ──────────────────────────────

@router.get("/events", response_class=HTMLResponse)
async def events_page(request: Request):
    """Browse all events page"""
    return templates.TemplateResponse("events.html", {"request": request})


@router.get("/events/{event_id}", response_class=HTMLResponse)
async def event_detail_page(request: Request, event_id: int):
    """Single event detail page"""
    return templates.TemplateResponse("event_detail.html", {
        "request": request,
        "event_id": event_id
    })


# ── Authenticated User Pages ─────────────────

@router.get("/my-bookings", response_class=HTMLResponse)
async def my_bookings_page(request: Request):
    """User's bookings page"""
    return templates.TemplateResponse("my_bookings.html", {"request": request})


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """User profile page"""
    return templates.TemplateResponse("profile.html", {"request": request})


# ── Admin Pages ──────────────────────────────

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request):
    """Admin dashboard page"""
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})


# ── OAuth Callback Page ────────────────────────

@router.get("/oauth/callback", response_class=HTMLResponse)
async def oauth_callback_page(request: Request):
    """OAuth callback page - Handles redirect from backend after OAuth authentication"""
    return templates.TemplateResponse("oauth_callback.html", {"request": request})


# ── Error Pages ──────────────────────────────

@router.get("/404", response_class=HTMLResponse)
async def not_found_page(request: Request):
    """404 error page"""
    return templates.TemplateResponse("404.html", {
        "request": request
    }, status_code=404)
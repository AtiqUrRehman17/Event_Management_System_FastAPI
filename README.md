# Event Management System

A comprehensive Event Management System built with **FastAPI**, featuring JWT authentication, OAuth integrations (Google, LinkedIn & Facebook), role-based access control, email verification, password reset, booking management, waitlist functionality, invoice generation, notifications, admin dashboard, audit logs, and a complete server-side rendered frontend using Jinja2 templates.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Frontend Architecture](#frontend-architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Database Migrations](#database-migrations)
- [OAuth Setup Guides](#oauth-setup-guides)
- [API Endpoints](#api-endpoints)
- [Background Jobs](#background-jobs)
- [Security Features](#security-features)
- [Error Responses](#error-responses)
- [Pagination](#pagination)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Features

### 🔐 Authentication & Authorization

- **JWT Authentication** — Access and refresh tokens with expiry handling
- **Role-Based Access Control** — Admin and User roles with different permissions
- **Email Verification** — Verify user emails during registration
- **Password Reset Flow** — Forgot password with email reset links
- **Google OAuth Login** — Sign in with Google account
- **LinkedIn OAuth Login** — Sign in with LinkedIn account
- **Facebook OAuth Login** — Sign in with Facebook account
- **Token Blacklist** — Secure logout functionality

### 👤 User Management

- User registration and login
- Profile update (first name, last name, email, phone, bio, timezone)
- Password change functionality
- Account activation/deactivation (Admin only)
- Profile picture upload support

### 📅 Event Management

- Create, read, update, delete events (Admin only)
- Event fields: title, description, location, date/time, total seats, available seats, price, status, image URL
- Event statuses: `UPCOMING`, `COMPLETED`, `CANCELLED`
- Soft delete — Events can be soft-deleted and restored
- Search and filter events (by title, category, location, price range, date range, status)
- Event image upload support
- Pagination support for event lists

### 🎟️ Booking System

- Book events with seat availability validation
- **Concurrency-safe booking** — Row-level locking prevents overselling
- Automatic seat count management (decrease on booking, increase on cancellation)
- View user's own bookings
- Cancel own bookings (users) or any booking (admin)
- Booking history with categorized views (upcoming, past, cancelled)
- Booking statistics and analytics
- Export bookings to CSV and PDF

### 📊 Admin Dashboard

- Complete dashboard statistics (users, events, bookings, revenue)
- User activity tracking and analytics
- Event performance metrics
- Booking reports with date range filters
- Revenue reports by period (today, week, month, year, all-time)
- CSV export for reports

### 📝 Audit Logs

- Track all important actions (user login, profile updates, event changes, bookings)
- IP address and user agent tracking
- Filterable logs by user, action, category, date range
- Audit trail for specific users and entities
- Compliance and security forensics

### 🔔 Notification System

- Email and in-app notifications
- Notification types: booking confirmation, cancellation, payment updates, event reminders, waitlist promotions
- User-configurable notification preferences
- Unread notification count and marking as read

### ⏳ Waitlist Functionality

- Join waitlist when events are sold out
- Automatic position management
- Email notification when spot becomes available
- 48-hour confirmation window
- Automatic expiration handling

### 📄 Invoice Generation

- Unique invoice numbers (`INV-YYYYMM-XXXXXX`)
- PDF invoice download
- Tax calculation support
- QR code for verification
- Payment status tracking

### 🗂️ Category Management

- Create, read, update, delete event categories (Admin only)
- **Category hierarchy** — Parent-child relationships
- **Category icons and colors** — Visual distinction
- **Category images** — Upload category thumbnails
- Soft delete categories (`is_active` flag)
- Popular categories endpoint

### 🖼️ File Upload

- Event image upload
- Category image upload
- User avatar upload
- Image validation (type, size)
- Image optimization and thumbnail generation

### ⚙️ Additional Features

- Pagination for all list endpoints
- Background scheduler for event status auto-updates
- Token cleanup jobs (blacklist, reset tokens, verification tokens, waitlist)
- Email notifications (verification, password reset, booking confirmations, waitlist)
- Standardized API responses
- Comprehensive error handling
- Database migrations with Alembic

---

## Tech Stack

| Technology   | Version  | Purpose                  |
|--------------|----------|--------------------------|
| Python       | 3.11+    | Programming language     |
| FastAPI      | 0.104.1  | Web framework            |
| SQLAlchemy   | 2.0.23   | ORM for database         |
| Alembic      | 1.12.1   | Database migrations      |
| SQLite       | —        | Database (development)   |
| Pydantic     | 2.5.0    | Data validation          |
| PyJWT        | 2.8.0    | JWT token handling       |
| bcrypt       | 4.1.1    | Password hashing         |
| APScheduler  | 3.10.4   | Background jobs          |
| Authlib      | 1.2.1    | OAuth integration        |
| Pillow       | 10.1.0   | Image processing         |
| ReportLab    | 4.0.4    | PDF generation           |
| Uvicorn      | 0.24.0   | ASGI server              |

---

## Project Structure

```
event-management-system/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI application entry point
│   │
│   ├── core/                            # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py                    # App settings & environment variables
│   │   ├── database.py                  # Database connection & session
│   │   ├── enums.py                     # UserRole, EventStatus, BookingStatus
│   │   ├── exceptions.py                # Custom exception classes
│   │   ├── security.py                  # JWT token creation & verification
│   │   └── seed.py                      # Default admin user seeding
│   │
│   ├── models/                          # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py                      # User model (with OAuth fields)
│   │   ├── event.py                     # Event model (with soft delete)
│   │   ├── booking.py                   # Booking model
│   │   ├── category.py                  # Category model (with hierarchy)
│   │   ├── token_blacklist.py           # Token blacklist model
│   │   ├── password_reset_token.py      # Password reset tokens
│   │   ├── email_verification_token.py  # Email verification tokens
│   │   ├── waitlist.py                  # Waitlist model
│   │   ├── notification.py              # Notification models
│   │   └── audit_log.py                 # Audit log model
│   │
│   ├── schemas/                         # Pydantic models
│   │   ├── __init__.py
│   │   ├── auth.py                      # Authentication schemas
│   │   ├── user.py                      # User schemas
│   │   ├── event.py                     # Event schemas
│   │   ├── booking.py                   # Booking schemas
│   │   ├── category.py                  # Category schemas
│   │   ├── notification.py              # Notification schemas
│   │   ├── audit.py                     # Audit log schemas
│   │   ├── admin.py                     # Admin dashboard schemas
│   │   ├── invoice.py                   # Invoice schemas
│   │   └── waitlist.py                  # Waitlist schemas
│   │
│   ├── routers/                         # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py                      # Login, register, refresh, logout
│   │   ├── users.py                     # User profile & management
│   │   ├── events.py                    # Event CRUD & search
│   │   ├── bookings.py                  # Booking operations
│   │   ├── categories.py                # Category management
│   │   ├── oauth.py                     # Google, LinkedIn, Facebook OAuth
│   │   ├── invoice.py                   # Invoice generation
│   │   ├── waitlist.py                  # Waitlist management
│   │   ├── notifications.py             # Notification endpoints
│   │   ├── admin.py                     # Admin dashboard
│   │   ├── audit.py                     # Audit log endpoints
│   │   └── upload.py                    # File upload endpoints
│   │
│   ├── services/                        # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py              # Authentication logic
│   │   ├── user_service.py              # User management logic
│   │   ├── event_service.py             # Event management logic
│   │   ├── booking_service.py           # Booking management logic
│   │   ├── category_service.py          # Category management logic
│   │   ├── email_service.py             # Email sending service
│   │   ├── oauth_service.py             # Google OAuth logic
│   │   ├── linkedin_oauth_service.py    # LinkedIn OAuth logic
│   │   ├── facebook_oauth_service.py    # Facebook OAuth logic
│   │   ├── invoice_service.py           # Invoice generation logic
│   │   ├── waitlist_service.py          # Waitlist logic
│   │   ├── notification_service.py      # Notification logic
│   │   ├── admin_service.py             # Admin dashboard logic
│   │   └── audit_service.py             # Audit log logic
│   │
│   ├── dependencies/                    # FastAPI dependencies
│   │   ├── __init__.py
│   │   ├── auth.py                      # get_current_user, get_current_admin
│   │   └── db.py                        # get_db session
│   │
│   ├── pagination/                      # Pagination module
│   │   ├── __init__.py
│   │   └── pagination.py                # PaginationParams, paginate_query
│   │
│   └── utils/                           # Utility functions
│       ├── __init__.py
│       ├── auth_utils.py                # Password hashing & verification
│       ├── response.py                  # Standardized API responses
│       ├── error_handlers.py            # Global exception handlers
│       ├── validators.py                # Input validation functions
│       ├── datetime_utils.py            # Datetime utilities
│       └── image_upload.py              # Image upload utilities
│   ├── templates/                    # HTML templates
│   │   ├── admin_dashboard.html      # Admin dashboard page
│   │   ├── base.html                 # Base template (navigation, footer)
│   │   ├── event_details.html        # Single event details page
│   │   ├── event.html                # Events listing page
│   │   ├── home.html                 # Homepage
│   │   ├── login.html                # Login page
│   │   ├── profile.html              # User profile page
│   │   ├── register.html             # Registration page
│   │   └── bookings.html             # User bookings page
│   │
│   └── static/                       # Static assets
│       ├── css/
│       │   └── style.css             # Main stylesheet
│       └── js/
│           └── main.js               # JavaScript for frontend
tests/
├── __init__.py
├── conftest.py                         # Shared fixtures and configuration
│
├── unit/                               # Unit tests (isolated functions)
│   ├── __init__.py
│   ├── test_auth_utils.py              # Password hashing & verification
│   ├── test_datetime_utils.py          # Datetime helper functions
│   ├── test_pagination.py              # Pagination logic
│   ├── test_response.py                # API response formatters
│   ├── test_security.py                # JWT token functions
│   └── test_validator.py               # Input validation functions
│
├── integration/                        # Integration tests (API endpoints)
│   ├── __init__.py
│   ├── test_admin.py                   # Admin dashboard endpoints
│   ├── test_audit.py                   # Audit log endpoints
│   ├── test_auth.py                    # Authentication endpoints
│   ├── test_categories.py              # Category CRUD endpoints
│   ├── test_bookings.py                # Booking endpoints
│   ├── test_events.py                  # Event CRUD endpoints
│   ├── test_invoices.py                # Invoice endpoints
│   ├── test_notifications.py           # Notification endpoints
│   ├── test_users.py                   # User management endpoints
│   └── test_waitlist.py                # Waitlist endpoints
│
└── fixtures/                           # Test data fixtures
    ├── __init__.py
    ├── booking_fixtures.py             # Booking test data
    ├── category_fixtures.py            # Category test data
    ├── events_fixtures.py              # Event test data
    └── users_fixtures.py               # User test data
│
├── alembic/                             # Database migrations
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
│
├── uploads/                             # Uploaded files
│   ├── events/
│   ├── categories/
│   └── avatars/
│
├── .env                                 # Environment variables
├── .env.example                         # Example environment variables
├── .gitignore                           # Git ignore file
├── requirements.txt                     # Project dependencies
├── alembic.ini                          # Alembic configuration
└── README.md                            # This file
```

---

## Frontend Architecture

The project includes a complete **server-side rendered (SSR) frontend** built with **Jinja2 templates**, **Bootstrap 5**, and **Vanilla JavaScript**. The frontend communicates with the FastAPI backend via REST API calls.

### Frontend Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Jinja2 | 3.1.2 | Server-side template engine |
| Bootstrap | 5.3.2 | CSS framework (via CDN) |
| Font Awesome | 6.5.1 | Icon library (via CDN) |
| Google Fonts | — | Inter font family (via CDN) |
| Vanilla JavaScript | ES6+ | Client-side logic (no build step) |

### Template Structure (`app/templates/`)

```
templates/
├── base.html                 # Base layout with navbar, footer, auth state
├── home.html                 # Landing page with hero, stats, categories, featured events
├── events.html               # Events listing with search, filters, pagination
├── event_detail.html         # Single event view with booking sidebar
├── login.html                # Login page with OAuth buttons
├── register.html             # Registration page with password strength meter
├── profile.html              # User profile management (avatar, password, info)
├── my_bookings.html          # User's bookings with tabs (All/Active/Cancelled)
├── admin_dashboard.html      # Admin dashboard with stats, charts, recent activity
├── verify_email.html         # Email verification page
└── errors/
    └── 404.html              # Custom 404 error page
```

### Static Assets (`app/static/`)

```
static/
├── css/
│   └── style.css             # Custom styles (538 lines) extending Bootstrap
└── js/
    └── main.js               # Core JavaScript module (386 lines)
```

### Core JavaScript Module (`app/static/js/main.js`)

The `main.js` file provides a complete client-side application framework:

#### Authentication & Token Management
- **Token Storage**: Access/refresh tokens stored in `localStorage`
- **Auto-refresh**: Automatic token refresh on 401 responses
- **Auth State**: `checkAuthStatus()` updates navbar UI based on login state
- **Logout**: Secure logout with server-side token blacklisting

#### API Communication Layer
- **`apiCall(url, options)`**: Unified fetch wrapper with auth headers
- **Automatic retry**: Retries failed requests after token refresh
- **Error handling**: Network error fallbacks and user-friendly messages

#### UI Utilities
- **`showAlert(message, type, duration)`**: Toast-style notifications with icons
- **`showLoading/showEmpty/showError(containerId)`**: Standardized loading states
- **Date formatting**: `formatDate()`, `formatDateShort()`, `formatDateRelative()`
- **Currency/Number formatting**: `formatCurrency()`, `formatNumber()`
- **URL helpers**: `getUrlParam()`, `setUrlParam()` for query string manipulation
- **Debounce**: `debounce(func, wait)` for search inputs

#### Page-Specific JavaScript (Inline in Templates)

Each template includes page-specific logic in `{% block extra_js %}`:

| Page | Key Features |
|------|--------------|
| **home.html** | Loads categories & featured events, hero search, admin stats |
| **events.html** | Search/filter (category, price range), pagination, URL state sync |
| **event_detail.html** | Seat selector, price calculator, booking, waitlist join |
| **my_bookings.html** | Tab filtering, cancel booking, summary cards |
| **admin_dashboard.html** | Stats cards, recent bookings table, top events, recent users |
| **profile.html** | Avatar upload, profile update, password change, password strength |
| **register.html** | Password strength meter, real-time validation |
| **login.html** | OAuth redirect handlers, form validation |

### Base Template (`base.html`) Features

- **Responsive Navbar**: Collapsible mobile menu with user dropdown
- **Auth-Aware UI**: Shows login/register when logged out; profile/bookings/admin when logged in
- **Role-Based Links**: Admin dashboard link only for admin users
- **Global Alert Container**: Centralized toast notifications
- **CDN Resources**: Bootstrap, Font Awesome, Google Fonts loaded via CDN
- **Auto Auth Check**: Runs `checkAuthStatus()` on every page load

### CSS Architecture (`app/static/css/style.css`)

Custom styles (538 lines) organized into sections:

1. **CSS Variables** — Colors, shadows, transitions, fonts
2. **Global Reset** — Box-sizing, typography, scrollbar styling
3. **Navbar** — Brand, links, dropdown animations
4. **Cards** — Hover effects, event/category card variants
5. **Buttons** — Primary/secondary variants, loading states
6. **Forms** — Input styling, focus states, validation feedback
7. **Hero Section** — Gradient background with SVG pattern
8. **Badges/Alerts/Tables** — Component customizations
9. **Pagination/Progress** — Custom pagination, progress bars
10. **Auth Pages** — Centered card layouts
11. **Dashboard Stats** — Border-left accent cards
12. **Responsive** — Breakpoints at 768px and 576px
13. **Print Styles** — Hides UI elements for printing

### Key Frontend Features

#### 1. **Event Discovery**
- Homepage: Hero search, category grid, featured events carousel
- Events page: Full-text search, category filter, price range filter, pagination
- Event detail: Image gallery, seat availability progress bar, real-time price calculation

#### 2. **Booking Flow**
- Seat selector with +/- buttons (max 10 or available seats)
- Live total price calculation
- One-click booking with loading state
- Waitlist join when sold out
- Booking history with status tabs (All/Active/Cancelled)
- Cancel booking with confirmation

#### 3. **Authentication UX**
- Login/Register with validation
- Password strength meter (visual progress bar)
- OAuth buttons (Google, LinkedIn, Facebook)
- Email verification page
- Forgot/Reset password flow

#### 4. **User Profile**
- Avatar upload with preview
- Profile info editing (name, email, phone, bio, timezone)
- Password change with current password verification
- Notification preferences toggle

#### 5. **Admin Dashboard**
- 8 stat cards (users, events, bookings, revenue + secondary metrics)
- Recent bookings table with status badges
- Top events by revenue/bookings with fill rate
- Recent users with role badges and booking counts
- Responsive grid layout

#### 6. **Responsive Design**
- Mobile-first approach with Bootstrap 5 grid
- Collapsible navbar on mobile
- Stacked cards on small screens
- Touch-friendly buttons and inputs
- Print-optimized styles

### Frontend-Backend Integration

| Frontend | Backend API |
|----------|-------------|
| `apiCall('/api/v1/events/')` | `GET /api/v1/events` |
| `apiCall('/api/v1/bookings/', {method: 'POST', body: ...})` | `POST /api/v1/bookings` |
| `apiCall('/api/v1/auth/login', {method: 'POST', body: ...})` | `POST /api/v1/auth/login` |
| `apiCall('/api/v1/admin/dashboard/stats')` | `GET /api/v1/admin/dashboard/stats` |
| `apiCall('/api/v1/upload/avatar', {method: 'POST', body: FormData})` | `POST /api/v1/upload/avatar` |

### Running the Frontend

The frontend is served **automatically** by FastAPI:

```bash
# Start the server (serves both API and frontend)
uvicorn app.main:app --reload

# Access points:
# - Frontend Homepage:     http://localhost:8000/
# - Events Listing:        http://localhost:8000/events
# - Event Detail:          http://localhost:8000/events/{id}
# - Login:                 http://localhost:8000/login
# - Register:              http://localhost:8000/register
# - My Bookings:           http://localhost:8000/my-bookings
# - Profile:               http://localhost:8000/profile
# - Admin Dashboard:       http://localhost:8000/admin
# - API Docs (Swagger):    http://localhost:8000/docs
```

### Customization Guide

#### Adding a New Page
1. Create template: `app/templates/new_page.html`
2. Extend base: `{% extends "base.html" %}`
3. Add route in `app/routerss/views.py`
4. Include page-specific JS in `{% block extra_js %}`

#### Modifying Styles
- Edit `app/static/css/style.css`
- Use CSS variables for consistent theming
- Follow existing component patterns

#### Adding JavaScript Features
- Add utility functions to `main.js`
- Use `apiCall()` for all backend communication
- Follow existing patterns for loading/error states

---

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git (optional, for version control)
- Gmail account (for email notifications)
- Google Developer account (for Google OAuth)
- LinkedIn Developer account (for LinkedIn OAuth)
- Facebook Developer account (for Facebook OAuth)

---

## Automated Tests

The project includes a comprehensive test suite using **pytest** with **asyncio** support for testing async FastAPI endpoints.

### Test Structure

```
tests/
├── conftest.py                    # Shared fixtures & test configuration
├── unit/                          # Unit tests (isolated, fast)
│   ├── test_auth_utils.py         # Password hashing & verification
│   ├── test_datetime_utils.py     # Datetime helper functions
│   ├── test_pagination.py         # Pagination logic
│   ├── test_response.py           # API response formatters
│   ├── test_security.py           # JWT token creation/validation
│   └── test_validators.py         # Input validation functions
├── integration/                   # Integration tests (API endpoints)
│   ├── test_admin.py              # Admin dashboard endpoints
│   ├── test_audit.py              # Audit log endpoints
│   ├── test_auth.py               # Authentication endpoints
│   ├── test_categories.py         # Category CRUD endpoints
│   ├── test_bookings.py           # Booking endpoints
│   ├── test_events.py             # Event CRUD endpoints
│   ├── test_invoices.py           # Invoice endpoints
│   ├── test_notifications.py      # Notification endpoints
│   ├── test_users.py              # User management endpoints
│   └── test_waitlist.py           # Waitlist endpoints
└── fixtures/                      # Test data factories
    ├── booking_fixtures.py        # Booking test data
    ├── category_fixtures.py       # Category test data
    ├── event_fixtures.py          # Event test data
    └── user_fixtures.py           # User test data
```

### Test Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | 7.4.3 | Test framework |
| pytest-asyncio | 0.21.1 | Async test support |
| pytest-cov | 4.1.0 | Coverage reporting |
| factory-boy | 3.3.0 | Test data factories |
| faker | 20.1.0 | Fake data generation |
| freezegun | 1.2.2 | Time manipulation |

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/integration/test_auth.py -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run with verbose output
pytest -v --tb=short
```

### Test Configuration (`conftest.py`)

- **Database**: Uses in-memory SQLite for fast, isolated tests
- **Fixtures**: Provides `client` (TestClient), `db_session`, `admin_user`, `regular_user`, `auth_headers`
- **Factories**: Factory Boy factories for User, Event, Category, Booking models
- **Authentication**: Helper fixtures for generating valid JWT tokens

### Writing Tests

```python
# Unit test example
def test_password_hashing():
    from app.utils.auth_utils import hash_password, verify_password
    password = "Test@123456"
    hashed = hash_password(password)
    assert verify_password(password, hashed)

# Integration test example
def test_create_event(client, admin_auth_headers):
    response = client.post(
        "/api/v1/events/",
        json={"title": "Test Event", ...},
        headers=admin_auth_headers
    )
    assert response.status_code == 201
    assert response.json()["success"] is True
```

---

## Interactive UI (Frontend Pages)

The application includes a complete **server-side rendered web interface** built with Jinja2 templates, accessible directly in the browser. No separate frontend build process is required.

### Available Pages

| Route | Template | Description | Auth Required |
|-------|----------|-------------|---------------|
| `/` | `home.html` | Landing page with hero, stats, categories, featured events | No |
| `/events` | `events.html` | Events listing with search, filters, pagination | No |
| `/events/{id}` | `event_detail.html` | Event details with booking sidebar | No* |
| `/login` | `login.html` | Login form with OAuth buttons | No |
| `/register` | `register.html` | Registration with password strength meter | No |
| `/profile` | `profile.html` | User profile, avatar, password change | Yes |
| `/my-bookings` | `my_bookings.html` | User's bookings with filter tabs | Yes |
| `/admin` | `admin_dashboard.html` | Admin dashboard with stats & analytics | Admin |
| `/verify-email` | `verify_email.html` | Email verification page | No |

*Booking requires authentication

### Key UI Features

- **Responsive Design**: Works on mobile, tablet, desktop
- **Real-time Updates**: Booking seat availability, price calculation
- **Toast Notifications**: Success/error/warning alerts auto-dismiss
- **Loading States**: Spinners, skeleton screens, empty states
- **Form Validation**: Client-side + server-side validation feedback
- **OAuth Integration**: One-click Google/LinkedIn/Facebook login
- **Admin Dashboard**: Visual stats cards, tables, rankings
- **Image Upload**: Drag-and-drop avatar/event/category images

### Accessing the UI

```bash
# Start server
uvicorn app.main:app --reload

# Open in browser
http://localhost:8000/
```

---

## Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd event-management-system
```

### Step 2: Create Virtual Environment

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root with the following configuration:

```env
# Application
APP_NAME="Event Management System"
APP_VERSION="1.0.0"
DEBUG=True
API_PREFIX="/api/v1"

# Database
DATABASE_URL="sqlite:///./event_management.db"

# JWT Configuration - Generate your own secure key!
# Run: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY="your-generated-secret-key-here-at-least-32-characters"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Server
HOST="0.0.0.0"
PORT=8000

# Default Admin Credentials (CHANGE IN PRODUCTION!)
ADMIN_USERNAME="admin"
ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD="Admin@1234"
ADMIN_FIRST_NAME="Super"
ADMIN_LAST_NAME="Admin"

# Email Configuration (Gmail SMTP)
DEFAULT_FROM_EMAIL="your-email@gmail.com"
EMAIL_HOST="smtp.gmail.com"
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER="your-email@gmail.com"
EMAIL_HOST_PASSWORD="your-16-character-app-password"

# Google OAuth Configuration
GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
GOOGLE_REDIRECT_URI="http://localhost:8000/api/v1/auth/google/callback"

# LinkedIn OAuth Configuration
LINKEDIN_CLIENT_ID="your-linkedin-client-id"
LINKEDIN_CLIENT_SECRET="your-linkedin-client-secret"
LINKEDIN_REDIRECT_URI="http://localhost:8000/api/v1/auth/linkedin/callback"

# Facebook OAuth Configuration
FACEBOOK_CLIENT_ID="your-facebook-app-id"
FACEBOOK_CLIENT_SECRET="your-facebook-app-secret"
FACEBOOK_REDIRECT_URI="http://localhost:8000/api/v1/auth/facebook/callback"

# Email Verification
VERIFICATION_TOKEN_EXPIRE_MINUTES=1440
REQUIRE_EMAIL_VERIFICATION=True
RESET_TOKEN_EXPIRE_MINUTES=30

# Image Upload
MAX_IMAGE_SIZE_MB=5
```

### Step 5: Initialize Database

```bash
alembic upgrade head
```

### Step 6: Run the Application

```bash
uvicorn app.main:app --reload
```

### Step 7: Access the Application

| Resource                          | URL                            |
|-----------------------------------|--------------------------------|
| API Documentation (Swagger UI)    | http://localhost:8000/docs     |
| Alternative Documentation (ReDoc) | http://localhost:8000/redoc    |
| Health Check                      | http://localhost:8000/health   |

---

## Database Migrations

This project uses **Alembic** for database migrations.

### Common Commands

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Check current version
alembic current

# View migration history
alembic history

# Rollback last migration
alembic downgrade -1
```

---

## OAuth Setup Guides

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the **People API**
4. Configure the OAuth consent screen:
   - User Type: `External`
   - App name: `Event Management System`
   - Scopes: `email`, `profile`, `openid`
5. Create an **OAuth 2.0 Client ID**:
   - Application type: `Web application`
   - Redirect URI: `http://localhost:8000/api/v1/auth/google/callback`
6. Copy the **Client ID** and **Client Secret** to your `.env` file

### LinkedIn OAuth Setup

1. Go to [LinkedIn Developer Portal](https://developer.linkedin.com)
2. Create a new app
3. Enable **Sign In with LinkedIn using OpenID Connect** product
4. Configure OAuth 2.0 settings:
   - Redirect URL: `http://localhost:8000/api/v1/auth/linkedin/callback`
5. Copy the **Client ID** and **Client Secret** to your `.env` file

### Facebook OAuth Setup

1. Go to [Facebook Developers Portal](https://developers.facebook.com)
2. Create a new app (Consumer type)
3. Add the **Facebook Login** product
4. Configure OAuth settings:
   - Valid OAuth Redirect URIs: `http://localhost:8000/api/v1/auth/facebook/callback`
   - App Domains: `localhost`
5. Add required permissions: `public_profile`, `email`
6. Copy the **App ID** and **App Secret** to your `.env` file

---

## API Endpoints

### Authentication

| Method | Endpoint                             | Description                    | Auth Required |
|--------|--------------------------------------|--------------------------------|---------------|
| POST   | `/api/v1/auth/register`              | Register new user              | No            |
| POST   | `/api/v1/auth/login`                 | Login with username/password   | No            |
| POST   | `/api/v1/auth/verify-email`          | Verify email with token        | No            |
| POST   | `/api/v1/auth/resend-verification`   | Resend verification email      | No            |
| POST   | `/api/v1/auth/forgot-password`       | Request password reset         | No            |
| POST   | `/api/v1/auth/reset-password`        | Reset password with token      | No            |
| POST   | `/api/v1/auth/refresh`               | Refresh access token           | No            |
| POST   | `/api/v1/auth/logout`                | Logout and blacklist tokens    | Yes           |
| GET    | `/api/v1/auth/google/login`          | Google OAuth login             | No            |
| GET    | `/api/v1/auth/google/callback`       | Google OAuth callback          | No            |
| GET    | `/api/v1/auth/linkedin/login`        | LinkedIn OAuth login           | No            |
| GET    | `/api/v1/auth/linkedin/callback`     | LinkedIn OAuth callback        | No            |
| GET    | `/api/v1/auth/facebook/login`        | Facebook OAuth login           | No            |
| GET    | `/api/v1/auth/facebook/callback`     | Facebook OAuth callback        | No            |

### Users

| Method | Endpoint                              | Description                       | Auth Required |
|--------|---------------------------------------|-----------------------------------|---------------|
| GET    | `/api/v1/users/me`                    | Get current user profile          | Yes           |
| PUT    | `/api/v1/users/me`                    | Update current user profile       | Yes           |
| POST   | `/api/v1/users/me/change-password`    | Change password                   | Yes           |
| GET    | `/api/v1/users/`                      | Get all users (Admin only)        | Admin         |
| GET    | `/api/v1/users/{user_id}`             | Get user by ID (Admin only)       | Admin         |
| PUT    | `/api/v1/users/{user_id}/deactivate`  | Deactivate user (Admin only)      | Admin         |
| PUT    | `/api/v1/users/{user_id}/activate`    | Activate user (Admin only)        | Admin         |

### Events

| Method | Endpoint                              | Description                          | Auth Required  |
|--------|---------------------------------------|--------------------------------------|----------------|
| GET    | `/api/v1/events`                      | Get all events (with filters)        | No (Optional)  |
| GET    | `/api/v1/events/deleted`              | Get deleted events (Admin only)      | Admin          |
| GET    | `/api/v1/events/{event_id}`           | Get event by ID                      | No (Optional)  |
| POST   | `/api/v1/events`                      | Create event (Admin only)            | Admin          |
| PUT    | `/api/v1/events/{event_id}`           | Update event (Admin only)            | Admin          |
| DELETE | `/api/v1/events/{event_id}`           | Soft delete event (Admin only)       | Admin          |
| POST   | `/api/v1/events/{event_id}/restore`   | Restore deleted event (Admin only)   | Admin          |

### Categories

| Method | Endpoint                                | Description                       | Auth Required  |
|--------|-----------------------------------------|-----------------------------------|----------------|
| GET    | `/api/v1/categories`                    | Get all categories                | No (Optional)  |
| GET    | `/api/v1/categories/tree`               | Get category hierarchy            | No (Optional)  |
| GET    | `/api/v1/categories/popular`            | Get popular categories            | No (Optional)  |
| GET    | `/api/v1/categories/{category_id}`      | Get category by ID                | No (Optional)  |
| POST   | `/api/v1/categories`                    | Create category (Admin only)      | Admin          |
| PUT    | `/api/v1/categories/{category_id}`      | Update category (Admin only)      | Admin          |
| DELETE | `/api/v1/categories/{category_id}`      | Delete category (Admin only)      | Admin          |

### Bookings

| Method | Endpoint                               | Description                        | Auth Required |
|--------|----------------------------------------|------------------------------------|---------------|
| POST   | `/api/v1/bookings`                     | Book an event                      | Yes           |
| GET    | `/api/v1/bookings/me`                  | Get current user's bookings        | Yes           |
| GET    | `/api/v1/bookings/history`             | Get categorized booking history    | Yes           |
| GET    | `/api/v1/bookings/statistics`          | Get booking statistics             | Yes           |
| GET    | `/api/v1/bookings/me/summary`          | Get booking summary                | Yes           |
| GET    | `/api/v1/bookings/me/timeline`         | Get booking timeline               | Yes           |
| GET    | `/api/v1/bookings/me/export/csv`       | Export bookings to CSV             | Yes           |
| GET    | `/api/v1/bookings/me/export/pdf`       | Export bookings to PDF             | Yes           |
| POST   | `/api/v1/bookings/{booking_id}/cancel` | Cancel a booking                   | Yes           |
| GET    | `/api/v1/bookings/`                    | Get all bookings (Admin only)      | Admin         |
| GET    | `/api/v1/bookings/events/{event_id}`   | Get event bookings (Admin only)    | Admin         |

### Invoices

| Method | Endpoint                           | Description               | Auth Required |
|--------|------------------------------------|---------------------------|---------------|
| GET    | `/api/v1/invoices/{booking_id}`     | Get invoice as JSON       | Yes           |
| GET    | `/api/v1/invoices/{booking_id}/pdf` | Download invoice as PDF   | Yes           |

### Waitlist

| Method | Endpoint                                | Description           | Auth Required |
|--------|-----------------------------------------|-----------------------|---------------|
| POST   | `/api/v1/waitlist/{event_id}/join`      | Join waitlist         | Yes           |
| GET    | `/api/v1/waitlist/{event_id}/position`  | Check position        | Yes           |
| DELETE | `/api/v1/waitlist/{event_id}/leave`     | Leave waitlist        | Yes           |
| POST   | `/api/v1/waitlist/{event_id}/confirm`   | Confirm spot          | Yes           |

### Notifications

| Method | Endpoint                                   | Description                      | Auth Required |
|--------|--------------------------------------------|----------------------------------|---------------|
| GET    | `/api/v1/notifications/`                   | Get user notifications           | Yes           |
| GET    | `/api/v1/notifications/unread/count`       | Get unread count                 | Yes           |
| POST   | `/api/v1/notifications/mark-read`          | Mark notifications as read       | Yes           |
| GET    | `/api/v1/notifications/preferences`        | Get preferences                  | Yes           |
| PUT    | `/api/v1/notifications/preferences`        | Update preferences               | Yes           |

### Admin Dashboard

| Method | Endpoint                                         | Description               | Auth Required |
|--------|--------------------------------------------------|---------------------------|---------------|
| GET    | `/api/v1/admin/dashboard/stats`                  | Dashboard statistics      | Admin         |
| GET    | `/api/v1/admin/users/activity`                   | User activity             | Admin         |
| GET    | `/api/v1/admin/events/analytics`                 | Event analytics           | Admin         |
| GET    | `/api/v1/admin/reports/bookings`                 | Booking report            | Admin         |
| GET    | `/api/v1/admin/reports/revenue`                  | Revenue report            | Admin         |
| GET    | `/api/v1/admin/reports/bookings/export/csv`      | Export bookings report    | Admin         |

### Audit Logs

| Method | Endpoint                                  | Description               | Auth Required |
|--------|-------------------------------------------|---------------------------|---------------|
| GET    | `/api/v1/audit/logs`                      | Get audit logs            | Admin         |
| GET    | `/api/v1/audit/summary`                   | Get audit summary         | Admin         |
| GET    | `/api/v1/audit/user/{user_id}`            | Get user audit trail      | Admin         |
| GET    | `/api/v1/audit/entity/{type}/{id}`        | Get entity audit trail    | Admin         |

### File Upload

| Method | Endpoint                                   | Description               | Auth Required |
|--------|--------------------------------------------|---------------------------|---------------|
| POST   | `/api/v1/upload/event/{event_id}`          | Upload event image        | Admin         |
| POST   | `/api/v1/upload/category/{category_id}`    | Upload category image     | Admin         |
| POST   | `/api/v1/upload/avatar`                    | Upload user avatar        | Yes           |

---

## Background Jobs

The system runs automatic background jobs using **APScheduler**:

| Job                         | Frequency      | Description                                         |
|-----------------------------|----------------|-----------------------------------------------------|
| Event Status Update         | Every 1 hour   | Auto-updates past events to `COMPLETED` status      |
| Token Cleanup               | Every 24 hours | Removes expired tokens from blacklist               |
| Reset Token Cleanup         | Every 12 hours | Removes expired password reset tokens               |
| Verification Token Cleanup  | Every 24 hours | Removes expired email verification tokens           |
| Waitlist Cleanup            | Every 1 hour   | Removes expired waitlist notifications              |

---

## Security Features

| Feature                | Description                                           |
|------------------------|-------------------------------------------------------|
| Password Hashing       | bcrypt with salt                                      |
| JWT Tokens             | Access tokens (30 min) and refresh tokens (7 days)    |
| Token Blacklist        | Revoked tokens are blacklisted                        |
| Email Verification     | Required before login                                 |
| Refresh Token Rotation | Old refresh tokens are blacklisted on refresh         |
| Input Validation       | Pydantic schemas with field validators                |
| SQL Injection Protection | SQLAlchemy ORM                                      |
| CORS                   | Configurable allowed origins                          |
| Row-Level Locking      | Prevents seat overselling                             |
| Audit Logging          | Complete action tracking                              |
| Soft Delete            | Data preservation                                     |

---

## Error Responses

All errors follow a consistent format:

```json
{
  "success": false,
  "message": "Error description",
  "error_code": "ERROR_CODE"
}
```

### Common Error Codes

| Error Code                  | Description                        |
|-----------------------------|------------------------------------|
| `INVALID_CREDENTIALS`       | Wrong username/password            |
| `INVALID_TOKEN`             | Invalid or expired JWT token       |
| `PERMISSION_DENIED`         | Insufficient permissions           |
| `EMAIL_ALREADY_EXISTS`      | Email already registered           |
| `USERNAME_ALREADY_EXISTS`   | Username already taken             |
| `EVENT_NOT_FOUND`           | Event doesn't exist                |
| `INSUFFICIENT_SEATS`        | Not enough seats available         |
| `BOOKING_NOT_FOUND`         | Booking not found                  |
| `CATEGORY_NOT_FOUND`        | Category not found                 |
| `VALIDATION_ERROR`          | Request validation failed          |

---

## Pagination

All list endpoints support pagination with query parameters:

| Parameter | Default | Description                  |
|-----------|---------|------------------------------|
| `page`    | `1`     | Page number (starts at 1)    |
| `limit`   | `10`    | Items per page (max 100)     |

**Example:**

```bash
GET /api/v1/events?page=2&limit=20
```

**Response includes pagination metadata:**

```json
{
  "success": true,
  "data": [...],
  "meta": {
    "total": 100,
    "page": 2,
    "limit": 20,
    "total_pages": 5,
    "has_next": true,
    "has_previous": true
  }
}
```

---

## Testing

### Test Registration

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "Test@123456",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### Test Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test@123456"}'
```

### Test Protected Endpoint

```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Troubleshooting

| Issue                    | Solution                                                               |
|--------------------------|------------------------------------------------------------------------|
| Module not found errors  | Run `pip install -r requirements.txt`                                  |
| Database locked          | Delete `event_management.db` and run migrations again                  |
| Email not sending        | Generate a new Gmail App Password                                      |
| Token expired            | Use the refresh token endpoint to get new tokens                       |
| Port already in use      | Change `PORT` in `.env` or kill the process using port 8000            |
| CORS error               | Configure allowed origins in `.env`                                    |
| Migration conflicts      | Delete the database and run `alembic upgrade head`                     |

---

## Default Admin Account

On first run, the system automatically creates a default admin account:

| Field    | Value                  |
|----------|------------------------|
| Username | `admin`                |
| Password | `Admin@1234`           |
| Email    | `admin@example.com`    |

> ⚠️ **Important:** Change the default password immediately after first login!
# Event Management System

A comprehensive Event Management System built with **FastAPI**, featuring JWT authentication, OAuth integrations (Google, LinkedIn & Facebook), role-based access control, email verification, password reset, booking management, payment processing, waitlist functionality, invoice generation, notifications, admin dashboard, audit logs, and a complete server-side rendered frontend using Jinja2 templates.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Frontend Architecture](#frontend-architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Setup](#environment-setup)
- [Running the Application](#running-the-application)
- [Database Migrations](#database-migrations)
- [OAuth Setup Guides](#oauth-setup-guides)
- [API Endpoints](#api-endpoints)
- [Payment System](#payment-system)
- [Background Jobs](#background-jobs)
- [Security Features](#security-features)
- [Error Responses](#error-responses)
- [Pagination](#pagination)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Features

### Authentication & Authorization

- **JWT Authentication** — Access tokens (30 min) and refresh tokens (7 days) with automatic expiry handling
- **Role-Based Access Control** — Admin and User roles with strict permission enforcement
- **Email Verification** — Token-based email verification during registration (auto-disabled in dev mode when SMTP unconfigured)
- **Password Reset Flow** — Forgot password with email token
- **Google OAuth Login** — Sign in with Google account via OpenID Connect
- **LinkedIn OAuth Login** — Sign in with LinkedIn account via OpenID Connect
- **Facebook OAuth Login** — Sign in with Facebook account via Facebook Login
- **Token Blacklist** — Secure logout with token invalidation
- **Refresh Token Rotation** — Old refresh tokens blacklisted on each refresh

### User Management

- User registration and login
- Profile update (first name, last name, email, phone, bio, timezone)
- Password change with current password verification
- Account activation/deactivation (Admin only)
- Avatar upload support

### Event Management

- Create, read, update, delete events (Admin only)
- Fields: title, description, location, date/time, total seats, available seats, price, status, image
- Statuses: `UPCOMING`, `COMPLETED`, `CANCELLED`
- Soft delete with restore capability
- Search and filter (by title, category, location, price range, date range, status)
- Event image upload
- Pagination with metadata

### Booking System

- Book events with real-time seat availability validation
- **Concurrency-safe** — Row-level locking prevents overselling
- Automatic seat count management (decrease on booking, increase on cancellation)
- View own bookings with categorized tabs (All / Active / Cancelled)
- Cancel own bookings (users) or any booking (admin)
- Booking history, statistics, and analytics
- Export to CSV and PDF

### Payment System

- Initiate payments for bookings
- Simulate successful/failed payments (development mode)
- Full refund processing with audit trail
- Payment status tracking (pending, completed, failed, refunded)
- View payment by ID or by booking
- List own payments with pagination
- Admin can view all payments

### Admin Dashboard

- Dashboard statistics (users, events, bookings, revenue)
- User activity tracking
- Event performance analytics
- Booking reports with date range filters
- Revenue reports (today, week, month, year, all-time)
- CSV export for reports

### Audit Logs

- Track all important actions (login, registration, profile updates, events, bookings, payments)
- IP address and user agent tracking
- Filterable logs (by user, action, category, date range)
- Audit trail for specific users and entities

### Notification System

- Email and in-app notifications
- Types: booking confirmation, cancellation, payment updates, event reminders, waitlist promotions
- User-configurable notification preferences
- Unread notification count and mark-as-read

### Waitlist Functionality

- Join waitlist when events are sold out
- Automatic position management
- Email notification when spot becomes available
- 48-hour confirmation window
- Automatic expiration handling

### Invoice Generation

- Unique invoice numbers (`INV-YYYYMM-XXXXXX`)
- PDF invoice download with QR code for verification
- Tax calculation support
- Payment status tracking

### Category Management

- Create, read, update, delete categories (Admin only)
- **Hierarchy** — Parent-child relationships with path tracking
- **Icons and colors** — Visual distinction
- **Category images** — Upload thumbnails
- Soft delete (`is_active` flag)
- Popular categories endpoint

### File Upload

- Event image upload
- Category image upload
- User avatar upload
- Image validation (type, size)
- Organized upload directories

### Additional Features

- Pagination with metadata for all list endpoints
- Background scheduler (event status updates, token cleanup, waitlist cleanup)
- Alembic migrations auto-run on startup
- Auto-copy `.env.example` → `.env` when missing
- Smart dev defaults (email verification auto-disabled when SMTP unconfigured)
- Graceful SMTP fallback (logs warning instead of crashing)
- Standardized API responses (`success`, `data`, `message`, `meta`)
- Comprehensive error handling with custom exceptions

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
| Jinja2       | 3.1.2    | Server-side templates    |
| Bootstrap    | 5.3.2    | CSS framework (via CDN)  |

---

## Project Structure

```
event-management-system/
├── app/
│   ├── __init__.py
│   ├── main.py                              # FastAPI app entry, lifespan, routers
│   │
│   ├── core/                                # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py                        # Settings via pydantic-settings
│   │   ├── database.py                      # Engine & session factory
│   │   ├── enums.py                         # UserRole, EventStatus, BookingStatus, etc.
│   │   ├── exceptions.py                    # Custom HTTP exceptions
│   │   ├── security.py                      # JWT create/decode helpers
│   │   └── seed.py                          # Admin user auto-seeding
│   │
│   ├── models/                              # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py                          # User (username, email, role, OAuth fields)
│   │   ├── event.py                         # Event (soft delete, status)
│   │   ├── booking.py                       # Booking (seats, price, status)
│   │   ├── payment.py                       # Payment (amount, status, refund)
│   │   ├── category.py                      # Category (hierarchy via parent_id)
│   │   ├── token_blacklist.py               # Revoked JWT tokens
│   │   ├── password_reset_token.py          # Password reset tokens
│   │   ├── email_verification_token.py      # Email verification tokens
│   │   ├── waitlist.py                      # Waitlist entry (position, status)
│   │   ├── notification.py                  # Notification + NotificationPreference
│   │   └── audit_log.py                     # Audit log entries
│   │
│   ├── schemas/                             # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── auth.py                          # RegisterRequest, LoginRequest, etc.
│   │   ├── user.py                          # UserUpdate, UserResponse
│   │   ├── event.py                         # EventCreate, EventUpdate, EventResponse
│   │   ├── booking.py                       # BookingCreate, BookingResponse
│   │   ├── payment.py                       # PaymentInitiate, PaymentResponse
│   │   ├── category.py                      # CategoryCreate, CategoryResponse
│   │   ├── notification.py                  # NotificationResponse, Preferences
│   │   ├── audit.py                         # AuditLogResponse
│   │   ├── admin.py                         # DashboardStats, ReportResponse
│   │   ├── invoice.py                       # InvoiceResponse
│   │   └── waitlist.py                      # WaitlistResponse
│   │
│   ├── routers/                             # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py                          # POST register, login, refresh, logout, verify
│   │   ├── oauth.py                         # GET google/linkedin/facebook login & callback
│   │   ├── users.py                         # GET/PUT me, admin user management
│   │   ├── events.py                        # CRUD + filters, restore, deleted
│   │   ├── bookings.py                      # CRUD, cancel, export, stats
│   │   ├── payments.py                      # Initiate, simulate, refund, list
│   │   ├── categories.py                    # CRUD, tree, popular
│   │   ├── waitlist.py                      # Join, leave, position, confirm
│   │   ├── notifications.py                 # List, count, mark-read, preferences
│   │   ├── invoice.py                       # GET json/pdf by booking
│   │   ├── admin.py                         # Dashboard stats, reports, analytics
│   │   ├── audit.py                         # Logs, summary, user/entity trail
│   │   └── upload.py                        # Event/category/avatar image upload
│   │
│   ├── services/                            # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py                  # Registration, login, email verification, password reset
│   │   ├── oauth_service.py                 # Google OAuth flow
│   │   ├── linkedin_oauth_service.py        # LinkedIn OAuth flow
│   │   ├── facebook_oauth_service.py        # Facebook OAuth flow
│   │   ├── user_service.py                  # Profile CRUD
│   │   ├── event_service.py                 # Event CRUD, status updates
│   │   ├── booking_service.py               # Booking, cancellation, export
│   │   ├── payment_service.py               # Initiate, simulate, refund, query
│   │   ├── category_service.py              # Category CRUD, hierarchy
│   │   ├── email_service.py                 # SMTP + Postmark email sending
│   │   ├── invoice_service.py               # PDF generation via ReportLab
│   │   ├── waitlist_service.py              # Join, notify, confirm, cleanup
│   │   ├── notification_service.py          # Create, fetch, mark-read
│   │   ├── admin_service.py                 # Dashboard stats & reports
│   │   └── audit_service.py                 # Log actions, query logs
│   │
│   ├── dependencies/                        # FastAPI dependency injection
│   │   ├── __init__.py
│   │   ├── auth.py                          # get_current_user, get_current_admin
│   │   └── db.py                            # get_db session
│   │
│   ├── pagination/                          # Reusable pagination
│   │   ├── __init__.py
│   │   └── pagination.py                    # PaginationParams, paginate_query
│   │
│   ├── utils/                               # Utility functions
│   │   ├── __init__.py
│   │   ├── auth_utils.py                    # hash_password, verify_password
│   │   ├── datetime_utils.py                # get_current_utc, format helpers
│   │   ├── response.py                      # success_response, error_response, paginated_response
│   │   ├── error_handlers.py                # Global exception → JSON handler
│   │   ├── validators.py                    # password_strength, validate_email, etc.
│   │   └── image_upload.py                  # Save, validate, delete images
│   │
│   ├── templates/                           # Jinja2 server-side templates
│   │   ├── base.html                        # Base layout (navbar, footer, auth state)
│   │   ├── home.html                        # Landing page with hero, stats, categories
│   │   ├── events.html                      # Event listing with search/filter/pagination
│   │   ├── event_detail.html                # Single event with booking sidebar
│   │   ├── login.html                       # Login form + OAuth buttons
│   │   ├── register.html                    # Registration with password strength meter
│   │   ├── profile.html                     # Profile edit, avatar, password change
│   │   ├── my_bookings.html                 # Bookings with tabs (All/Active/Cancelled)
│   │   ├── admin_dashboard.html             # Admin stats, charts, tables
│   │   ├── verify_email.html                # Email verification status
│   │   ├── resend_verification.html         # Resend verification email
│   │   ├── oauth_callback.html              # OAuth callback handler
│   │   └── errors/
│   │       └── 404.html                     # Custom 404 page
│   │
│   └── static/                              # Static assets
│       ├── css/
│       │   └── style.css                    # Custom styles (538 lines)
│       └── js/
│           └── main.js                      # Core JS module (API calls, auth, UI)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                          # Shared fixtures (in-memory SQLite, client, users)
│   │
│   ├── unit/                                # Unit tests (isolated, fast)
│   │   ├── __init__.py
│   │   ├── test_auth_utils.py               # Password hashing & verification
│   │   ├── test_datetime_utils.py           # Datetime helpers
│   │   ├── test_pagination.py               # Pagination logic
│   │   ├── test_response.py                 # Response formatters
│   │   ├── test_security.py                 # JWT creation/validation
│   │   └── test_validators.py               # Input validators
│   │
│   ├── oauth/                               # OAuth service tests (mocked HTTP)
│   │   ├── __init__.py
│   │   ├── test_google_oauth.py             # Google OAuth flow tests
│   │   ├── test_linkedin_oauth.py           # LinkedIn OAuth flow tests
│   │   └── test_facebook_oauth.py           # Facebook OAuth flow tests
│   │
│   ├── integration/                         # Integration tests (real API calls)
│   │   ├── __init__.py
│   │   ├── test_admin.py                    # Admin dashboard endpoints
│   │   ├── test_audit.py                    # Audit log endpoints
│   │   ├── test_auth.py                     # Authentication endpoints
│   │   ├── test_bookings.py                 # Booking endpoints
│   │   ├── test_categories.py               # Category CRUD
│   │   ├── test_events.py                   # Event CRUD
│   │   ├── test_invoices.py                 # Invoice endpoints
│   │   ├── test_notifications.py            # Notification endpoints
│   │   ├── test_payments.py                 # Payment endpoints (28 tests)
│   │   ├── test_users.py                    # User management endpoints
│   │   └── test_waitlist.py                 # Waitlist endpoints
│   │
│   └── fixtures/                            # Test data factories
│       ├── __init__.py
│       ├── user_fixtures.py                 # User factory
│       ├── category_fixtures.py             # Category factory
│       ├── event_fixtures.py                # Event factory
│       └── booking_fixtures.py              # Booking factory
│
├── alembic/                                 # Database migrations
│   ├── versions/
│   │   └── c5fb60420995_initial_schema.py   # Full initial schema migration
│   ├── env.py                               # Alembic environment config
│   └── script.py.mako                       # Migration template
│
├── uploads/                                 # Uploaded files
│   ├── events/
│   ├── categories/
│   └── avatars/
│
├── .env                                     # Local environment (git-ignored)
├── .env.example                             # Environment template
├── .env.test                                # Test environment variables
├── .gitignore
├── pytest.ini                               # Pytest markers & config
├── requirements.txt                         # Python dependencies
├── alembic.ini                              # Alembic configuration
├── run.py                                   # App entry point
├── setup.py                                   # env setup
└── README.md                                # This file
```

---

## Frontend Architecture

The project includes a complete **server-side rendered (SSR) frontend** built with **Jinja2 templates**, **Bootstrap 5**, and **Vanilla JavaScript**. No separate build step is required.

### Template Structure (`app/templates/`)

```
templates/
├── base.html                     # Base layout with navbar, footer, auth state
├── home.html                     # Landing page with hero, stats, categories, featured events
├── events.html                   # Events listing with search, filters, pagination
├── event_detail.html             # Single event view with booking sidebar
├── login.html                    # Login page with OAuth buttons
├── register.html                 # Registration with password strength meter
├── profile.html                  # User profile (avatar, info, password)
├── my_bookings.html              # Bookings with tabs (All/Active/Cancelled)
├── admin_dashboard.html          # Admin stats, recent activity, reports
├── verify_email.html             # Email verification page
├── resend_verification.html      # Resend verification email form
├── oauth_callback.html           # OAuth callback handler page
└── errors/
    └── 404.html                  # Custom 404 error page
```

### Core JavaScript Module (`app/static/js/main.js`)

The `main.js` file provides:

- **Token Management** — Store access/refresh tokens in `localStorage`, auto-refresh on 401
- **Auth State** — `checkAuthStatus()` updates navbar (login/register vs profile/admin/logout)
- **API Layer** — `apiCall(url, options)` unified fetch wrapper with auth headers, automatic retry
- **UI Utilities** — `showAlert()` toast notifications, `showLoading/showEmpty/showError()`, date/currency formatting, debounce
- **Page-Specific Logic** — Inline `{% block extra_js %}` per template

### Frontend Pages

| Route | Template | Description | Auth |
|-------|----------|-------------|------|
| `/` | `home.html` | Landing page with hero, stats, categories, featured events | No |
| `/events` | `events.html` | Events listing with search, filters, pagination | No |
| `/events/{id}` | `event_detail.html` | Event details with booking sidebar, waitlist | No* |
| `/login` | `login.html` | Login form with Google/LinkedIn/Facebook OAuth buttons | No |
| `/register` | `register.html` | Registration with password strength meter | No |
| `/profile` | `profile.html` | Profile edit, avatar upload, password change | Yes |
| `/my-bookings` | `my_bookings.html` | User's bookings with filter tabs | Yes |
| `/admin` | `admin_dashboard.html` | Admin dashboard with stats & analytics | Admin |
| `/verify-email` | `verify_email.html` | Email verification status page | No |

*\*Booking requires authentication.*

### Frontend-Backend Integration

| Frontend | Backend API |
|----------|-------------|
| `apiCall('/api/v1/events/')` | `GET /api/v1/events` |
| `apiCall('/api/v1/bookings/', {method: 'POST', body: ...})` | `POST /api/v1/bookings` |
| `apiCall('/api/v1/auth/login', {method: 'POST', body: ...})` | `POST /api/v1/auth/login` |
| `apiCall('/api/v1/admin/dashboard/stats')` | `GET /api/v1/admin/dashboard/stats` |
| `apiCall('/api/v1/upload/avatar', {method: 'POST', body: FormData})` | `POST /api/v1/upload/avatar` |

---

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git (optional, for version control)

**Optional (for email/OAuth features):**
- Gmail account with App Password (for email notifications)
- Google Developer account (for Google OAuth)
- LinkedIn Developer account (for LinkedIn OAuth)
- Facebook Developer account (for Facebook OAuth)

> **Note:** The app works out-of-the-box without any of the above. Email verification is automatically disabled in dev mode when SMTP is unconfigured. OAuth logins simply won't appear if credentials are empty.

---

## Installation

### Quick Start (Recommended)

```bash
# 1. Clone the repository
git clone <repository-url>
cd event-management-system

# 2. Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the one-command setup (copies .env.example → .env, generates SECRET_KEY)
python setup.py

# 5. Start the app
python run.py

# 6. Open in browser
open http://localhost:8000
```

### Step-by-Step Installation

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd event-management-system
```

#### 2. Create Virtual Environment

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

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure Environment Variables

**Option A: Automatic (Recommended)**
```bash
python setup.py
```
This copies `.env.example` → `.env` (if missing) and generates a secure `SECRET_KEY`.

**Option B: Manual**
```bash
cp .env.example .env
# Then edit .env and set a SECRET_KEY:
#   python -c "import secrets; print(secrets.token_urlsafe(32))"
```

> **Note:** The app also auto-copies `.env.example` → `.env` on startup if `.env` is missing, so you can just run `python run.py` directly.

#### 5. Run the Application

```bash
python run.py
```

Or with uvicorn directly:

```bash
uvicorn app.main:app --reload
```

#### 6. Access the Application

| Resource                          | URL                            |
|-----------------------------------|--------------------------------|
| Web Application (Homepage)        | http://localhost:8000/         |
| API Documentation (Swagger UI)    | http://localhost:8000/docs     |
| Alternative Docs (ReDoc)          | http://localhost:8000/redoc    |
| Health Check                      | http://localhost:8000/health   |

#### Default Admin Account

On first run, the system automatically creates a default admin account:

| Field    | Value               |
|----------|---------------------|
| Username | `admin`             |
| Password | `Admin@1234`        |
| Email    | `admin@example.com` |

> **Important:** Change the default password immediately after first login!

---

## Environment Setup

### `.env` File Reference

The system uses a `.env` file for all configuration. See `.env.example` for the complete template.

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | Event Management System | Application name |
| `DEBUG` | True | Development mode (disables email verification if SMTP unconfigured) |
| `DATABASE_URL` | sqlite:///./event_management.db | Database connection string |
| `SECRET_KEY` | (generated) | JWT signing key (min 32 chars for production) |
| `REQUIRE_EMAIL_VERIFICATION` | True | Block login until email verified (auto-disabled in dev when SMTP missing) |
| `FRONTEND_URL` | http://localhost:8000 | Used in email links and OAuth callbacks |
| `UPLOAD_DIR` | uploads | Directory for uploaded files |

### Smart Dev Defaults

When `DEBUG=True` and SMTP credentials (`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`) are empty:

- `REQUIRE_EMAIL_VERIFICATION` is automatically set to `False` — login works without email verification
- `EmailService.send_email()` logs a warning and returns `False` instead of crashing

This means a new developer can clone, run, and log in without configuring any email provider.

### Setup Script

```bash
python setup.py
```

This script:
1. Copies `.env.example` → `.env` if `.env` doesn't exist
2. Generates a cryptographically secure `SECRET_KEY` via `secrets.token_urlsafe(32)`
3. Prints a summary of the setup

---

## Running the Application

### Development

```bash
# Standard
python run.py

# Or with hot-reload
uvicorn app.main:app --reload
```

### Production

```bash
# Set DEBUG=False in .env and configure a production database (PostgreSQL)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### What Happens on Startup

1. **Alienbic migrations** run automatically (`alembic upgrade head`)
2. **Database seeding** creates the default admin user if not exists
3. **Event status update** marks past events as `COMPLETED`
4. **Background scheduler** starts with 5 jobs
5. **Frontend** is served at `/`, API at `/api/v1/`

---

## Database Migrations

Migrations run **automatically** on every startup via `app/main.py`. You can also manage them manually:

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply pending migrations
alembic upgrade head

# Check current version
alembic current

# View history
alembic history

# Rollback one step
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

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/auth/register` | Register new user | No |
| POST | `/api/v1/auth/login` | Login with username/password | No |
| POST | `/api/v1/auth/verify-email` | Verify email with token | No |
| POST | `/api/v1/auth/resend-verification` | Resend verification email | No |
| POST | `/api/v1/auth/forgot-password` | Request password reset | No |
| POST | `/api/v1/auth/reset-password` | Reset password with token | No |
| POST | `/api/v1/auth/refresh` | Refresh access token | No |
| POST | `/api/v1/auth/logout` | Logout and blacklist tokens | Yes |
| GET | `/api/v1/auth/google/login` | Google OAuth login redirect | No |
| GET | `/api/v1/auth/google/callback` | Google OAuth callback | No |
| GET | `/api/v1/auth/linkedin/login` | LinkedIn OAuth login redirect | No |
| GET | `/api/v1/auth/linkedin/callback` | LinkedIn OAuth callback | No |
| GET | `/api/v1/auth/facebook/login` | Facebook OAuth login redirect | No |
| GET | `/api/v1/auth/facebook/callback` | Facebook OAuth callback | No |

### Users

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/users/me` | Get current user profile | Yes |
| PUT | `/api/v1/users/me` | Update current user profile | Yes |
| POST | `/api/v1/users/me/change-password` | Change password | Yes |
| GET | `/api/v1/users/` | Get all users (Admin only) | Admin |
| GET | `/api/v1/users/{user_id}` | Get user by ID (Admin only) | Admin |
| PUT | `/api/v1/users/{user_id}/deactivate` | Deactivate user (Admin only) | Admin |
| PUT | `/api/v1/users/{user_id}/activate` | Activate user (Admin only) | Admin |

### Events

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/events` | List events (with filters, search, pagination) | No |
| GET | `/api/v1/events/deleted` | List deleted events (Admin only) | Admin |
| GET | `/api/v1/events/{event_id}` | Get event by ID | No |
| POST | `/api/v1/events` | Create event (Admin only) | Admin |
| PUT | `/api/v1/events/{event_id}` | Update event (Admin only) | Admin |
| DELETE | `/api/v1/events/{event_id}` | Soft delete event (Admin only) | Admin |
| POST | `/api/v1/events/{event_id}/restore` | Restore deleted event (Admin only) | Admin |

### Categories

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/categories` | List all categories | No |
| GET | `/api/v1/categories/tree` | Get category hierarchy tree | No |
| GET | `/api/v1/categories/popular` | Get popular categories | No |
| GET | `/api/v1/categories/{category_id}` | Get category by ID | No |
| POST | `/api/v1/categories` | Create category (Admin only) | Admin |
| PUT | `/api/v1/categories/{category_id}` | Update category (Admin only) | Admin |
| DELETE | `/api/v1/categories/{category_id}` | Delete category (Admin only) | Admin |

### Bookings

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/bookings` | Book an event | Yes |
| GET | `/api/v1/bookings/me` | Get current user's bookings | Yes |
| GET | `/api/v1/bookings/history` | Categorized booking history | Yes |
| GET | `/api/v1/bookings/statistics` | Booking statistics | Yes |
| GET | `/api/v1/bookings/me/summary` | Booking summary | Yes |
| GET | `/api/v1/bookings/me/timeline` | Booking timeline | Yes |
| GET | `/api/v1/bookings/me/export/csv` | Export bookings to CSV | Yes |
| GET | `/api/v1/bookings/me/export/pdf` | Export bookings to PDF | Yes |
| POST | `/api/v1/bookings/{booking_id}/cancel` | Cancel a booking | Yes |
| GET | `/api/v1/bookings/` | All bookings (Admin only) | Admin |
| GET | `/api/v1/bookings/events/{event_id}` | Event bookings (Admin only) | Admin |

### Payments

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/payments/initiate` | Initiate payment for a booking | Yes |
| GET | `/api/v1/payments/{payment_id}` | Get payment details | Yes |
| GET | `/api/v1/payments/booking/{booking_id}` | Get payment by booking | Yes |
| GET | `/api/v1/payments/me` | List own payments | Yes |
| POST | `/api/v1/payments/{payment_id}/simulate` | Simulate payment (dev mode) | Yes |
| POST | `/api/v1/payments/{payment_id}/refund` | Refund a payment | Yes |

### Invoices

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/invoices/{booking_id}` | Get invoice as JSON | Yes |
| GET | `/api/v1/invoices/{booking_id}/pdf` | Download invoice as PDF | Yes |

### Waitlist

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/waitlist/{event_id}/join` | Join event waitlist | Yes |
| GET | `/api/v1/waitlist/{event_id}/position` | Check waitlist position | Yes |
| DELETE | `/api/v1/waitlist/{event_id}/leave` | Leave waitlist | Yes |
| POST | `/api/v1/waitlist/{event_id}/confirm` | Confirm available spot | Yes |

### Notifications

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/notifications/` | List user notifications | Yes |
| GET | `/api/v1/notifications/unread/count` | Get unread count | Yes |
| POST | `/api/v1/notifications/mark-read` | Mark notifications as read | Yes |
| GET | `/api/v1/notifications/preferences` | Get notification preferences | Yes |
| PUT | `/api/v1/notifications/preferences` | Update notification preferences | Yes |

### Admin Dashboard

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/admin/dashboard/stats` | Dashboard statistics | Admin |
| GET | `/api/v1/admin/users/activity` | User activity | Admin |
| GET | `/api/v1/admin/events/analytics` | Event analytics | Admin |
| GET | `/api/v1/admin/reports/bookings` | Booking report | Admin |
| GET | `/api/v1/admin/reports/revenue` | Revenue report | Admin |
| GET | `/api/v1/admin/reports/bookings/export/csv` | Export bookings report | Admin |

### Audit Logs

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/audit/logs` | List audit logs | Admin |
| GET | `/api/v1/audit/summary` | Audit summary | Admin |
| GET | `/api/v1/audit/user/{user_id}` | User audit trail | Admin |
| GET | `/api/v1/audit/entity/{type}/{id}` | Entity audit trail | Admin |

### File Upload

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/upload/event/{event_id}` | Upload event image | Admin |
| POST | `/api/v1/upload/category/{category_id}` | Upload category image | Admin |
| POST | `/api/v1/upload/avatar` | Upload user avatar | Yes |

---

## Payment System

The payment module provides a complete payment lifecycle:

### Flow

1. **Create Booking** → `POST /api/v1/bookings` → booking with `payment_status: "pending"`
2. **Initiate Payment** → `POST /api/v1/payments/initiate` → creates payment record
3. **Simulate Payment** → `POST /api/v1/payments/{id}/simulate` → marks as `completed` or `failed`
4. **Refund Payment** → `POST /api/v1/payments/{id}/refund` → marks as `refunded`

### Payment Statuses

- `pending` — Payment initiated, awaiting processing
- `completed` — Payment successful
- `failed` — Payment failed
- `refunded` — Payment refunded

### Audit Trail

All payment actions (initiate, complete, fail, refund) are logged to the audit log with user ID, IP address, and user agent.

---

## Background Jobs

The system runs automatic background jobs using **APScheduler**:

| Job | Frequency | Description |
|-----|-----------|-------------|
| Event Status Update | Every 1 hour | Auto-updates past events to `COMPLETED` status |
| Token Cleanup | Every 24 hours | Removes expired tokens from blacklist |
| Reset Token Cleanup | Every 12 hours | Removes expired password reset tokens |
| Verification Token Cleanup | Every 24 hours | Removes expired email verification tokens |
| Waitlist Cleanup | Every 1 hour | Removes expired waitlist notifications |

---

## Security Features

| Feature | Description |
|---------|-------------|
| Password Hashing | bcrypt with salt |
| JWT Tokens | Access tokens (30 min) and refresh tokens (7 days) |
| Token Blacklist | Revoked tokens are blacklisted and rejected |
| Email Verification | Optional block on unverified emails |
| Refresh Token Rotation | Old tokens blacklisted on refresh |
| Input Validation | Pydantic schemas with field validators |
| SQL Injection Protection | SQLAlchemy ORM (parameterized queries) |
| CORS | Configurable allowed origins |
| Row-Level Locking | `SELECT ... FOR UPDATE` prevents seat overselling |
| Audit Logging | Every action tracked with IP and user agent |
| Soft Delete | Data preserved instead of deleted |

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

| Code | Description |
|------|-------------|
| `INVALID_CREDENTIALS` | Wrong username/password |
| `INVALID_TOKEN` | Invalid or expired JWT token |
| `PERMISSION_DENIED` | Insufficient permissions |
| `EMAIL_ALREADY_EXISTS` | Email already registered |
| `USERNAME_ALREADY_EXISTS` | Username already taken |
| `EVENT_NOT_FOUND` | Event doesn't exist |
| `INSUFFICIENT_SEATS` | Not enough seats available |
| `BOOKING_NOT_FOUND` | Booking not found |
| `CATEGORY_NOT_FOUND` | Category not found |
| `VALIDATION_ERROR` | Request validation failed |

---

## Pagination

All list endpoints support pagination with query parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `page` | `1` | Page number (starts at 1) |
| `limit` | `10` | Items per page (max 100) |

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

The project includes **375 tests** covering unit, integration, and OAuth scenarios.

### Test Structure

```
tests/
├── conftest.py                    # Shared fixtures (in-memory SQLite, TestClient, users)
├── unit/                          # 6 files — isolated function-level tests
├── oauth/                         # 3 files — mocked HTTP OAuth flows
├── integration/                   # 11 files — full API endpoint tests
└── fixtures/                      # 4 files — test data factories
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
| httpx | 0.25.0 | Async HTTP client |
| requests | 2.31.0 | OAuth mock responses |

### Running Tests

```bash
# Run all 375 tests
pytest

# With coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/integration/test_payments.py -v

# Run by marker
pytest -m payments
pytest -m integration

# Verbose output with short traceback
pytest -v --tb=short
```

### Test Configuration

- **Database**: In-memory SQLite (`sqlite:///:memory:`) with `StaticPool` for thread safety
- **Isolation**: Each test gets a fresh database session with rollback after completion
- **Environment**: Loads `.env.test` which disables email verification and uses fake OAuth credentials
- **Fixtures**: Provides `client` (TestClient), `db` (DB session), `test_user`, `test_admin`, `user_token`, `admin_token`, auth headers

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
        json={"title": "Test Event", "description": "...", ...},
        headers=admin_auth_headers
    )
    assert response.status_code == 201
    assert response.json()["success"] is True
```

### Available Pytest Markers

Defined in `pytest.ini`:

- `unit` — Fast unit tests
- `integration` — API endpoint tests
- `oauth` — OAuth service tests
- `payments` — Payment system tests

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Module not found | Run `pip install -r requirements.txt` |
| Database locked | Delete `event_management.db` and restart |
| Email not sending | Generate a new Gmail App Password, or leave SMTP fields empty to auto-disable in dev mode |
| Token expired | Use `POST /api/v1/auth/refresh` to get new tokens |
| Port in use | Change `PORT` in `.env` or kill the process on port 8000 |
| CORS error | Update allowed origins in the CORS middleware in `app/main.py` |
| Migration conflicts | Delete the database and restart (migrations auto-run) |
| OAuth callback fails | Ensure redirect URIs match exactly between your OAuth provider config and `.env` |
| Secret key warning | Run `python setup.py` to generate a secure key |

---

## Default Admin Account

On first run, the system automatically creates a default admin account:

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `Admin@1234` |
| Email | `admin@example.com` |

> **Important:** Change the default password immediately after first login!

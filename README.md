# Event Management System

A comprehensive Event Management System built with FastAPI, featuring JWT authentication, OAuth integrations (Google & LinkedIn), role-based access control, email verification, password reset, booking management, and more.

## Features

### Authentication & Authorization
- **JWT Authentication** - Access and refresh tokens with expiry handling
- **Role-Based Access Control** - Admin and User roles with different permissions
- **Email Verification** - Verify user emails during registration
- **Password Reset Flow** - Forgot password with email reset links
- **Google OAuth Login** - Sign in with Google account
- **LinkedIn OAuth Login** - Sign in with LinkedIn account
- **Token Blacklist** - Secure logout functionality

### User Management
- User registration and login
- Profile update (first name, last name, email, phone, bio, timezone)
- Password change functionality
- Account activation/deactivation (Admin only)
- Profile picture support

### Event Management
- Create, read, update, delete events (Admin only)
- Event fields: title, description, location, date/time, total seats, available seats, price, status, image URL
- Event statuses: UPCOMING, COMPLETED, CANCELLED
- Search and filter events (by title, category, location, price range, date range, status)
- Pagination support for event lists

### Booking System
- Book events with seat availability validation
- Automatic seat count management (decrease on booking, increase on cancellation)
- View user's own bookings
- Cancel own bookings
- Admin can view all bookings and cancel any booking
- Booking summary with total spent

### Category Management
- Create, read, update, delete event categories (Admin only)
- Soft delete categories (is_active flag)

### Additional Features
- Pagination for all list endpoints
- Background scheduler for event status auto-updates
- Token cleanup jobs (blacklist, reset tokens, verification tokens)
- Email notifications (verification, password reset, booking confirmations)
- Standardized API responses
- Comprehensive error handling

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Programming language |
| FastAPI | 0.104.1 | Web framework |
| SQLAlchemy | 2.0.23 | ORM for database |
| SQLite | - | Database (development) |
| Pydantic | 2.5.0 | Data validation |
| PyJWT | 2.8.0 | JWT token handling |
| bcrypt | 4.1.1 | Password hashing |
| APScheduler | 3.10.4 | Background jobs |
| Authlib | 1.2.1 | OAuth integration |
| Uvicorn | 0.24.0 | ASGI server |

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
│   │   ├── event.py                     # Event model
│   │   ├── booking.py                   # Booking model
│   │   ├── category.py                  # Category model
│   │   ├── token_blacklist.py           # Token blacklist model
│   │   ├── password_reset_token.py      # Password reset tokens
│   │   └── email_verification_token.py  # Email verification tokens
│   │
│   ├── schemas/                         # Pydantic models
│   │   ├── __init__.py
│   │   ├── auth.py                      # Authentication schemas
│   │   ├── user.py                      # User schemas
│   │   ├── event.py                     # Event schemas
│   │   ├── booking.py                   # Booking schemas
│   │   └── category.py                  # Category schemas
│   │
│   ├── routers/                         # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py                      # Login, register, refresh, logout
│   │   ├── users.py                     # User profile & management
│   │   ├── events.py                    # Event CRUD & search
│   │   ├── bookings.py                  # Booking operations
│   │   ├── categories.py                # Category management
│   │   └── oauth.py                     # Google & LinkedIn OAuth
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
│   │   └── linkedin_oauth_service.py    # LinkedIn OAuth logic
│   │
│   ├── dependencies/                    # FastAPI dependencies
│   │   ├── __init__.py
│   │   ├── auth.py                      # get_current_user, get_current_admin
│   │   └── db.py                        # get_db session
│   │
│   ├── pagination/                      # Pagination module
│   │   ├── __init__.py
│   │   └── pagination.py               # PaginationParams, paginate_query
│   │
│   └── utils/                           # Utility functions
│       ├── __init__.py
│       ├── auth_utils.py                # Password hashing & verification
│       ├── response.py                  # Standardized API responses
│       ├── error_handlers.py            # Global exception handlers
│       ├── validators.py                # Input validation functions
│       └── datetime_utils.py           # Datetime utilities
│
├── .env                                 # Environment variables
├── .gitignore                           # Git ignore file
├── requirements.txt                     # Project dependencies
├── run.py                               # Server startup script
└── README.md                            # This file
```


## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git (optional, for version control)
- Gmail account (for email notifications)
- Google Developer account (for Google OAuth)
- LinkedIn Developer account (for LinkedIn OAuth)

## Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd event-management-system
```
## Step 2: Create Virtual Environment
## Windows
```
python -m venv venv
venv\Scripts\activate
```
## macOS/Linux:
```
python3 -m venv venv
source venv/bin/activate
```
## Step 3: Install Dependencies
```
pip install -r requirements.txt
```
## Step 4: Configure Environment Variables
Create a .env file in the project root with the following configuration:

```
# Application
APP_NAME="Event Management System"
APP_VERSION="1.0.0"
DEBUG=True
API_PREFIX="/api/v1"

# Database
DATABASE_URL="sqlite:///./event_management.db"

# JWT Configuration
SECRET_KEY="your-super-secret-key-change-this-in-production"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Server
HOST="0.0.0.0"
PORT=8000

# Default Admin Credentials
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
EMAIL_HOST_PASSWORD="your-gmail-app-password"

# Google OAuth Configuration
GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
GOOGLE_REDIRECT_URI="http://localhost:8000/api/v1/auth/google/callback"

# LinkedIn OAuth Configuration
LINKEDIN_CLIENT_ID="your-linkedin-client-id"
LINKEDIN_CLIENT_SECRET="your-linkedin-client-secret"
LINKEDIN_REDIRECT_URI="http://localhost:8000/api/v1/auth/linkedin/callback"

# Email Verification
VERIFICATION_TOKEN_EXPIRE_MINUTES=1440
REQUIRE_EMAIL_VERIFICATION=True
RESET_TOKEN_EXPIRE_MINUTES=30
```
## Step 5: Run the Application
uing Uvicorn directly:
```
uvicorn app.main:app --reload
```
## Step 6: Access the Application
```
API Documentation (Swagger UI): http://localhost:8000/docs

Alternative Documentation (ReDoc): http://localhost:8000/redoc

Health Check: http://localhost:8000/health
```
## OAuth Setup Guides
Google OAuth Setup
Go to Google Cloud Console

Create a new project or select existing one

Enable the People API

## Configure OAuth consent screen:
User Type: External

App name: Event Management System

Scopes: email, profile, openid

Create OAuth 2.0 Client ID:

Application type: Web application

Redirect URI: http://localhost:8000/api/v1/auth/google/callback

Copy Client ID and Client Secret to your .env file

## LinkedIn OAuth Setup
Go to LinkedIn Developer Portal

Create a new app

Enable Sign In with LinkedIn using OpenID Connect product

Configure OAuth 2.0 settings:

Redirect URL: http://localhost:8000/api/v1/auth/linkedin/callback

Copy Client ID and Client Secret to your .env file

## API Endpoints
```
Authentication
Method	Endpoint	Description	Auth Required
POST	/api/v1/auth/register	Register new user	No
POST	/api/v1/auth/login	Login with username/password	No
POST	/api/v1/auth/verify-email	Verify email with token	No
POST	/api/v1/auth/resend-verification	Resend verification email	No
POST	/api/v1/auth/forgot-password	Request password reset	No
POST	/api/v1/auth/reset-password	Reset password with token	No
POST	/api/v1/auth/refresh	Refresh access token	No
POST	/api/v1/auth/logout	Logout and blacklist tokens	Yes
GET	/api/v1/auth/google/login	Google OAuth login	No
GET	/api/v1/auth/google/callback	Google OAuth callback	No
GET	/api/v1/auth/linkedin/login	LinkedIn OAuth login	No
GET	/api/v1/auth/linkedin/callback	LinkedIn OAuth callback	No
```
## Users
```
Method	Endpoint	Description	Auth Required
GET	/api/v1/users/me	Get current user profile	Yes
PUT	/api/v1/users/me	Update current user profile	Yes
POST	/api/v1/users/me/change-password	Change password	Yes
GET	/api/v1/users/	Get all users (Admin only)	Admin
GET	/api/v1/users/{user_id}	Get user by ID (Admin only)	Admin
PUT	/api/v1/users/{user_id}/deactivate	Deactivate user (Admin only)	Admin
PUT	/api/v1/users/{user_id}/activate	Activate user (Admin only)	Admin
```
## Events
```

Method	Endpoint	Description	Auth Required
GET	/api/v1/events	Get all events (with filters)	No (Optional)
GET	/api/v1/events/{event_id}	Get event by ID	No (Optional)
POST	/api/v1/events	Create event (Admin only)	Admin
PUT	/api/v1/events/{event_id}	Update event (Admin only)	Admin
DELETE	/api/v1/events/{event_id}	Delete event (Admin only)	Admin
```
## Categories
```
Method	Endpoint	Description	Auth Required
GET	/api/v1/categories	Get all categories	No (Optional)
GET	/api/v1/categories/{category_id}	Get category by ID	No (Optional)
POST	/api/v1/categories	Create category (Admin only)	Admin
PUT	/api/v1/categories/{category_id}	Update category (Admin only)	Admin
DELETE	/api/v1/categories/{category_id}	Delete category (Admin only)	Admin
```
## Bookings
```
Method	Endpoint	Description	Auth Required
POST	/api/v1/bookings	Book an event	Yes
GET	/api/v1/bookings/me	Get current user's bookings	Yes
GET	/api/v1/bookings/me/summary	Get booking summary	Yes
POST	/api/v1/bookings/{booking_id}/cancel	Cancel a booking	Yes
GET	/api/v1/bookings/	Get all bookings (Admin only)	Admin
GET	/api/v1/bookings/events/{event_id}	Get event bookings (Admin only)	Admin
```
## Background Jobs
The system runs automatic background jobs using APScheduler:

Job	Frequency	Description
Event Status Update	Every 1 hour	Auto-updates past events to COMPLETED status
Token Cleanup	Every 24 hours	Removes expired tokens from blacklist
Reset Token Cleanup	Every 12 hours	Removes expired password reset tokens
Verification Token Cleanup	Every 24 hours	Removes expired email verification tokens


## Security Features
Password Hashing: bcrypt with salt

JWT Tokens: Access tokens (30 min) and refresh tokens (7 days)

Token Blacklist: Revoked tokens are blacklisted

Email Verification: Required before login

Refresh Token Rotation: Old refresh tokens are blacklisted on refresh

Input Validation: Pydantic schemas with field validators

SQL Injection Protection: SQLAlchemy ORM

CORS: Configured for security

## Error Responses
```
{
  "success": false,
  "message": "Error description",
  "error_code": "ERROR_CODE"
}
```
## Common error codes:
INVALID_CREDENTIALS - Wrong username/password

INVALID_TOKEN - Invalid or expired JWT token

PERMISSION_DENIED - Insufficient permissions

EMAIL_ALREADY_EXISTS - Email already registered

USERNAME_ALREADY_EXISTS - Username already taken

EVENT_NOT_FOUND - Event doesn't exist

INSUFFICIENT_SEATS - Not enough seats available

## Pagination
All list endpoints support pagination with query parameters:

Parameter	Default	Description
page	1	Page number (starts at 1)
limit	10	Items per page (max 100).

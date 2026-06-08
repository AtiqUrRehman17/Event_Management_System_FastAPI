# Event Management System

A comprehensive REST API for managing events, bookings, and users built with FastAPI framework.
The system supports two roles (Admin and User) with JWT-based authentication, token blacklisting,
and automated event status management.

---

## Table of Contents

- [Event Management System](#event-management-system)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
    - [Authentication](#authentication)
    - [User Management](#user-management)
    - [Event Management](#event-management)
    - [Booking Management](#booking-management)
    - [Category Management](#category-management)
    - [Background Jobs](#background-jobs)
  - [Tech Stack](#tech-stack)
  - [Project Structure](#project-structure)

---

## Features

### Authentication
- User registration with unique username and email
- Login with username and password
- JWT access token (short-lived: 30 minutes)
- JWT refresh token (long-lived: 7 days)
- Token blacklisting on logout
- Token rotation on refresh
- Protected APIs using Bearer token

### User Management
- Two roles: Admin and User
- User profile view and update
- Admin can view, activate, and deactivate users
- Search and filter users (Admin only)

### Event Management
- Full CRUD for events (Admin only)
- Public event listing with search and filters
- Filter by category, location, price range, date range, status
- Auto status update (upcoming → completed) via scheduler
- Manual status update with transition validation
- Optional event image URL

### Booking Management
- Book events with seat selection
- Cancel own bookings (User)
- Cancel any booking (Admin)
- View own bookings with pagination
- View booking summary with total spent
- Seat management (decrease on book, increase on cancel)

### Category Management
- Full CRUD for categories (Admin only)
- Public category listing
- Soft deactivation support

### Background Jobs
- Auto event status update every hour
- Expired blacklisted token cleanup every 24 hours

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.12 | Programming language |
| FastAPI | Web framework |
| SQLAlchemy | ORM for database |
| SQLite | Database (default) |
| Pydantic v2 | Data validation |
| PyJWT | JWT token handling |
| bcrypt | Password hashing |
| APScheduler | Background job scheduling |
| Uvicorn | ASGI server |

---

## Project Structure
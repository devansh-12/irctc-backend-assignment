# IRCTC Backend API

A RESTful backend API for a simplified train booking system built with Django REST Framework.

## Features

- **User Authentication**: JWT-based registration, login, token refresh
- **Train Management**: Search trains, admin-only creation/update
- **Seat Booking**: Book seats with race condition handling (optimistic locking)
- **Analytics**: Top routes, API logs with production-ready filtering

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | Django 5.0 + DRF |
| Database | SQLite (dev) / MySQL (prod) |
| Logging | MongoDB |
| Auth | JWT (SimpleJWT) |
| Docs | Swagger UI |

---

## Design Decisions

<!-- TODO: Add design decisions here -->

---

## Database Schema

### ER Diagram (MySQL)

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────────┐
│   USERS     │       │     TRAINS       │       │ TRAIN_SCHEDULES │
├─────────────┤       ├──────────────────┤       ├─────────────────┤
│ id (PK)     │       │ id (PK)          │       │ id (PK)         │
│ email       │       │ train_number     │──┐    │ train_id (FK)   │──┐
│ name        │       │ train_name       │  │    │ source          │  │
│ phone       │       │ total_seats      │  │    │ destination     │  │
│ is_admin    │       │ is_active        │  │    │ departure_time  │  │
│ password    │       │ created_at       │  │    │ arrival_time    │  │
│ created_at  │       └──────────────────┘  │    │ base_fare       │  │
└─────────────┘                             │    │ runs_on         │  │
      │                                     │    │ is_active       │  │
      │                                     │    └─────────────────┘  │
      │                                     │            │            │
      │                                     └────────────┘            │
      │                                                               │
      │       ┌─────────────────┐       ┌─────────────────────┐      │
      │       │    BOOKINGS     │       │  SEAT_AVAILABILITY  │      │
      │       ├─────────────────┤       ├─────────────────────┤      │
      └──────▶│ id (PK)         │       │ id (PK)             │◀─────┘
              │ pnr (unique)    │       │ schedule_id (FK)    │
              │ user_id (FK)    │       │ booked_seats        │
              │ schedule_id (FK)│───────│ version (lock)      │
              │ num_passengers  │       │ updated_at          │
              │ total_fare      │       └─────────────────────┘
              │ status          │
              │ booking_date    │
              └─────────────────┘
                      │
                      │
              ┌───────▼───────┐
              │  PASSENGERS   │
              ├───────────────┤
              │ id (PK)       │
              │ booking_id(FK)│
              │ name          │
              │ age           │
              │ gender        │
              │ seat_number   │
              └───────────────┘
```

### MongoDB Schema (API Logs)

```json
// Collection: api_logs
{
  "_id": ObjectId("..."),
  "endpoint": "/api/trains/search/",
  "method": "GET",
  "user_id": 1,
  "request_params": {
    "source": "Delhi",
    "destination": "Mumbai"
  },
  "response_status": 200,
  "execution_time_ms": 45.23,
  "results_count": 5,
  "timestamp": ISODate("2026-01-08T10:30:00Z")
}

// Collection: route_analytics (aggregated)
{
  "_id": ObjectId("..."),
  "source": "Delhi",
  "destination": "Mumbai",
  "search_count": 150,
  "last_updated": ISODate("2026-01-08T12:00:00Z")
}
```

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone <repo-url>
cd irctc-backend-assignment

# Start all services (Django + MySQL + MongoDB)
docker-compose up --build

# Access:
# - API: http://localhost:8000
# - Swagger UI: http://localhost:8000/api/docs/
```

### Option 2: Local Development

```bash
# Clone and setup
git clone <repo-url>
cd irctc-backend-assignment

# Virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env

# Run migrations
python manage.py migrate

# Seed sample data
python manage.py seed_db

# Start server
python manage.py runserver
```

---

## End-to-End Usage

### 1. Access API Documentation
```
http://localhost:8000/api/docs/
```

### 2. Register a User
```bash
curl -X POST http://localhost:8000/api/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","name":"Test","password":"Test@123","password_confirm":"Test@123"}'
```

### 3. Login (Get Token)
```bash
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"Test@123"}'

# Response: {"tokens": {"access": "eyJ...", "refresh": "..."}}
```

### 4. Search Trains
```bash
curl -X GET "http://localhost:8000/api/trains/search/?source=Delhi&destination=Mumbai" \
  -H "Authorization: Bearer <access_token>"
```

### 5. Book Seats
```bash
curl -X POST http://localhost:8000/api/bookings/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"schedule_id":1,"passengers":[{"name":"John","age":30,"gender":"M"}]}'
```

### 6. View My Bookings
```bash
curl -X GET http://localhost:8000/api/bookings/my/ \
  -H "Authorization: Bearer <access_token>"
```

---

## Testing

```bash
# Run all tests (66 tests)
python manage.py test

# Run with verbosity
python manage.py test -v2

# Run specific app
python manage.py test core trains bookings analytics
```

---

## Test Credentials (after seeding)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@irctc.com | Admin@123 |
| User | john@example.com | User@123 |

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/register/` | - | Register user |
| POST | `/api/login/` | - | Login |
| POST | `/api/token/refresh/` | - | Refresh token |
| GET | `/api/profile/` | User | Get profile |
| GET | `/api/trains/search/` | User | Search trains |
| POST | `/api/trains/` | Admin | Create train |
| POST | `/api/bookings/` | User | Book seats |
| GET | `/api/bookings/my/` | User | My bookings |
| GET | `/api/analytics/top-routes/` | User | Top routes |
| GET | `/api/analytics/logs/` | Admin | API logs |
| GET | `/api/analytics/stats/` | Admin | Stats |

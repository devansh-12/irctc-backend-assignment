# IRCTC Backend Assignment

A simplified IRCTC backend system supporting user registration, authentication, train search, and booking built with Django REST Framework.

## Tech Stack

- **Backend**: Django 5.x / Django REST Framework
- **Primary Database**: MySQL (transactional data - users, trains, bookings)
- **Analytics Database**: MongoDB (API logs and analytics)
- **Authentication**: JWT (JSON Web Tokens)

## Features

- ✅ User registration and authentication with JWT tokens
- ✅ Train search with source, destination, and date filters
- ✅ Admin-only train creation/management
- ✅ Seat booking with availability validation and race condition handling
- ✅ View user's booking history
- ✅ Analytics for top searched routes (MongoDB aggregation)
- ✅ API request logging to MongoDB

## Project Structure

```
irctc-backend-assignment/
├── irctc_backend/          # Django project settings
│   ├── settings.py         # Configuration with MySQL, MongoDB, JWT
│   └── urls.py             # Main URL routing
├── core/                   # Authentication app
│   ├── models.py           # Custom User model
│   ├── serializers.py      # Registration/Login serializers
│   └── views.py            # Auth endpoints
├── trains/                 # Train management app
│   ├── models.py           # Train, TrainSchedule, SeatAvailability
│   ├── serializers.py      # Train serializers
│   ├── views.py            # Search and manage endpoints
│   └── permissions.py      # Admin permission class
├── bookings/               # Booking management app
│   ├── models.py           # Booking, Passenger models
│   ├── serializers.py      # Booking serializers with validation
│   └── views.py            # Booking endpoints
├── analytics/              # Analytics app
│   └── views.py            # Top routes endpoint
├── utils/                  # Utilities
│   ├── mongo.py            # MongoDB connection and helpers
│   └── middleware.py       # API logging middleware
├── requirements.txt
└── .env.example
```

## Setup Instructions

### Prerequisites

- Python 3.10+
- MySQL Server
- MongoDB Server
- pip (Python package manager)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd irctc-backend-assignment
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your database credentials:

```env
# Django
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# MySQL Database
MYSQL_DATABASE=irctc_db
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password
MYSQL_HOST=localhost
MYSQL_PORT=3306

# MongoDB
MONGODB_URI=mongodb://localhost:27017/
MONGODB_NAME=irctc_logs

# JWT Settings
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
```

### 5. Create MySQL Database

```sql
CREATE DATABASE irctc_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 6. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create Admin User (Optional)

```bash
python manage.py createsuperuser
```

### 8. Run Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

---

## API Documentation

### Authentication APIs

#### Register User
```http
POST /api/register/
Content-Type: application/json

{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "phone": "9876543210"
}
```

**Response:**
```json
{
    "message": "User registered successfully",
    "user": {
        "id": 1,
        "email": "john@example.com",
        "name": "John Doe",
        "phone": "9876543210",
        "is_admin": false,
        "created_at": "2026-01-07T17:00:00Z"
    },
    "tokens": {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
}
```

#### Login
```http
POST /api/login/
Content-Type: application/json

{
    "email": "john@example.com",
    "password": "SecurePass123!"
}
```

**Response:**
```json
{
    "message": "Login successful",
    "user": {
        "id": 1,
        "email": "john@example.com",
        "name": "John Doe"
    },
    "tokens": {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
}
```

#### Refresh Token
```http
POST /api/token/refresh/
Content-Type: application/json

{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

---

### Train APIs

> **Note:** All train APIs require authentication. Include the JWT token in the Authorization header:
> `Authorization: Bearer <access_token>`

#### Search Trains
```http
GET /api/trains/search/?source=Delhi&destination=Mumbai&date=2026-01-15&limit=10&offset=0
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "count": 2,
    "limit": 10,
    "offset": 0,
    "results": [
        {
            "id": 1,
            "train_number": "12951",
            "train_name": "Mumbai Rajdhani",
            "source": "Delhi",
            "destination": "Mumbai",
            "departure_time": "16:55:00",
            "arrival_time": "08:35:00",
            "base_fare": "2500.00",
            "runs_on": "2026-01-15",
            "total_seats": 500,
            "available_seats": 450
        }
    ]
}
```

#### Create/Update Train (Admin Only)
```http
POST /api/trains/
Authorization: Bearer <admin_access_token>
Content-Type: application/json

{
    "train_number": "12951",
    "train_name": "Mumbai Rajdhani",
    "total_seats": 500,
    "source": "Delhi",
    "destination": "Mumbai",
    "departure_time": "16:55:00",
    "arrival_time": "08:35:00",
    "base_fare": 2500.00,
    "runs_on": "2026-01-15"
}
```

**Response:**
```json
{
    "message": "Train created successfully",
    "train": {
        "id": 1,
        "train_number": "12951",
        "train_name": "Mumbai Rajdhani",
        "total_seats": 500
    },
    "schedule": {
        "id": 1,
        "source": "Delhi",
        "destination": "Mumbai",
        "departure_time": "16:55:00",
        "arrival_time": "08:35:00",
        "base_fare": "2500.00",
        "runs_on": "2026-01-15"
    }
}
```

---

### Booking APIs

#### Book Seats
```http
POST /api/bookings/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "schedule_id": 1,
    "passengers": [
        {
            "name": "John Doe",
            "age": 30,
            "gender": "M"
        },
        {
            "name": "Jane Doe",
            "age": 28,
            "gender": "F"
        }
    ]
}
```

**Response:**
```json
{
    "message": "Booking confirmed successfully",
    "booking": {
        "id": 1,
        "pnr": "ABC1234XYZ",
        "schedule": 1,
        "num_passengers": 2,
        "total_fare": "5000.00",
        "status": "CONFIRMED",
        "booking_date": "2026-01-07T17:30:00Z",
        "confirmed_at": "2026-01-07T17:30:00Z",
        "passengers": [
            {
                "id": 1,
                "name": "John Doe",
                "age": 30,
                "gender": "M",
                "seat_number": 1
            },
            {
                "id": 2,
                "name": "Jane Doe",
                "age": 28,
                "gender": "F",
                "seat_number": 2
            }
        ],
        "train_details": {
            "train_number": "12951",
            "train_name": "Mumbai Rajdhani",
            "source": "Delhi",
            "destination": "Mumbai",
            "departure_time": "16:55:00",
            "arrival_time": "08:35:00",
            "travel_date": "2026-01-15",
            "base_fare": "2500.00"
        }
    }
}
```

#### Get My Bookings
```http
GET /api/bookings/my/
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "count": 1,
    "results": [
        {
            "id": 1,
            "pnr": "ABC1234XYZ",
            "num_passengers": 2,
            "total_fare": "5000.00",
            "status": "CONFIRMED",
            "booking_date": "2026-01-07T17:30:00Z",
            "train_details": {
                "train_number": "12951",
                "train_name": "Mumbai Rajdhani",
                "source": "Delhi",
                "destination": "Mumbai"
            }
        }
    ]
}
```

---

### Analytics API

#### Get Top Routes
```http
GET /api/analytics/top-routes/
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "count": 5,
    "results": [
        {
            "source": "Delhi",
            "destination": "Mumbai",
            "search_count": 1523
        },
        {
            "source": "Bangalore",
            "destination": "Chennai",
            "search_count": 892
        },
        {
            "source": "Kolkata",
            "destination": "Delhi",
            "search_count": 756
        },
        {
            "source": "Mumbai",
            "destination": "Pune",
            "search_count": 654
        },
        {
            "source": "Hyderabad",
            "destination": "Bangalore",
            "search_count": 543
        }
    ]
}
```

---

## MongoDB Log Samples

### API Logs Collection

```javascript
// Sample document in api_logs collection
{
    "_id": ObjectId("679d5e3f2b8c9a1234567890"),
    "endpoint": "/api/trains/search/",
    "method": "GET",
    "user_id": 1,
    "request_params": {
        "source": "Delhi",
        "destination": "Mumbai",
        "date": "2026-01-15",
        "limit": "10",
        "offset": "0"
    },
    "response_status": 200,
    "execution_time_ms": 145.5,
    "results_count": 5,
    "timestamp": ISODate("2026-01-07T13:12:15.123Z")
}
```

### View Logs in MongoDB Shell

```javascript
// Connect to MongoDB
mongosh "mongodb://localhost:27017/irctc_logs"

// View recent logs
db.api_logs.find().sort({timestamp: -1}).limit(10)

// View top routes aggregation
db.api_logs.aggregate([
    {$match: {"endpoint": "/api/trains/search/"}},
    {$group: {
        _id: {source: "$request_params.source", destination: "$request_params.destination"},
        count: {$sum: 1}
    }},
    {$sort: {count: -1}},
    {$limit: 5}
])
```

---

## Database Schema

### MySQL Tables

| Table | Description |
|-------|-------------|
| `users` | User accounts with email authentication |
| `refresh_tokens` | JWT refresh token management |
| `trains` | Train metadata (number, name, seats) |
| `train_schedules` | Schedule details (route, times, fare, date) |
| `seat_availability` | Real-time seat availability per schedule |
| `bookings` | Booking records with PNR |
| `passengers` | Passenger details per booking |

### MongoDB Collections

| Collection | Description |
|------------|-------------|
| `api_logs` | Request logs for train search API |
| `route_analytics` | Aggregated route search counts |

---

## Testing

### Run Tests
```bash
python manage.py test
```

### Quick API Test with cURL

```bash
# Register
curl -X POST http://localhost:8000/api/register/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","password":"Test@123!","password_confirm":"Test@123!"}'

# Login
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test@123!"}'

# Search trains (replace <token> with actual JWT)
curl -X GET "http://localhost:8000/api/trains/search/?source=Delhi&destination=Mumbai" \
  -H "Authorization: Bearer <token>"
```

---

## License

This project is for educational/assignment purposes.

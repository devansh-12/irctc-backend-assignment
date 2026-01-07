"""
MongoDB utility functions for API logging and analytics.
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from django.conf import settings
from datetime import datetime

# MongoDB client singleton
_mongo_client = None
_mongo_db = None
_mongo_available = None


def get_mongo_db():
    """Get MongoDB database instance (singleton pattern)."""
    global _mongo_client, _mongo_db, _mongo_available
    
    # If we already know MongoDB is unavailable, return None
    if _mongo_available is False:
        return None
    
    if _mongo_db is None:
        try:
            _mongo_client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=3000,  # 3 second timeout
                connectTimeoutMS=3000
            )
            # Test connection
            _mongo_client.admin.command('ping')
            _mongo_db = _mongo_client[settings.MONGODB_NAME]
            _mongo_available = True
            
            # Ensure indexes exist
            _ensure_indexes(_mongo_db)
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"MongoDB connection failed: {e}")
            _mongo_available = False
            return None
    
    return _mongo_db


def _ensure_indexes(db):
    """Create necessary indexes for MongoDB collections."""
    try:
        # API logs indexes
        api_logs = db.api_logs
        api_logs.create_index([("timestamp", -1)])
        api_logs.create_index([("endpoint", 1), ("timestamp", -1)])
        api_logs.create_index([("user_id", 1), ("timestamp", -1)])
        api_logs.create_index([("execution_time_ms", -1)])
        api_logs.create_index([
            ("request_params.source", 1),
            ("request_params.destination", 1)
        ])
        api_logs.create_index([("response_status", 1)])
        
        # Route analytics indexes
        route_analytics = db.route_analytics
        route_analytics.create_index([("search_count", -1)])
        route_analytics.create_index(
            [("source", 1), ("destination", 1)],
            unique=True
        )
    except Exception as e:
        print(f"Error creating MongoDB indexes: {e}")


def log_api_request(endpoint, method, user_id, request_params, 
                    response_status, execution_time_ms, results_count=None):
    """
    Log an API request to MongoDB.
    
    Args:
        endpoint: API endpoint path
        method: HTTP method (GET, POST, etc.)
        user_id: ID of the authenticated user
        request_params: Dictionary of request parameters
        response_status: HTTP response status code
        execution_time_ms: Execution time in milliseconds
        results_count: Number of results returned (optional)
    """
    db = get_mongo_db()
    if db is None:
        return  # MongoDB not available, skip logging
    
    log_entry = {
        "endpoint": endpoint,
        "method": method,
        "user_id": user_id,
        "request_params": request_params,
        "response_status": response_status,
        "execution_time_ms": execution_time_ms,
        "timestamp": datetime.utcnow()
    }
    
    if results_count is not None:
        log_entry["results_count"] = results_count
    
    try:
        db.api_logs.insert_one(log_entry)
        
        # Update route analytics if this is a train search
        if endpoint == '/api/trains/search/' and 'source' in request_params and 'destination' in request_params:
            update_route_analytics(
                request_params['source'],
                request_params['destination']
            )
    except Exception as e:
        print(f"Error logging to MongoDB: {e}")


def update_route_analytics(source, destination):
    """
    Update route analytics - increment search count for a source-destination pair.
    """
    db = get_mongo_db()
    if db is None:
        return
    
    try:
        db.route_analytics.update_one(
            {"source": source, "destination": destination},
            {
                "$inc": {"search_count": 1},
                "$set": {"last_updated": datetime.utcnow()}
            },
            upsert=True
        )
    except Exception as e:
        print(f"Error updating route analytics: {e}")


def get_top_routes(limit=5):
    """
    Get top searched routes using MongoDB aggregation.
    
    Args:
        limit: Number of top routes to return (default: 5)
    
    Returns:
        List of top routes with source, destination, and search_count
    """
    db = get_mongo_db()
    if db is None:
        return []  # Return empty list if MongoDB not available
    
    # Aggregate from api_logs for real-time data
    pipeline = [
        {
            "$match": {
                "endpoint": "/api/trains/search/",
                "request_params.source": {"$exists": True},
                "request_params.destination": {"$exists": True}
            }
        },
        {
            "$group": {
                "_id": {
                    "source": "$request_params.source",
                    "destination": "$request_params.destination"
                },
                "search_count": {"$sum": 1}
            }
        },
        {
            "$sort": {"search_count": -1}
        },
        {
            "$limit": limit
        },
        {
            "$project": {
                "_id": 0,
                "source": "$_id.source",
                "destination": "$_id.destination",
                "search_count": 1
            }
        }
    ]
    
    try:
        return list(db.api_logs.aggregate(pipeline))
    except Exception as e:
        print(f"Error getting top routes: {e}")
        return []


def get_api_logs(limit=100, endpoint=None, user_id=None):
    """
    Get recent API logs with optional filters.
    
    Args:
        limit: Maximum number of logs to return
        endpoint: Filter by endpoint (optional)
        user_id: Filter by user ID (optional)
    
    Returns:
        List of API log entries
    """
    db = get_mongo_db()
    if db is None:
        return []  # Return empty list if MongoDB not available
    
    query = {}
    if endpoint:
        query["endpoint"] = endpoint
    if user_id:
        query["user_id"] = user_id
    
    try:
        logs = db.api_logs.find(query).sort("timestamp", -1).limit(limit)
        
        # Convert to list and handle ObjectId serialization
        result = []
        for log in logs:
            log["_id"] = str(log["_id"])
            log["timestamp"] = log["timestamp"].isoformat()
            result.append(log)
        
        return result
    except Exception as e:
        print(f"Error getting API logs: {e}")
        return []


def is_mongodb_available():
    """Check if MongoDB is available."""
    global _mongo_available
    if _mongo_available is not None:
        return _mongo_available
    
    # Try to connect
    get_mongo_db()
    return _mongo_available or False

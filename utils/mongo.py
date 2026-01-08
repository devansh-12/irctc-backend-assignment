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


def get_api_logs(limit=100, offset=0, endpoint=None, user_id=None, 
                  status_code=None, method=None, min_time_ms=None,
                  start_date=None, end_date=None, sort='-timestamp'):
    """
    Production-ready API logs retrieval with advanced filtering.
    
    Args:
        limit: Maximum number of logs to return
        offset: Pagination offset
        endpoint: Filter by endpoint (e.g., '/api/trains/search/')
        user_id: Filter by user ID
        status_code: Filter by HTTP status code (200, 400, 500, etc.)
        method: Filter by HTTP method (GET, POST, etc.)
        min_time_ms: Filter by minimum execution time (for slow queries)
        start_date: Filter logs after this datetime
        end_date: Filter logs before this datetime
        sort: Sort field with direction (prefix - for descending)
    
    Returns:
        List of API log entries
    """
    db = get_mongo_db()
    if db is None:
        return []
    
    # Build query with filters
    query = {}
    
    if endpoint:
        query["endpoint"] = endpoint
    if user_id:
        query["user_id"] = user_id
    if status_code:
        query["response_status"] = status_code
    if method:
        query["method"] = method.upper()
    if min_time_ms:
        query["execution_time_ms"] = {"$gte": min_time_ms}
    
    # Date range filter
    if start_date or end_date:
        query["timestamp"] = {}
        if start_date:
            query["timestamp"]["$gte"] = start_date
        if end_date:
            query["timestamp"]["$lte"] = end_date
    
    # Parse sort field
    sort_field = sort.lstrip('-')
    sort_direction = -1 if sort.startswith('-') else 1
    
    try:
        cursor = db.api_logs.find(query).sort(sort_field, sort_direction).skip(offset).limit(limit)
        
        result = []
        for log in cursor:
            log["_id"] = str(log["_id"])
            if "timestamp" in log and hasattr(log["timestamp"], 'isoformat'):
                log["timestamp"] = log["timestamp"].isoformat()
            result.append(log)
        
        return result
    except Exception as e:
        print(f"Error getting API logs: {e}")
        return []


def get_log_stats(hours=24, endpoint=None):
    """
    Get aggregated log statistics for monitoring dashboards.
    
    Args:
        hours: Number of hours to analyze (default: 24)
        endpoint: Filter by specific endpoint
    
    Returns:
        Dictionary with aggregated statistics
    """
    db = get_mongo_db()
    if db is None:
        return {
            'total_requests': 0,
            'error_message': 'MongoDB not available'
        }
    
    from datetime import datetime, timedelta
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    match_stage = {"timestamp": {"$gte": cutoff_time}}
    if endpoint:
        match_stage["endpoint"] = endpoint
    
    pipeline = [
        {"$match": match_stage},
        {
            "$facet": {
                "total": [{"$count": "count"}],
                "by_status": [
                    {"$group": {"_id": "$response_status", "count": {"$sum": 1}}}
                ],
                "by_endpoint": [
                    {"$group": {"_id": "$endpoint", "count": {"$sum": 1}, "avg_time": {"$avg": "$execution_time_ms"}}},
                    {"$sort": {"count": -1}},
                    {"$limit": 10}
                ],
                "response_times": [
                    {"$group": {
                        "_id": None,
                        "avg_ms": {"$avg": "$execution_time_ms"},
                        "max_ms": {"$max": "$execution_time_ms"},
                        "min_ms": {"$min": "$execution_time_ms"}
                    }}
                ],
                "slow_queries": [
                    {"$match": {"execution_time_ms": {"$gte": 1000}}},  # >1 second
                    {"$count": "count"}
                ],
                "errors": [
                    {"$match": {"response_status": {"$gte": 400}}},
                    {"$count": "count"}
                ]
            }
        }
    ]
    
    try:
        result = list(db.api_logs.aggregate(pipeline))
        if not result:
            return {'total_requests': 0}
        
        stats = result[0]
        total = stats['total'][0]['count'] if stats['total'] else 0
        errors = stats['errors'][0]['count'] if stats['errors'] else 0
        slow = stats['slow_queries'][0]['count'] if stats['slow_queries'] else 0
        
        response_times = stats['response_times'][0] if stats['response_times'] else {}
        
        return {
            'total_requests': total,
            'error_count': errors,
            'error_rate': round((errors / total * 100), 2) if total > 0 else 0,
            'slow_queries_count': slow,
            'status_breakdown': {str(s['_id']): s['count'] for s in stats['by_status']},
            'response_time_ms': {
                'avg': round(response_times.get('avg_ms', 0), 2),
                'max': round(response_times.get('max_ms', 0), 2),
                'min': round(response_times.get('min_ms', 0), 2)
            },
            'top_endpoints': [
                {
                    'endpoint': e['_id'],
                    'requests': e['count'],
                    'avg_time_ms': round(e['avg_time'], 2) if e['avg_time'] else 0
                }
                for e in stats['by_endpoint']
            ]
        }
    except Exception as e:
        print(f"Error getting log stats: {e}")
        return {'total_requests': 0, 'error': str(e)}


def is_mongodb_available():
    """Check if MongoDB is available."""
    global _mongo_available
    if _mongo_available is not None:
        return _mongo_available
    
    get_mongo_db()
    return _mongo_available or False


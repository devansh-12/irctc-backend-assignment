"""
Custom middleware for API request logging.
"""
import time
from utils.mongo import log_api_request


class APILoggingMiddleware:
    """
    Middleware to log API requests to MongoDB.
    Currently logs train search requests as specified in requirements.
    """
    
    # Endpoints to log
    LOGGED_ENDPOINTS = ['/api/trains/search/']
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if this endpoint should be logged
        should_log = any(
            request.path.startswith(endpoint.rstrip('/'))
            for endpoint in self.LOGGED_ENDPOINTS
        )
        
        if should_log:
            start_time = time.time()
        
        # Process the request
        response = self.get_response(request)
        
        if should_log:
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Get user ID if authenticated
            user_id = None
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_id = request.user.id
            
            # Get request parameters
            request_params = {}
            if request.method == 'GET':
                request_params = dict(request.GET)
                # Flatten single-value lists
                request_params = {
                    k: v[0] if isinstance(v, list) and len(v) == 1 else v
                    for k, v in request_params.items()
                }
            
            # Get results count from response data if available
            results_count = None
            if hasattr(response, 'data'):
                if isinstance(response.data, dict) and 'results' in response.data:
                    results_count = len(response.data['results'])
                elif isinstance(response.data, list):
                    results_count = len(response.data)
            
            try:
                log_api_request(
                    endpoint=request.path,
                    method=request.method,
                    user_id=user_id,
                    request_params=request_params,
                    response_status=response.status_code,
                    execution_time_ms=round(execution_time_ms, 2),
                    results_count=results_count
                )
            except Exception as e:
                # Don't let logging errors affect the response
                print(f"Error logging API request: {e}")
        
        return response

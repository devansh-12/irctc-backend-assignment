"""
Analytics views with production-ready logging.

Production Log Access Pattern:
- Admins access logs via API, not directly via MongoDB shell
- Supports filtering, pagination, date ranges
- Returns structured JSON for dashboards/monitoring tools
"""
from datetime import datetime, timedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from utils.mongo import get_top_routes, get_api_logs, get_log_stats


class TopRoutesView(APIView):
    """
    GET /api/analytics/top-routes/?limit=5
    
    Returns top searched routes aggregated from MongoDB logs.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        limit = min(max(int(request.query_params.get('limit', 5)), 1), 20)
        
        try:
            top_routes = get_top_routes(limit=limit)
            return Response({
                'count': len(top_routes),
                'results': top_routes
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class APILogsView(APIView):
    """
    Production-ready API logs endpoint (Admin only).
    
    GET /api/analytics/logs/
    
    Query Parameters:
        endpoint    - Filter by endpoint (e.g., /api/trains/search/)
        user_id     - Filter by user ID
        status_code - Filter by HTTP status code (200, 400, 500, etc.)
        method      - Filter by HTTP method (GET, POST, etc.)
        start_date  - Filter logs after this date (ISO format: 2026-01-01)
        end_date    - Filter logs before this date (ISO format: 2026-01-08)
        min_time_ms - Filter by minimum execution time (for slow queries)
        limit       - Number of results (default: 50, max: 500)
        offset      - Pagination offset (default: 0)
        sort        - Sort field: timestamp, execution_time_ms (default: -timestamp)
    
    Example:
        GET /api/analytics/logs/?endpoint=/api/trains/search/&limit=50
        GET /api/analytics/logs/?status_code=500&start_date=2026-01-01
        GET /api/analytics/logs/?min_time_ms=1000  # Slow queries (>1s)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Admin check
        if not request.user.is_admin:
            return Response({
                'error': 'Admin access required',
                'message': 'This endpoint is restricted to administrators only.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Parse query parameters
        filters = self._parse_filters(request.query_params)
        
        try:
            logs = get_api_logs(**filters)
            
            return Response({
                'count': len(logs),
                'limit': filters['limit'],
                'offset': filters.get('offset', 0),
                'filters_applied': {k: v for k, v in filters.items() if v is not None and k not in ['limit', 'offset']},
                'results': logs
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _parse_filters(self, params):
        """Parse and validate query parameters."""
        filters = {
            'limit': min(max(int(params.get('limit', 50)), 1), 500),
            'offset': max(int(params.get('offset', 0)), 0),
            'endpoint': params.get('endpoint'),
            'user_id': self._parse_int(params.get('user_id')),
            'status_code': self._parse_int(params.get('status_code')),
            'method': params.get('method', '').upper() or None,
            'min_time_ms': self._parse_float(params.get('min_time_ms')),
            'start_date': self._parse_date(params.get('start_date')),
            'end_date': self._parse_date(params.get('end_date')),
            'sort': params.get('sort', '-timestamp'),
        }
        return filters
    
    def _parse_int(self, value):
        try:
            return int(value) if value else None
        except ValueError:
            return None
    
    def _parse_float(self, value):
        try:
            return float(value) if value else None
        except ValueError:
            return None
    
    def _parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


class LogStatsView(APIView):
    """
    Production monitoring: Aggregated log statistics (Admin only).
    
    GET /api/analytics/stats/
    
    Query Parameters:
        hours     - Stats for last N hours (default: 24)
        endpoint  - Filter by specific endpoint
    
    Returns:
        - Total requests
        - Requests by status code (success/error breakdown)
        - Average response time
        - Slowest endpoints
        - Error rate
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_admin:
            return Response({
                'error': 'Admin access required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        hours = min(max(int(request.query_params.get('hours', 24)), 1), 168)  # Max 7 days
        endpoint = request.query_params.get('endpoint')
        
        try:
            stats = get_log_stats(hours=hours, endpoint=endpoint)
            return Response({
                'period_hours': hours,
                'endpoint_filter': endpoint,
                'stats': stats
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

"""
Views for analytics endpoints.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from utils.mongo import get_top_routes, get_api_logs


class TopRoutesView(APIView):
    """
    API endpoint for top searched routes.
    
    GET /api/analytics/top-routes/
    - Aggregates data from MongoDB logs
    - Returns the top 5 most searched (source, destination) routes
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        limit = request.query_params.get('limit', 5)
        
        try:
            limit = int(limit)
            if limit < 1 or limit > 20:
                limit = 5
        except ValueError:
            limit = 5
        
        try:
            top_routes = get_top_routes(limit=limit)
            
            return Response({
                'count': len(top_routes),
                'results': top_routes
            })
        except Exception as e:
            return Response({
                'error': f'Failed to fetch analytics: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class APILogsView(APIView):
    """
    API endpoint for viewing API logs (Admin only).
    
    GET /api/analytics/logs/
    - Returns recent API logs from MongoDB
    - Supports filtering by endpoint and user_id
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Only admins can view logs
        if not request.user.is_admin:
            return Response({
                'error': 'Admin access required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        limit = request.query_params.get('limit', 100)
        endpoint = request.query_params.get('endpoint')
        user_id = request.query_params.get('user_id')
        
        try:
            limit = int(limit)
            if limit < 1 or limit > 500:
                limit = 100
        except ValueError:
            limit = 100
        
        if user_id:
            try:
                user_id = int(user_id)
            except ValueError:
                user_id = None
        
        try:
            logs = get_api_logs(limit=limit, endpoint=endpoint, user_id=user_id)
            
            return Response({
                'count': len(logs),
                'results': logs
            })
        except Exception as e:
            return Response({
                'error': f'Failed to fetch logs: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

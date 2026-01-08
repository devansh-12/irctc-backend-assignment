"""
Analytics views with production-ready logging and Swagger documentation.
"""
from datetime import datetime
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers as drf_serializers

from utils.mongo import get_top_routes, get_api_logs, get_log_stats


# Response serializers for Swagger
class RouteSerializer(drf_serializers.Serializer):
    source = drf_serializers.CharField()
    destination = drf_serializers.CharField()
    search_count = drf_serializers.IntegerField()


class TopRoutesResponseSerializer(drf_serializers.Serializer):
    count = drf_serializers.IntegerField()
    results = RouteSerializer(many=True)


class TopRoutesView(APIView):
    """Get top searched routes."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get top searched routes",
        description="Returns the most searched (source, destination) pairs aggregated from MongoDB logs",
        parameters=[
            OpenApiParameter(name='limit', type=int, required=False, description='Number of routes (default: 5, max: 20)')
        ],
        responses={200: TopRoutesResponseSerializer},
        tags=["Analytics"]
    )
    def get(self, request):
        try:
            limit = min(max(int(request.query_params.get('limit', 5)), 1), 20)
        except ValueError:
            limit = 5
        
        try:
            top_routes = get_top_routes(limit=limit)
            return Response({
                'count': len(top_routes),
                'results': top_routes
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class APILogsView(APIView):
    """Production API logs (Admin only)."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get API logs (Admin only)",
        description="Query API logs from MongoDB with filters. Supports pagination, date range, and status filtering.",
        parameters=[
            OpenApiParameter(name='endpoint', type=str, required=False, description='Filter by endpoint path'),
            OpenApiParameter(name='user_id', type=int, required=False, description='Filter by user ID'),
            OpenApiParameter(name='status_code', type=int, required=False, description='Filter by HTTP status (200/400/500)'),
            OpenApiParameter(name='method', type=str, required=False, description='Filter by HTTP method (GET/POST)'),
            OpenApiParameter(name='min_time_ms', type=float, required=False, description='Min execution time (for slow queries)'),
            OpenApiParameter(name='start_date', type=str, required=False, description='Start date (YYYY-MM-DD)'),
            OpenApiParameter(name='end_date', type=str, required=False, description='End date (YYYY-MM-DD)'),
            OpenApiParameter(name='limit', type=int, required=False, description='Results limit (default: 50, max: 500)'),
            OpenApiParameter(name='offset', type=int, required=False, description='Pagination offset'),
        ],
        responses={
            200: inline_serializer(name='LogsResponse', fields={
                'count': drf_serializers.IntegerField(),
                'limit': drf_serializers.IntegerField(),
                'offset': drf_serializers.IntegerField(),
                'results': drf_serializers.ListField()
            }),
            403: inline_serializer(name='Forbidden', fields={'error': drf_serializers.CharField()})
        },
        tags=["Analytics (Admin)"]
    )
    def get(self, request):
        if not request.user.is_admin:
            return Response({
                'error': 'Admin access required',
                'message': 'This endpoint is restricted to administrators only.'
            }, status=status.HTTP_403_FORBIDDEN)
        
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
        def parse_int(v): 
            try: return int(v) if v else None
            except: return None
        def parse_float(v):
            try: return float(v) if v else None
            except: return None
        def parse_date(v):
            try: return datetime.fromisoformat(v) if v else None
            except: return None
        
        return {
            'limit': min(max(int(params.get('limit', 50)), 1), 500),
            'offset': max(int(params.get('offset', 0)), 0),
            'endpoint': params.get('endpoint'),
            'user_id': parse_int(params.get('user_id')),
            'status_code': parse_int(params.get('status_code')),
            'method': params.get('method', '').upper() or None,
            'min_time_ms': parse_float(params.get('min_time_ms')),
            'start_date': parse_date(params.get('start_date')),
            'end_date': parse_date(params.get('end_date')),
            'sort': params.get('sort', '-timestamp'),
        }


class LogStatsView(APIView):
    """Aggregated statistics (Admin only)."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get log statistics (Admin only)",
        description="Returns aggregated statistics: total requests, error rate, slow queries, top endpoints",
        parameters=[
            OpenApiParameter(name='hours', type=int, required=False, description='Hours to analyze (default: 24, max: 168)'),
            OpenApiParameter(name='endpoint', type=str, required=False, description='Filter by endpoint'),
        ],
        responses={
            200: inline_serializer(name='StatsResponse', fields={
                'period_hours': drf_serializers.IntegerField(),
                'stats': inline_serializer(name='Stats', fields={
                    'total_requests': drf_serializers.IntegerField(),
                    'error_count': drf_serializers.IntegerField(),
                    'error_rate': drf_serializers.FloatField(),
                })
            })
        },
        tags=["Analytics (Admin)"]
    )
    def get(self, request):
        if not request.user.is_admin:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            hours = min(max(int(request.query_params.get('hours', 24)), 1), 168)
        except ValueError:
            hours = 24
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

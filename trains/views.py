"""
Views for train management and search.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch

from .models import Train, TrainSchedule, SeatAvailability
from .serializers import (
    TrainScheduleListSerializer,
    TrainWithScheduleSerializer,
    TrainSerializer
)
from .permissions import IsAdminUser


class TrainSearchView(APIView):
    """
    API endpoint for searching trains.
    
    GET /api/trains/search/?source=&destination=&date=&limit=&offset=
    - Search trains between two stations
    - Optional filters: date, limit, offset
    - Logs each request to MongoDB (handled by middleware)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        source = request.query_params.get('source', '').strip().title()
        destination = request.query_params.get('destination', '').strip().title()
        date = request.query_params.get('date')
        limit = request.query_params.get('limit', 10)
        offset = request.query_params.get('offset', 0)
        
        # Validate required parameters
        if not source or not destination:
            return Response({
                'error': 'Both source and destination are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse limit and offset
        try:
            limit = int(limit)
            offset = int(offset)
            if limit < 1 or limit > 100:
                limit = 10
            if offset < 0:
                offset = 0
        except ValueError:
            limit = 10
            offset = 0
        
        # Build query
        queryset = TrainSchedule.objects.filter(
            source__iexact=source,
            destination__iexact=destination,
            is_active=True,
            train__is_active=True
        ).select_related('train').prefetch_related(
            Prefetch('availability', queryset=SeatAvailability.objects.all())
        )
        
        # Filter by date if provided
        if date:
            queryset = queryset.filter(runs_on=date)
        
        # Order by departure time
        queryset = queryset.order_by('runs_on', 'departure_time')
        
        # Apply pagination
        total_count = queryset.count()
        trains = queryset[offset:offset + limit]
        
        serializer = TrainScheduleListSerializer(trains, many=True)
        
        return Response({
            'count': total_count,
            'limit': limit,
            'offset': offset,
            'results': serializer.data
        })


class TrainManageView(APIView):
    """
    API endpoint for managing trains (Admin only).
    
    POST /api/trains/
    - Create or update train details
    - Includes train number, name, source, destination, times, seats, etc.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def post(self, request):
        serializer = TrainWithScheduleSerializer(data=request.data)
        
        if serializer.is_valid():
            result = serializer.save()
            
            train = result['train']
            schedule = result['schedule']
            created = result['created']
            
            return Response({
                'message': f"Train {'created' if created else 'updated'} successfully",
                'train': {
                    'id': train.id,
                    'train_number': train.train_number,
                    'train_name': train.train_name,
                    'total_seats': train.total_seats,
                },
                'schedule': {
                    'id': schedule.id,
                    'source': schedule.source,
                    'destination': schedule.destination,
                    'departure_time': str(schedule.departure_time),
                    'arrival_time': str(schedule.arrival_time),
                    'base_fare': str(schedule.base_fare),
                    'runs_on': str(schedule.runs_on),
                }
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request):
        """List all trains (Admin only)."""
        trains = Train.objects.filter(is_active=True).order_by('train_number')
        serializer = TrainSerializer(trains, many=True)
        return Response({
            'count': trains.count(),
            'results': serializer.data
        })

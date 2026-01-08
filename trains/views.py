"""Views for train management and search."""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch

from .models import Train, TrainSchedule, SeatAvailability
from .serializers import TrainScheduleListSerializer, TrainWithScheduleSerializer, TrainSerializer
from .permissions import IsAdminUser


class TrainSearchView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        source = request.query_params.get('source', '').strip().title()
        destination = request.query_params.get('destination', '').strip().title()
        date = request.query_params.get('date')
        limit = request.query_params.get('limit', 10)
        offset = request.query_params.get('offset', 0)
        
        if not source or not destination:
            return Response({'error': 'Both source and destination are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            limit = min(max(int(limit), 1), 100)
            offset = max(int(offset), 0)
        except ValueError:
            limit, offset = 10, 0
        
        queryset = TrainSchedule.objects.filter(
            source__iexact=source, destination__iexact=destination,
            is_active=True, train__is_active=True
        ).select_related('train').prefetch_related('availability')
        
        if date:
            queryset = queryset.filter(runs_on=date)
        
        queryset = queryset.order_by('runs_on', 'departure_time')
        total_count = queryset.count()
        trains = queryset[offset:offset + limit]
        
        return Response({
            'count': total_count, 'limit': limit, 'offset': offset,
            'results': TrainScheduleListSerializer(trains, many=True).data
        })


class TrainManageView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def post(self, request):
        serializer = TrainWithScheduleSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            train, schedule = result['train'], result['schedule']
            return Response({
                'message': f"Train {'created' if result['created'] else 'updated'} successfully",
                'train': {'id': train.id, 'train_number': train.train_number, 'train_name': train.train_name, 'total_seats': train.total_seats},
                'schedule': {'id': schedule.id, 'source': schedule.source, 'destination': schedule.destination,
                             'departure_time': str(schedule.departure_time), 'arrival_time': str(schedule.arrival_time),
                             'base_fare': str(schedule.base_fare), 'runs_on': str(schedule.runs_on)}
            }, status=status.HTTP_201_CREATED if result['created'] else status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request):
        trains = Train.objects.filter(is_active=True).order_by('train_number')
        return Response({'count': trains.count(), 'results': TrainSerializer(trains, many=True).data})

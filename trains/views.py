"""Views for train management and search."""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, inline_serializer
from rest_framework import serializers as drf_serializers

from .models import Train, TrainSchedule
from .serializers import TrainScheduleListSerializer, TrainWithScheduleSerializer, TrainSerializer
from .permissions import IsAdminUser


# Response serializers for Swagger
class TrainSearchResponseSerializer(drf_serializers.Serializer):
    count = drf_serializers.IntegerField()
    limit = drf_serializers.IntegerField()
    offset = drf_serializers.IntegerField()
    results = TrainScheduleListSerializer(many=True)


class TrainListResponseSerializer(drf_serializers.Serializer):
    count = drf_serializers.IntegerField()
    results = TrainSerializer(many=True)


class TrainSearchView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Search trains between stations",
        description="Search for available trains between source and destination stations. Logs request to MongoDB.",
        parameters=[
            OpenApiParameter(name='source', type=str, required=True, description='Source station (e.g., Delhi)'),
            OpenApiParameter(name='destination', type=str, required=True, description='Destination station (e.g., Mumbai)'),
            OpenApiParameter(name='date', type=str, required=False, description='Travel date (YYYY-MM-DD)'),
            OpenApiParameter(name='limit', type=int, required=False, description='Results per page (default: 10, max: 100)'),
            OpenApiParameter(name='offset', type=int, required=False, description='Pagination offset (default: 0)'),
        ],
        responses={200: TrainSearchResponseSerializer},
        tags=["Trains"]
    )
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
    
    @extend_schema(
        summary="Create train with schedule (Admin only)",
        description="Create a new train and its schedule. Requires admin privileges.",
        request=TrainWithScheduleSerializer,
        responses={201: inline_serializer(
            name='TrainCreateResponse',
            fields={
                'message': drf_serializers.CharField(),
                'train': inline_serializer(name='TrainInfo', fields={
                    'id': drf_serializers.IntegerField(),
                    'train_number': drf_serializers.CharField(),
                    'train_name': drf_serializers.CharField(),
                    'total_seats': drf_serializers.IntegerField(),
                }),
                'schedule': inline_serializer(name='ScheduleInfo', fields={
                    'id': drf_serializers.IntegerField(),
                    'source': drf_serializers.CharField(),
                    'destination': drf_serializers.CharField(),
                }),
            }
        )},
        examples=[
            OpenApiExample(
                "Create Train",
                value={
                    "train_number": "12951",
                    "train_name": "Mumbai Rajdhani",
                    "total_seats": 500,
                    "source": "Delhi",
                    "destination": "Mumbai",
                    "departure_time": "16:55:00",
                    "arrival_time": "08:35:00",
                    "base_fare": "2500.00",
                    "runs_on": "2026-01-15"
                },
                request_only=True
            )
        ],
        tags=["Trains (Admin)"]
    )
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
    
    @extend_schema(
        summary="List all trains (Admin only)",
        description="Get list of all active trains. Requires admin privileges.",
        responses={200: TrainListResponseSerializer},
        tags=["Trains (Admin)"]
    )
    def get(self, request):
        trains = Train.objects.filter(is_active=True).order_by('train_number')
        return Response({'count': trains.count(), 'results': TrainSerializer(trains, many=True).data})

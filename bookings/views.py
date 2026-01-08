"""Views for booking management."""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, inline_serializer
from rest_framework import serializers as drf_serializers

from .models import Booking
from .serializers import BookingSerializer, BookingCreateSerializer


# Response serializers for Swagger
class BookingResponseSerializer(drf_serializers.Serializer):
    message = drf_serializers.CharField()
    booking = BookingSerializer()


class BookingListResponseSerializer(drf_serializers.Serializer):
    count = drf_serializers.IntegerField()
    results = BookingSerializer(many=True)


class BookingCreateView(APIView):
    """Create a new booking."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Book seats on a train",
        description="Book seats on a given train schedule. Validates seat availability and creates passengers.",
        request=BookingCreateSerializer,
        responses={201: BookingResponseSerializer},
        examples=[
            OpenApiExample(
                "Book 2 passengers",
                value={
                    "schedule_id": 1,
                    "passengers": [
                        {"name": "John Doe", "age": 30, "gender": "M"},
                        {"name": "Jane Doe", "age": 28, "gender": "F"}
                    ]
                },
                request_only=True
            )
        ],
        tags=["Bookings"]
    )
    def post(self, request):
        serializer = BookingCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            try:
                booking = serializer.save()
                return Response({
                    'message': 'Booking confirmed successfully',
                    'booking': BookingSerializer(booking).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyBookingsView(APIView):
    """Get user's booking history."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get my bookings",
        description="Returns all bookings of the authenticated user with train details",
        responses={200: BookingListResponseSerializer},
        tags=["Bookings"]
    )
    def get(self, request):
        bookings = Booking.objects.filter(
            user=request.user
        ).select_related(
            'schedule__train'
        ).prefetch_related(
            'passengers'
        ).order_by('-booking_date')
        
        serializer = BookingSerializer(bookings, many=True)
        
        return Response({
            'count': bookings.count(),
            'results': serializer.data
        })


class BookingDetailView(APIView):
    """Get booking by PNR."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get booking by PNR",
        description="Returns booking details for the given PNR. User can only view their own bookings.",
        parameters=[
            OpenApiParameter(name='pnr', type=str, location='path', description='Booking PNR (10-character code)')
        ],
        responses={200: BookingSerializer, 404: inline_serializer(name='NotFound', fields={'error': drf_serializers.CharField()})},
        tags=["Bookings"]
    )
    def get(self, request, pnr):
        try:
            booking = Booking.objects.select_related(
                'schedule__train'
            ).prefetch_related(
                'passengers'
            ).get(
                pnr=pnr.upper(),
                user=request.user
            )
            
            serializer = BookingSerializer(booking)
            return Response(serializer.data)
        
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

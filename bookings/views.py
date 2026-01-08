"""
Views for booking management.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Booking
from .serializers import BookingSerializer, BookingCreateSerializer


class BookingCreateView(APIView):
    """
    API endpoint for creating bookings.
    
    POST /api/bookings/
    - Book seats on a given train
    - Validates seat availability before confirming
    - Deducts available seats once booking succeeds
    """
    permission_classes = [IsAuthenticated]
    
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
                return Response({
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyBookingsView(APIView):
    """
    API endpoint for viewing user's bookings.
    
    GET /api/bookings/my/
    - Returns all bookings of the logged-in user
    - Includes train details in response
    """
    permission_classes = [IsAuthenticated]
    
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
    """
    API endpoint for viewing a specific booking by PNR.
    
    GET /api/bookings/<pnr>/
    - Returns booking details for the given PNR
    - User can only view their own bookings
    """
    permission_classes = [IsAuthenticated]
    
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
            return Response({
                'error': 'Booking not found'
            }, status=status.HTTP_404_NOT_FOUND)

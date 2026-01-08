"""
Serializers for booking management.
"""
from rest_framework import serializers
from django.db import transaction
from django.utils import timezone

from .models import Booking, Passenger
from trains.models import TrainSchedule, SeatAvailability


class PassengerSerializer(serializers.ModelSerializer):
    """Serializer for Passenger model."""
    
    class Meta:
        model = Passenger
        fields = ['id', 'name', 'age', 'gender', 'seat_number']
        read_only_fields = ['id', 'seat_number']


class PassengerInputSerializer(serializers.Serializer):
    """Serializer for passenger input during booking."""
    name = serializers.CharField(max_length=255)
    age = serializers.IntegerField(min_value=1, max_value=120)
    gender = serializers.ChoiceField(choices=['M', 'F', 'O'])


class BookingSerializer(serializers.ModelSerializer):
    """Serializer for viewing bookings."""
    passengers = PassengerSerializer(many=True, read_only=True)
    train_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            'id', 'pnr', 'schedule', 'num_passengers', 'total_fare',
            'status', 'booking_date', 'confirmed_at', 'cancelled_at',
            'passengers', 'train_details'
        ]
    
    def get_train_details(self, obj):
        """Get train and schedule details."""
        schedule = obj.schedule
        return {
            'train_number': schedule.train.train_number,
            'train_name': schedule.train.train_name,
            'source': schedule.source,
            'destination': schedule.destination,
            'departure_time': str(schedule.departure_time),
            'arrival_time': str(schedule.arrival_time),
            'travel_date': str(schedule.runs_on),
            'base_fare': str(schedule.base_fare),
        }


class BookingCreateSerializer(serializers.Serializer):
    """Serializer for creating a booking."""
    schedule_id = serializers.IntegerField()
    passengers = PassengerInputSerializer(many=True)
    
    def validate_schedule_id(self, value):
        """Validate that schedule exists and is active."""
        try:
            schedule = TrainSchedule.objects.select_related('train').get(
                id=value,
                is_active=True,
                train__is_active=True
            )
            
            # Check if the schedule date is in the future
            if schedule.runs_on < timezone.now().date():
                raise serializers.ValidationError("Cannot book for past dates.")
            
            return schedule
        except TrainSchedule.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive schedule.")
    
    def validate_passengers(self, value):
        """Validate passenger list."""
        if not value:
            raise serializers.ValidationError("At least one passenger is required.")
        if len(value) > 6:
            raise serializers.ValidationError("Maximum 6 passengers allowed per booking.")
        return value
    
    def validate(self, attrs):
        """Validate seat availability (without locking - lock in create())."""
        schedule = attrs['schedule_id']
        num_passengers = len(attrs['passengers'])
        
        # Check seat availability (no lock here - just a preliminary check)
        # The actual locked check happens in create() inside transaction.atomic()
        try:
            availability = SeatAvailability.objects.get(schedule=schedule)
            if not availability.can_book(num_passengers):
                raise serializers.ValidationError({
                    'passengers': f"Only {availability.available_seats} seats available."
                })
        except SeatAvailability.DoesNotExist:
            raise serializers.ValidationError({
                'schedule_id': "Seat availability not found for this schedule."
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create booking with passengers and update seat availability."""
        schedule = validated_data['schedule_id']
        passengers_data = validated_data['passengers']
        user = self.context['request'].user
        
        num_passengers = len(passengers_data)
        total_fare = schedule.base_fare * num_passengers
        
        with transaction.atomic():
            # Re-fetch availability with lock to prevent race conditions
            availability = SeatAvailability.objects.select_for_update().get(
                schedule=schedule
            )
            
            # Double-check availability (optimistic locking)
            if not availability.can_book(num_passengers):
                raise serializers.ValidationError({
                    'passengers': f"Seats are no longer available. Only {availability.available_seats} seats left."
                })
            
            # Create booking
            booking = Booking.objects.create(
                user=user,
                schedule=schedule,
                num_passengers=num_passengers,
                total_fare=total_fare,
                status='CONFIRMED',
                confirmed_at=timezone.now()
            )
            
            # Create passengers with seat numbers
            current_booked = availability.booked_seats
            for i, passenger_data in enumerate(passengers_data):
                seat_number = current_booked + i + 1
                Passenger.objects.create(
                    booking=booking,
                    name=passenger_data['name'],
                    age=passenger_data['age'],
                    gender=passenger_data['gender'],
                    seat_number=seat_number
                )
            
            # Update seat availability with optimistic locking
            updated = SeatAvailability.objects.filter(
                id=availability.id,
                version=availability.version
            ).update(
                booked_seats=availability.booked_seats + num_passengers,
                version=availability.version + 1
            )
            
            if updated == 0:
                # Another transaction modified the availability
                raise serializers.ValidationError({
                    'passengers': "Booking failed due to concurrent booking. Please try again."
                })
        
        return booking

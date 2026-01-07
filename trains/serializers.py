"""
Serializers for train management.
"""
from rest_framework import serializers
from .models import Train, TrainSchedule, SeatAvailability


class TrainSerializer(serializers.ModelSerializer):
    """Serializer for Train model."""
    
    class Meta:
        model = Train
        fields = ['id', 'train_number', 'train_name', 'total_seats', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class SeatAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for SeatAvailability model."""
    available_seats = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = SeatAvailability
        fields = ['booked_seats', 'available_seats', 'updated_at']


class TrainScheduleSerializer(serializers.ModelSerializer):
    """Serializer for TrainSchedule model."""
    train = TrainSerializer(read_only=True)
    availability = SeatAvailabilitySerializer(read_only=True)
    available_seats = serializers.SerializerMethodField()
    
    class Meta:
        model = TrainSchedule
        fields = [
            'id', 'train', 'source', 'destination', 
            'departure_time', 'arrival_time', 'base_fare',
            'runs_on', 'is_active', 'availability', 'available_seats'
        ]
    
    def get_available_seats(self, obj):
        """Get available seats for this schedule."""
        if hasattr(obj, 'availability'):
            return obj.availability.available_seats
        return obj.train.total_seats


class TrainScheduleListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for train search results."""
    train_number = serializers.CharField(source='train.train_number')
    train_name = serializers.CharField(source='train.train_name')
    total_seats = serializers.IntegerField(source='train.total_seats')
    available_seats = serializers.SerializerMethodField()
    
    class Meta:
        model = TrainSchedule
        fields = [
            'id', 'train_number', 'train_name', 'source', 'destination',
            'departure_time', 'arrival_time', 'base_fare', 'runs_on',
            'total_seats', 'available_seats'
        ]
    
    def get_available_seats(self, obj):
        """Get available seats for this schedule."""
        if hasattr(obj, 'availability'):
            return obj.availability.available_seats
        return obj.train.total_seats


class TrainCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating trains."""
    
    class Meta:
        model = Train
        fields = ['train_number', 'train_name', 'total_seats', 'is_active']
    
    def validate_train_number(self, value):
        """Validate train number format."""
        if not value.isalnum():
            raise serializers.ValidationError("Train number must be alphanumeric.")
        return value.upper()


class TrainScheduleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating train schedules."""
    train_number = serializers.CharField(write_only=True)
    
    class Meta:
        model = TrainSchedule
        fields = [
            'train_number', 'source', 'destination',
            'departure_time', 'arrival_time', 'base_fare', 'runs_on', 'is_active'
        ]
    
    def validate_train_number(self, value):
        """Validate that train exists."""
        try:
            train = Train.objects.get(train_number=value.upper())
            return train
        except Train.DoesNotExist:
            raise serializers.ValidationError(f"Train with number '{value}' does not exist.")
    
    def validate(self, attrs):
        """Validate schedule data."""
        source = attrs.get('source', '').strip().title()
        destination = attrs.get('destination', '').strip().title()
        
        if source == destination:
            raise serializers.ValidationError({
                'destination': "Source and destination cannot be the same."
            })
        
        attrs['source'] = source
        attrs['destination'] = destination
        return attrs
    
    def create(self, validated_data):
        """Create a new train schedule with seat availability."""
        train = validated_data.pop('train_number')
        validated_data['train'] = train
        
        schedule = TrainSchedule.objects.create(**validated_data)
        
        # Create seat availability record
        SeatAvailability.objects.create(schedule=schedule)
        
        return schedule


class TrainWithScheduleSerializer(serializers.Serializer):
    """Serializer for creating train with schedule in one request."""
    # Train fields
    train_number = serializers.CharField(max_length=10)
    train_name = serializers.CharField(max_length=255)
    total_seats = serializers.IntegerField(min_value=1)
    
    # Schedule fields
    source = serializers.CharField(max_length=100)
    destination = serializers.CharField(max_length=100)
    departure_time = serializers.TimeField()
    arrival_time = serializers.TimeField()
    base_fare = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0.01)
    runs_on = serializers.DateField()
    
    def validate_train_number(self, value):
        """Validate and normalize train number."""
        if not value.replace('-', '').isalnum():
            raise serializers.ValidationError("Train number must be alphanumeric.")
        return value.upper()
    
    def validate(self, attrs):
        """Validate the combined data."""
        source = attrs.get('source', '').strip().title()
        destination = attrs.get('destination', '').strip().title()
        
        if source == destination:
            raise serializers.ValidationError({
                'destination': "Source and destination cannot be the same."
            })
        
        attrs['source'] = source
        attrs['destination'] = destination
        return attrs
    
    def create(self, validated_data):
        """Create or update train and add schedule."""
        train_number = validated_data['train_number']
        
        # Create or get train
        train, created = Train.objects.update_or_create(
            train_number=train_number,
            defaults={
                'train_name': validated_data['train_name'],
                'total_seats': validated_data['total_seats'],
                'is_active': True
            }
        )
        
        # Create schedule
        schedule = TrainSchedule.objects.create(
            train=train,
            source=validated_data['source'],
            destination=validated_data['destination'],
            departure_time=validated_data['departure_time'],
            arrival_time=validated_data['arrival_time'],
            base_fare=validated_data['base_fare'],
            runs_on=validated_data['runs_on'],
            is_active=True
        )
        
        # Create seat availability
        SeatAvailability.objects.create(schedule=schedule)
        
        return {
            'train': train,
            'schedule': schedule,
            'created': created
        }

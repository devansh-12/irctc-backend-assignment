"""
Train management models.
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Train(models.Model):
    """
    Train metadata (immutable information).
    Maps to the 'trains' table in MySQL.
    """
    train_number = models.CharField(max_length=10, unique=True)
    train_name = models.CharField(max_length=255)
    total_seats = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'trains'
        indexes = [
            models.Index(fields=['train_number']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.train_number} - {self.train_name}"


class TrainSchedule(models.Model):
    """
    Train schedules - when and where trains run.
    Maps to the 'train_schedules' table in MySQL.
    """
    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name='schedules')
    source = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    departure_time = models.TimeField()
    arrival_time = models.TimeField()
    base_fare = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    runs_on = models.DateField()  # Specific date this schedule applies
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'train_schedules'
        indexes = [
            models.Index(fields=['train', 'runs_on']),
            models.Index(fields=['source', 'destination', 'runs_on']),
            models.Index(fields=['runs_on']),
        ]
    
    def __str__(self):
        return f"{self.train.train_number}: {self.source} -> {self.destination} on {self.runs_on}"


class SeatAvailability(models.Model):
    """
    Seat availability per schedule.
    Maps to the 'seat_availability' table in MySQL.
    Uses optimistic locking with version field for race condition handling.
    """
    schedule = models.OneToOneField(
        TrainSchedule, 
        on_delete=models.CASCADE, 
        related_name='availability'
    )
    booked_seats = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=0)  # For optimistic locking
    
    class Meta:
        db_table = 'seat_availability'
        verbose_name_plural = 'Seat availabilities'
    
    def __str__(self):
        return f"Availability for {self.schedule}"
    
    @property
    def available_seats(self):
        """Calculate available seats."""
        return self.schedule.train.total_seats - self.booked_seats
    
    def can_book(self, num_seats):
        """Check if the requested number of seats can be booked."""
        return self.available_seats >= num_seats

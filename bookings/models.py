"""Booking management models."""
import random
import string
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

from core.models import User
from trains.models import TrainSchedule


def generate_pnr():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))


class Booking(models.Model):
    STATUS_CHOICES = [('PENDING', 'Pending'), ('CONFIRMED', 'Confirmed'), ('CANCELLED', 'Cancelled')]
    
    pnr = models.CharField(max_length=10, unique=True, default=generate_pnr)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='bookings')
    schedule = models.ForeignKey(TrainSchedule, on_delete=models.PROTECT, related_name='bookings')
    num_passengers = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    total_fare = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    booking_date = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'bookings'
        ordering = ['-booking_date']
    
    def __str__(self):
        return f"PNR: {self.pnr} - {self.user.email}"
    
    def save(self, *args, **kwargs):
        if not self.pnr:
            while True:
                pnr = generate_pnr()
                if not Booking.objects.filter(pnr=pnr).exists():
                    self.pnr = pnr
                    break
        super().save(*args, **kwargs)


class Passenger(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='passengers')
    name = models.CharField(max_length=255)
    age = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(120)])
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    seat_number = models.PositiveSmallIntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'passengers'
    
    def __str__(self):
        return f"{self.name} ({self.age}{self.gender})"

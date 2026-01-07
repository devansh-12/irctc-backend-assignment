from django.contrib import admin
from .models import Train, TrainSchedule, SeatAvailability


@admin.register(Train)
class TrainAdmin(admin.ModelAdmin):
    list_display = ['train_number', 'train_name', 'total_seats', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['train_number', 'train_name']
    ordering = ['train_number']


@admin.register(TrainSchedule)
class TrainScheduleAdmin(admin.ModelAdmin):
    list_display = ['train', 'source', 'destination', 'runs_on', 'departure_time', 'arrival_time', 'base_fare', 'is_active']
    list_filter = ['is_active', 'source', 'destination', 'runs_on']
    search_fields = ['train__train_number', 'train__train_name', 'source', 'destination']
    ordering = ['runs_on', 'departure_time']


@admin.register(SeatAvailability)
class SeatAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['schedule', 'booked_seats', 'available_seats', 'updated_at']
    search_fields = ['schedule__train__train_number']
    
    def available_seats(self, obj):
        return obj.available_seats
    available_seats.short_description = 'Available'

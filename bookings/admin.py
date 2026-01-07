from django.contrib import admin
from .models import Booking, Passenger


class PassengerInline(admin.TabularInline):
    model = Passenger
    extra = 0
    readonly_fields = ['seat_number']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['pnr', 'user', 'schedule', 'num_passengers', 'total_fare', 'status', 'booking_date']
    list_filter = ['status', 'booking_date']
    search_fields = ['pnr', 'user__email', 'schedule__train__train_number']
    readonly_fields = ['pnr', 'booking_date', 'confirmed_at', 'cancelled_at']
    inlines = [PassengerInline]
    ordering = ['-booking_date']


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = ['name', 'age', 'gender', 'seat_number', 'booking']
    list_filter = ['gender']
    search_fields = ['name', 'booking__pnr']

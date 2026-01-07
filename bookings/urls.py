"""
URL configuration for bookings app.
"""
from django.urls import path
from .views import BookingCreateView, MyBookingsView, BookingDetailView

urlpatterns = [
    path('', BookingCreateView.as_view(), name='booking_create'),
    path('my/', MyBookingsView.as_view(), name='my_bookings'),
    path('<str:pnr>/', BookingDetailView.as_view(), name='booking_detail'),
]

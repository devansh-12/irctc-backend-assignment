"""
URL configuration for analytics app.
"""
from django.urls import path
from .views import TopRoutesView, APILogsView, LogStatsView

urlpatterns = [
    path('top-routes/', TopRoutesView.as_view(), name='top_routes'),
    path('logs/', APILogsView.as_view(), name='api_logs'),
    path('stats/', LogStatsView.as_view(), name='log_stats'),
]


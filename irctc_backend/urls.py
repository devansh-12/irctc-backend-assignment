"""
URL configuration for irctc_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def api_root(request):
    """Root API endpoint showing available endpoints."""
    return JsonResponse({
        'message': 'Welcome to IRCTC Backend API',
        'version': '1.0',
        'endpoints': {
            'auth': {
                'register': '/api/register/',
                'login': '/api/login/',
                'token_refresh': '/api/token/refresh/',
                'profile': '/api/profile/',
            },
            'trains': {
                'search': '/api/trains/search/?source=&destination=&date=',
                'manage': '/api/trains/ (Admin only)',
            },
            'bookings': {
                'create': '/api/bookings/',
                'my_bookings': '/api/bookings/my/',
            },
            'analytics': {
                'top_routes': '/api/analytics/top-routes/',
            }
        },
        'documentation': 'See README.md for detailed API documentation'
    })


urlpatterns = [
    path('', api_root, name='api_root'),
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('api/trains/', include('trains.urls')),
    path('api/bookings/', include('bookings.urls')),
    path('api/analytics/', include('analytics.urls')),
]


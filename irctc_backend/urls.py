"""
URL configuration for irctc_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


def api_root(request):
    """Root API endpoint showing available endpoints."""
    return JsonResponse({
        'message': 'Welcome to IRCTC Backend API',
        'version': '1.0',
        'documentation': {
            'swagger_ui': '/api/docs/',
            'redoc': '/api/docs/redoc/',
            'openapi_schema': '/api/schema/',
        },
        'endpoints': {
            'auth': '/api/register/, /api/login/, /api/token/refresh/',
            'trains': '/api/trains/search/, /api/trains/',
            'bookings': '/api/bookings/, /api/bookings/my/',
            'analytics': '/api/analytics/top-routes/, /api/analytics/logs/',
        }
    })


urlpatterns = [
    path('', api_root, name='api_root'),
    path('admin/', admin.site.urls),
    
    # API Documentation (Swagger UI)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API Endpoints
    path('api/', include('core.urls')),
    path('api/trains/', include('trains.urls')),
    path('api/bookings/', include('bookings.urls')),
    path('api/analytics/', include('analytics.urls')),
]



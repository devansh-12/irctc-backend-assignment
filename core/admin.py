from django.contrib import admin
from .models import User, RefreshToken


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'is_admin', 'is_active', 'created_at']
    list_filter = ['is_admin', 'is_active']
    search_fields = ['email', 'name']
    ordering = ['-created_at']


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'expires_at', 'is_revoked', 'created_at']
    list_filter = ['is_revoked']
    search_fields = ['user__email']

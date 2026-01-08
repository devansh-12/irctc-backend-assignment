"""Custom permissions for train management."""
from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    message = "You do not have permission to perform this action. Admin access required."
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)

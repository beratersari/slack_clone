"""
Custom Permissions - API Layer
Permission classes for different user types.
"""
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Permission for admin users only."""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_admin
        )


class IsSuperUser(permissions.BasePermission):
    """Permission for super users and above."""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_admin or request.user.is_super_user)
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """Permission for object owner or admin."""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin:
            return True
        return obj.id == request.user.id

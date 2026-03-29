"""
User Repository - Repository Layer
Handles data access operations for User entity.
"""
from typing import Optional, List
from django.db.models import Q
from domain.models.user import User, UserType


class UserRepository:
    """
    Repository for User data access operations.
    Provides abstraction between domain and database.
    """
    
    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        """Get user by ID."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_email(email: str) -> Optional[User]:
        """Get user by email."""
        try:
            return User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_username(username: str) -> Optional[User]:
        """Get user by username."""
        try:
            return User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def get_all() -> List[User]:
        """Get all users."""
        return list(User.objects.all())
    
    @staticmethod
    def get_by_user_type(user_type: str) -> List[User]:
        """Get users by type."""
        return list(User.objects.filter(user_type=user_type))
    
    @staticmethod
    def get_admins() -> List[User]:
        """Get all admin users."""
        return list(User.objects.admins())
    
    @staticmethod
    def get_super_users() -> List[User]:
        """Get all super users."""
        return list(User.objects.super_users())
    
    @staticmethod
    def get_regular_users() -> List[User]:
        """Get all regular users."""
        return list(User.objects.regular_users())
    
    @staticmethod
    def search(query: str) -> List[User]:
        """Search users by email, username, or name."""
        return list(User.objects.filter(
            Q(email__icontains=query) |
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(display_name__icontains=query)
        ))
    
    @staticmethod
    def create_user(email: str, username: str, password: str, 
                    user_type: str = UserType.USER, **extra_fields) -> User:
        """Create a new user."""
        return User.objects.create_user(
            email=email,
            username=username,
            password=password,
            user_type=user_type,
            **extra_fields
        )
    
    @staticmethod
    def create_admin(email: str, username: str, password: str, **extra_fields) -> User:
        """Create a new admin user."""
        return User.objects.create_superuser(
            email=email,
            username=username,
            password=password,
            **extra_fields
        )
    
    @staticmethod
    def create_super_user(email: str, username: str, password: str, **extra_fields) -> User:
        """Create a new super user."""
        return User.objects.create_super_user(
            email=email,
            username=username,
            password=password,
            **extra_fields
        )
    
    @staticmethod
    def update_user(user: User, **fields) -> User:
        """Update user fields."""
        for field, value in fields.items():
            if hasattr(user, field):
                setattr(user, field, value)
        user.save()
        return user
    
    @staticmethod
    def delete_user(user_id: int) -> bool:
        """Delete user by ID."""
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return True
        except User.DoesNotExist:
            return False
    
    @staticmethod
    def email_exists(email: str) -> bool:
        """Check if email exists."""
        return User.objects.filter(email__iexact=email).exists()
    
    @staticmethod
    def username_exists(username: str) -> bool:
        """Check if username exists."""
        return User.objects.filter(username__iexact=username).exists()

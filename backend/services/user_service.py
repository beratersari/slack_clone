"""
User Service - Services Layer
Handles business logic for user management operations.
"""
from typing import List, Optional
from domain.models.user import User
from repository.user_repository import UserRepository


class UserServiceError(Exception):
    """Custom exception for user service errors."""
    pass


class UserService:
    """
    Service for handling user management business logic.
    """
    
    @staticmethod
    def get_user_profile(user_id: int) -> Optional[User]:
        """Get user profile by ID."""
        return UserRepository.get_by_id(user_id)
    
    @staticmethod
    def update_profile(user: User, **data) -> User:
        """
        Update user profile.
        
        Args:
            user: User instance
            **data: Fields to update
            
        Returns:
            Updated user
        """
        allowed_fields = [
            'first_name', 'last_name', 'display_name',
            'avatar_url', 'status', 'timezone', 'language',
            'email_notifications', 'push_notifications'
        ]
        
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        return UserRepository.update_user(user, **update_data)
    
    @staticmethod
    def list_users(user_type: Optional[str] = None) -> List[User]:
        """
        List users with optional filtering by type.
        
        Args:
            user_type: Optional filter by user type
            
        Returns:
            List of users
        """
        if user_type:
            return UserRepository.get_by_user_type(user_type)
        return UserRepository.get_all()
    
    @staticmethod
    def search_users(query: str) -> List[User]:
        """
        Search users by query string.
        
        Args:
            query: Search query
            
        Returns:
            List of matching users
        """
        if not query or len(query) < 2:
            return []
        return UserRepository.search(query)
    
    @staticmethod
    def deactivate_user(user: User) -> User:
        """Deactivate user account."""
        return UserRepository.update_user(user, is_active=False)
    
    @staticmethod
    def activate_user(user: User) -> User:
        """Activate user account."""
        return UserRepository.update_user(user, is_active=True)
    
    @staticmethod
    def delete_user(user_id: int) -> bool:
        """Delete user by ID."""
        return UserRepository.delete_user(user_id)

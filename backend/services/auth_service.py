"""
Authentication Service - Services Layer
Handles business logic for authentication operations.
"""
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import jwt
from django.conf import settings
from django.contrib.auth.hashers import check_password
from domain.models.user import User, UserType
from repository.user_repository import UserRepository


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass


class AuthService:
    """
    Service for handling authentication business logic.
    Manages login, registration, token generation/validation.
    """
    
    @staticmethod
    def register_user(email: str, username: str, password: str, 
                      user_type: str = UserType.USER, **extra_fields) -> Tuple[User, str]:
        """
        Register a new user.
        
        Args:
            email: User email
            username: Username
            password: User password
            user_type: Type of user (admin, super_user, user)
            **extra_fields: Additional user fields
            
        Returns:
            Tuple of (User, access_token)
            
        Raises:
            AuthenticationError: If registration fails
        """
        # Validate email uniqueness
        if UserRepository.email_exists(email):
            raise AuthenticationError("Email already registered")
        
        # Validate username uniqueness
        if UserRepository.username_exists(username):
            raise AuthenticationError("Username already taken")
        
        # Create user based on type
        if user_type == UserType.ADMIN:
            user = UserRepository.create_admin(email, username, password, **extra_fields)
        elif user_type == UserType.SUPER_USER:
            user = UserRepository.create_super_user(email, username, password, **extra_fields)
        else:
            user = UserRepository.create_user(email, username, password, user_type, **extra_fields)
        
        # Generate token
        token = AuthService.generate_token(user)
        
        return user, token
    
    @staticmethod
    def login(email: str, password: str) -> Tuple[User, str]:
        """
        Authenticate user and generate token.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Tuple of (User, access_token)
            
        Raises:
            AuthenticationError: If login fails
        """
        user = UserRepository.get_by_email(email)
        
        if not user:
            raise AuthenticationError("Invalid credentials")
        
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")
        
        if not check_password(password, user.password):
            raise AuthenticationError("Invalid credentials")
        
        # Update last active
        user.update_last_active()
        
        # Generate token
        token = AuthService.generate_token(user)
        
        return user, token
    
    @staticmethod
    def generate_token(user: User) -> str:
        """
        Generate JWT access token for user.
        
        Args:
            user: User instance
            
        Returns:
            JWT token string
        """
        payload = {
            'user_id': user.id,
            'email': user.email,
            'username': user.username,
            'user_type': user.user_type,
            'is_staff': user.is_staff,
            'exp': datetime.utcnow() + timedelta(seconds=settings.JWT_ACCESS_TOKEN_LIFETIME),
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm='HS256'
        )
    
    @staticmethod
    def generate_refresh_token(user: User) -> str:
        """
        Generate JWT refresh token for user.
        
        Args:
            user: User instance
            
        Returns:
            JWT refresh token string
        """
        payload = {
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(seconds=settings.JWT_REFRESH_TOKEN_LIFETIME),
            'iat': datetime.utcnow(),
            'type': 'refresh'
        }
        
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm='HS256'
        )
    
    @staticmethod
    def verify_token(token: str) -> Dict:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=['HS256']
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
    
    @staticmethod
    def get_user_from_token(token: str) -> Optional[User]:
        """
        Get user from JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            User instance or None
        """
        try:
            payload = AuthService.verify_token(token)
            user_id = payload.get('user_id')
            return UserRepository.get_by_id(user_id)
        except AuthenticationError:
            return None
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> str:
        """
        Generate new access token from refresh token.
        
        Args:
            refresh_token: JWT refresh token
            
        Returns:
            New access token
            
        Raises:
            AuthenticationError: If refresh token is invalid
        """
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=['HS256']
            )
            
            if payload.get('type') != 'refresh':
                raise AuthenticationError("Invalid token type")
            
            user_id = payload.get('user_id')
            user = UserRepository.get_by_id(user_id)
            
            if not user or not user.is_active:
                raise AuthenticationError("User not found or inactive")
            
            return AuthService.generate_token(user)
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Refresh token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid refresh token")
    
    @staticmethod
    def change_password(user: User, old_password: str, new_password: str) -> bool:
        """
        Change user password.
        
        Args:
            user: User instance
            old_password: Current password
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            AuthenticationError: If old password is incorrect
        """
        if not check_password(old_password, user.password):
            raise AuthenticationError("Current password is incorrect")
        
        user.set_password(new_password)
        user.save()
        return True
    
    @staticmethod
    def logout(user: User) -> bool:
        """
        Handle user logout.
        In a complete implementation, this would blacklist the token.
        
        Args:
            user: User instance
            
        Returns:
            True if successful
        """
        user.update_last_active()
        return True

"""
User Views - API Layer
API endpoints for user management operations.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from api.serializers.user_serializers import (
    UserSerializer,
    UserProfileSerializer,
    UserListSerializer
)
from api.permissions import IsAdmin, IsOwnerOrAdmin
from services.user_service import UserService
from repository.user_repository import UserRepository


class UserProfileView(APIView):
    """View for current user profile."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Users'],
        summary='Get current user profile',
        description='Retrieve the profile information of the currently authenticated user.',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='User profile retrieved successfully',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'user': {
                                'id': 1,
                                'email': 'user@example.com',
                                'username': 'user',
                                'first_name': 'John',
                                'last_name': 'Doe',
                                'display_name': 'John Doe',
                                'user_type': 'user',
                                'user_type_display': 'User',
                                'full_name': 'John Doe',
                                'avatar_url': '',
                                'status': 'Working hard!',
                                'is_active': True,
                                'date_joined': '2024-01-01T00:00:00Z',
                                'last_active': '2024-01-01T12:00:00Z',
                                'email_verified': True,
                                'timezone': 'UTC',
                                'language': 'en'
                            }
                        }
                    )
                ]
            ),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def get(self, request):
        """Get current user profile."""
        serializer = UserSerializer(request.user)
        return Response({
            'user': serializer.data
        })
    
    @extend_schema(
        tags=['Users'],
        summary='Update user profile',
        description='Update the current user profile information.',
        request=UserProfileSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Profile updated successfully'
            ),
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def put(self, request):
        """Update current user profile."""
        serializer = UserProfileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = UserService.update_profile(request.user, **serializer.validated_data)
        return Response({
            'message': 'Profile updated successfully',
            'user': UserSerializer(user).data
        })
    
    @extend_schema(
        tags=['Users'],
        summary='Partially update user profile',
        description='Partially update the current user profile (PATCH).',
        request=UserProfileSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Profile updated successfully'
            ),
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def patch(self, request):
        """Partially update current user profile."""
        serializer = UserProfileSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = UserService.update_profile(request.user, **serializer.validated_data)
        return Response({
            'message': 'Profile updated successfully',
            'user': UserSerializer(user).data
        })


class UserListView(APIView):
    """View for listing users."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Users'],
        summary='List users',
        description='List all users with optional filtering by user type or search query.',
        parameters=[
            {
                'name': 'user_type',
                'in': 'query',
                'description': 'Filter by user type (admin, super_user, user)',
                'required': False,
                'schema': {'type': 'string'}
            },
            {
                'name': 'search',
                'in': 'query',
                'description': 'Search users by name, email, or username',
                'required': False,
                'schema': {'type': 'string'}
            }
        ],
        responses={
            200: OpenApiResponse(
                response=dict,
                description='List of users',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'count': 3,
                            'users': [
                                {
                                    'id': 1,
                                    'username': 'admin',
                                    'display_name': 'Admin',
                                    'avatar_url': '',
                                    'status': 'Managing the system',
                                    'user_type': 'admin',
                                    'is_active': True
                                }
                            ]
                        }
                    )
                ]
            ),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def get(self, request):
        """Get list of users."""
        user_type = request.query_params.get('user_type')
        search = request.query_params.get('search')
        
        if search:
            users = UserService.search_users(search)
        else:
            users = UserService.list_users(user_type)
        
        # Filter out inactive users for non-admin users
        if not request.user.is_admin:
            users = [u for u in users if u.is_active]
        
        serializer = UserListSerializer(users, many=True)
        return Response({
            'count': len(users),
            'users': serializer.data
        })


class UserDetailView(APIView):
    """View for user details."""
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    
    @extend_schema(
        tags=['Users'],
        summary='Get user details',
        description='Get detailed information about a specific user.',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='User details retrieved'
            ),
            404: OpenApiResponse(description='User not found'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def get(self, request, user_id):
        """Get user details by ID."""
        user = UserRepository.get_by_id(user_id)
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission
        if not request.user.is_admin and not user.is_active and user.id != request.user.id:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = UserSerializer(user)
        return Response({
            'user': serializer.data
        })


class UserActivateView(APIView):
    """View for activating/deactivating users (admin only)."""
    permission_classes = [IsAdmin]
    
    @extend_schema(
        tags=['Users'],
        summary='Activate user',
        description='Activate a user account (admin only).',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='User activated'
            ),
            404: OpenApiResponse(description='User not found'),
            403: OpenApiResponse(description='Admin permission required')
        }
    )
    def post(self, request, user_id):
        """Activate user."""
        user = UserRepository.get_by_id(user_id)
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        UserService.activate_user(user)
        return Response({
            'message': 'User activated successfully'
        })
    
    @extend_schema(
        tags=['Users'],
        summary='Deactivate user',
        description='Deactivate a user account (admin only).',
        responses={
            200: OpenApiResponse(
                response=dict,
                description='User deactivated'
            ),
            404: OpenApiResponse(description='User not found'),
            403: OpenApiResponse(description='Admin permission required')
        }
    )
    def delete(self, request, user_id):
        """Deactivate user."""
        user = UserRepository.get_by_id(user_id)
        if not user:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        UserService.deactivate_user(user)
        return Response({
            'message': 'User deactivated successfully'
        })

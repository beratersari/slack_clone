"""
Authentication Views - API Layer
API endpoints for authentication operations.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from api.serializers.user_serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    PasswordChangeSerializer,
    UserSerializer
)
from services.auth_service import AuthService, AuthenticationError


class RegisterView(APIView):
    """View for user registration."""
    permission_classes = [AllowAny]
    authentication_classes = []
    
    @extend_schema(
        tags=['Authentication'],
        summary='Register a new user',
        description='Create a new user account with email, username, and password.',
        request=UserRegistrationSerializer,
        auth=[],
        responses={
            201: OpenApiResponse(
                response=dict,
                description='User registered successfully',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'message': 'User registered successfully',
                            'access_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                            'refresh_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                            'expires_in': 86400,
                            'user': {
                                'id': 1,
                                'email': 'user@example.com',
                                'username': 'newuser',
                                'user_type': 'user',
                                'user_type_display': 'User'
                            }
                        }
                    )
                ]
            ),
            400: OpenApiResponse(description='Validation error or email/username already exists')
        }
    )
    def post(self, request):
        """Handle user registration."""
        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data = serializer.validated_data
            user, token = AuthService.register_user(
                email=data['email'],
                username=data['username'],
                password=data['password'],
                user_type=data.get('user_type', 'user'),
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                display_name=data.get('display_name', '')
            )
            
            refresh_token = AuthService.generate_refresh_token(user)
            
            return Response({
                'message': 'User registered successfully',
                'access_token': token,
                'refresh_token': refresh_token,
                'expires_in': settings.JWT_ACCESS_TOKEN_LIFETIME,
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
            
        except AuthenticationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class LoginView(APIView):
    """View for user login."""
    permission_classes = [AllowAny]
    authentication_classes = []
    
    @extend_schema(
        tags=['Authentication'],
        summary='User login',
        description='Authenticate user with email and password to receive JWT tokens.',
        request=UserLoginSerializer,
        auth=[],
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Login successful',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'message': 'Login successful',
                            'access_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                            'refresh_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                            'expires_in': 86400,
                            'user': {
                                'id': 1,
                                'email': 'user@example.com',
                                'username': 'user',
                                'user_type': 'user',
                                'user_type_display': 'User'
                            }
                        }
                    )
                ]
            ),
            401: OpenApiResponse(description='Invalid credentials or account deactivated')
        }
    )
    def post(self, request):
        """Handle user login."""
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data = serializer.validated_data
            user, token = AuthService.login(
                email=data['email'],
                password=data['password']
            )
            
            refresh_token = AuthService.generate_refresh_token(user)
            
            return Response({
                'message': 'Login successful',
                'access_token': token,
                'refresh_token': refresh_token,
                'expires_in': settings.JWT_ACCESS_TOKEN_LIFETIME,
                'user': UserSerializer(user).data
            })
            
        except AuthenticationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )


class LogoutView(APIView):
    """View for user logout."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Authentication'],
        summary='User logout',
        description='Logout the current user.',
        request=None,
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Logout successful',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={'message': 'Logout successful'}
                    )
                ]
            ),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def post(self, request):
        """Handle user logout."""
        AuthService.logout(request.user)
        return Response({
            'message': 'Logout successful'
        })


class RefreshTokenView(APIView):
    """View for refreshing access token."""
    permission_classes = [AllowAny]
    authentication_classes = []
    
    @extend_schema(
        tags=['Authentication'],
        summary='Refresh access token',
        description='Get a new access token using a valid refresh token.',
        request=dict,
        auth=[],
        responses={
            200: OpenApiResponse(
                response=dict,
                description='New access token generated',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'access_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                            'expires_in': 86400
                        }
                    )
                ]
            ),
            401: OpenApiResponse(description='Invalid or expired refresh token')
        }
    )
    def post(self, request):
        """Handle token refresh."""
        refresh_token = request.data.get('refresh_token')
        
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_token = AuthService.refresh_access_token(refresh_token)
            return Response({
                'access_token': new_token,
                'expires_in': settings.JWT_ACCESS_TOKEN_LIFETIME
            })
        except AuthenticationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )


class ChangePasswordView(APIView):
    """View for changing password."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Authentication'],
        summary='Change password',
        description='Change the current user password.',
        request=PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(
                response=dict,
                description='Password changed successfully',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={'message': 'Password changed successfully'}
                    )
                ]
            ),
            400: OpenApiResponse(description='Validation error or incorrect old password'),
            401: OpenApiResponse(description='Authentication required')
        }
    )
    def post(self, request):
        """Handle password change."""
        serializer = PasswordChangeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data = serializer.validated_data
            AuthService.change_password(
                user=request.user,
                old_password=data['old_password'],
                new_password=data['new_password']
            )
            return Response({
                'message': 'Password changed successfully'
            })
        except AuthenticationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

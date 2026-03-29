"""
User Serializers - API Layer
Handles serialization/deserialization of User data.
"""
from rest_framework import serializers
from domain.models.user import User, UserType


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data."""
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'display_name', 'user_type', 'user_type_display',
            'full_name', 'avatar_url', 'status', 'is_active',
            'date_joined', 'last_active', 'email_verified',
            'timezone', 'language'
        ]
        read_only_fields = ['id', 'date_joined', 'last_active', 'email_verified']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    user_type = serializers.ChoiceField(
        choices=UserType.choices,
        default=UserType.USER,
        required=False
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'username', 'password', 'password_confirm',
            'first_name', 'last_name', 'display_name', 'user_type'
        ]
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'display_name': {'required': False}
        }
    
    def validate(self, data):
        """Validate password match."""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def validate_email(self, value):
        """Validate email uniqueness."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value.lower()
    
    def validate_username(self, value):
        """Validate username uniqueness."""
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username already taken")
        return value


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile updates."""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'display_name',
            'avatar_url', 'status', 'timezone', 'language',
            'email_notifications', 'push_notifications'
        ]


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""
    old_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, data):
        """Validate new passwords match."""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError("New passwords do not match")
        return data


class TokenResponseSerializer(serializers.Serializer):
    """Serializer for token response."""
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    user = UserSerializer()
    expires_in = serializers.IntegerField()


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users (limited fields)."""
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'display_name', 'avatar_url',
            'status', 'user_type', 'is_active'
        ]

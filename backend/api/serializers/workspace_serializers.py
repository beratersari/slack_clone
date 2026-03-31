"""
Workspace Serializers - API Layer
Handles serialization/deserialization of Workspace data.
"""
from rest_framework import serializers
from domain.models.workspace import Workspace, WorkspaceMembership, WorkspaceInvite, WorkspaceRole
from api.serializers.user_serializers import UserSerializer, UserListSerializer


class WorkspaceSerializer(serializers.ModelSerializer):
    """Serializer for workspace data."""
    owner = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    
    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'slug', 'description', 'owner',
            'is_public', 'allow_guests', 'icon_url',
            'invite_code', 'invite_code_expires_at',
            'is_active', 'member_count', 'user_role',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'slug', 'owner', 'invite_code', 
            'invite_code_expires_at', 'created_at', 'updated_at'
        ]
    
    def get_member_count(self, obj):
        """Get total member count."""
        return obj.get_member_count()
    
    def get_user_role(self, obj):
        """Get current user's role in workspace."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            role = obj.get_user_role(request.user)
            return role if role else None
        return None


class WorkspaceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating workspaces."""
    
    class Meta:
        model = Workspace
        fields = ['name', 'description', 'is_public']
    
    def validate_name(self, value):
        """Validate workspace name."""
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Name must be at least 3 characters")
        return value.strip()


class WorkspaceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating workspaces."""
    
    class Meta:
        model = Workspace
        fields = ['name', 'description', 'is_public', 'allow_guests', 'icon_url']


class WorkspaceListSerializer(serializers.ModelSerializer):
    """Serializer for listing workspaces (limited fields)."""
    owner = UserListSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    
    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'slug', 'description', 'icon_url',
            'is_public', 'owner', 'member_count', 'user_role', 'created_at'
        ]
    
    def get_member_count(self, obj):
        return obj.get_member_count()
    
    def get_user_role(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            role = obj.get_user_role(request.user)
            return role if role else None
        return None


class WorkspaceMembershipSerializer(serializers.ModelSerializer):
    """Serializer for workspace membership."""
    user = UserListSerializer(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = WorkspaceMembership
        fields = [
            'id', 'user', 'role', 'role_display', 'is_active',
            'joined_at', 'invited_by', 'notify_mentions', 
            'notify_all_messages'
        ]
        read_only_fields = ['id', 'joined_at', 'invited_by']


class WorkspaceMemberUpdateSerializer(serializers.Serializer):
    """Serializer for updating member role."""
    role = serializers.ChoiceField(
        choices=[WorkspaceRole.ADMIN, WorkspaceRole.MEMBER]
    )


class WorkspaceInviteSerializer(serializers.ModelSerializer):
    """Serializer for workspace invites."""
    invited_by = UserListSerializer(read_only=True)
    workspace = WorkspaceListSerializer(read_only=True)
    
    class Meta:
        model = WorkspaceInvite
        fields = [
            'id', 'workspace', 'email', 'invited_by',
            'token', 'status', 'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'token', 'status', 'created_at', 'expires_at']


class WorkspaceInviteCreateSerializer(serializers.Serializer):
    """Serializer for creating workspace invites."""
    email = serializers.EmailField(required=True)


class JoinByInviteCodeSerializer(serializers.Serializer):
    """Serializer for joining workspace by invite code."""
    invite_code = serializers.CharField(required=True, max_length=32)


class AcceptInviteSerializer(serializers.Serializer):
    """Serializer for accepting workspace invite."""
    token = serializers.CharField(required=True)


class TransferOwnershipSerializer(serializers.Serializer):
    """Serializer for transferring workspace ownership."""
    new_owner_id = serializers.IntegerField(required=True)

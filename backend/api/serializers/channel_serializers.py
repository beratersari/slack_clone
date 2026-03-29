"""
Channel Serializers - API Layer
Handles serialization/deserialization of Channel data.
"""
from rest_framework import serializers
from domain.models.channel import Channel, ChannelMembership, Message, ChannelType
from api.serializers.user_serializers import UserListSerializer


class ChannelSerializer(serializers.ModelSerializer):
    """Serializer for channel data."""
    created_by = UserListSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Channel
        fields = [
            'id', 'name', 'display_name', 'normalized_name',
            'channel_type', 'topic', 'description',
            'workspace', 'created_by',
            'is_default', 'is_archived', 'archived_at',
            'member_count', 'is_member', 'unread_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'normalized_name', 'created_by',
            'is_default', 'archived_at', 'created_at', 'updated_at'
        ]
    
    def get_member_count(self, obj):
        """Get total member count."""
        return obj.get_member_count()
    
    def get_is_member(self, obj):
        """Check if current user is a member."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.has_member(request.user)
        return False
    
    def get_unread_count(self, obj):
        """Get unread count for current user."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            membership = obj.memberships.filter(
                user=request.user,
                is_active=True
            ).first()
            if membership:
                return membership.get_unread_count()
        return 0


class ChannelListSerializer(serializers.ModelSerializer):
    """Serializer for listing channels (limited fields)."""
    member_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Channel
        fields = [
            'id', 'name', 'display_name', 'channel_type',
            'topic', 'is_default', 'is_archived',
            'member_count', 'is_member', 'unread_count',
            'created_at'
        ]
    
    def get_member_count(self, obj):
        return obj.get_member_count()
    
    def get_is_member(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.has_member(request.user)
        return False
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            membership = obj.memberships.filter(
                user=request.user,
                is_active=True
            ).first()
            if membership:
                return membership.get_unread_count()
        return 0


class ChannelCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating channels."""
    
    class Meta:
        model = Channel
        fields = ['name', 'channel_type', 'topic', 'description']
    
    def validate_name(self, value):
        """Validate channel name."""
        value = value.lower().strip()
        
        # Remove # if user included it
        if value.startswith('#'):
            value = value[1:]
        
        # Check length
        if len(value) < 2:
            raise serializers.ValidationError("Channel name must be at least 2 characters")
        
        if len(value) > 80:
            raise serializers.ValidationError("Channel name must be less than 80 characters")
        
        # Check valid characters (letters, numbers, hyphens, underscores)
        import re
        if not re.match(r'^[a-z0-9_-]+$', value):
            raise serializers.ValidationError(
                "Channel name can only contain lowercase letters, numbers, hyphens, and underscores"
            )
        
        return value


class ChannelUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating channels."""
    
    class Meta:
        model = Channel
        fields = ['topic', 'description']


class ChannelMembershipSerializer(serializers.ModelSerializer):
    """Serializer for channel membership."""
    user = UserListSerializer(read_only=True)
    
    class Meta:
        model = ChannelMembership
        fields = [
            'id', 'user', 'joined_at', 'invited_by',
            'notify_all_messages', 'muted', 'last_read_at'
        ]
        read_only_fields = ['id', 'joined_at', 'invited_by', 'last_read_at']


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages."""
    sender = UserListSerializer(read_only=True)
    is_own_message = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'channel', 'sender', 'content',
            'is_edited', 'edited_at', 'is_deleted',
            'is_thread_reply', 'is_thread_parent',
            'reply_count', 'is_own_message',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'sender', 'is_edited', 'edited_at',
            'is_deleted', 'created_at', 'updated_at'
        ]
    
    def get_is_own_message(self, obj):
        """Check if message is from current user."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender == request.user
        return False
    
    def get_reply_count(self, obj):
        """Get number of replies."""
        return obj.replies.filter(is_deleted=False).count()


class MessageCreateSerializer(serializers.Serializer):
    """Serializer for creating messages."""
    content = serializers.CharField(
        required=True,
        min_length=1,
        max_length=4000,
        help_text='Message content (max 4000 characters)'
    )
    parent_message_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='ID of parent message for thread replies'
    )


class MessageEditSerializer(serializers.Serializer):
    """Serializer for editing messages."""
    content = serializers.CharField(
        required=True,
        min_length=1,
        max_length=4000
    )

"""
Direct Message Serializers - API Layer
Handles serialization/deserialization of DM data.
"""
from rest_framework import serializers
from domain.models.direct_message import (
    DirectMessageConversation,
    DirectMessageParticipant,
    DirectMessage
)
from domain.models.channel import MessageReaction, FileAttachment
from api.serializers.user_serializers import UserListSerializer


class DirectMessageParticipantSerializer(serializers.ModelSerializer):
    """Serializer for DM participants."""
    user = UserListSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DirectMessageParticipant
        fields = [
            'id', 'user', 'joined_at', 'added_by',
            'muted', 'notify_mentions_only', 'last_read_at',
            'unread_count'
        ]
        read_only_fields = ['id', 'joined_at', 'added_by', 'last_read_at']
    
    def get_unread_count(self, obj):
        """Get unread message count."""
        return obj.get_unread_count()


class DirectMessageConversationSerializer(serializers.ModelSerializer):
    """Serializer for DM conversations."""
    created_by = UserListSerializer(read_only=True)
    participants = DirectMessageParticipantSerializer(many=True, read_only=True)
    display_name = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    is_participant = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DirectMessageConversation
        fields = [
            'id', 'workspace', 'is_group', 'name',
            'created_by', 'participants', 'display_name',
            'is_active', 'is_archived', 'participant_count',
            'is_participant', 'unread_count',
            'last_message_at', 'last_message_preview',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_by', 'is_active', 'is_archived',
            'last_message_at', 'last_message_preview',
            'created_at', 'updated_at'
        ]
    
    def get_display_name(self, obj):
        """Get display name for conversation."""
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        return obj.get_display_name(for_user=user)
    
    def get_participant_count(self, obj):
        """Get participant count."""
        return obj.get_participant_count()
    
    def get_is_participant(self, obj):
        """Check if current user is a participant."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.has_participant(request.user)
        return False
    
    def get_unread_count(self, obj):
        """Get unread count for current user."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            participant = obj.participants.filter(
                user=request.user,
                is_active=True
            ).first()
            if participant:
                return participant.get_unread_count()
        return 0


class DirectMessageConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing conversations."""
    display_name = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = DirectMessageConversation
        fields = [
            'id', 'is_group', 'name', 'display_name',
            'is_archived', 'participant_count', 'unread_count',
            'other_participant', 'last_message_at', 'last_message_preview'
        ]
    
    def get_display_name(self, obj):
        """Get display name for conversation."""
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        return obj.get_display_name(for_user=user)
    
    def get_participant_count(self, obj):
        """Get participant count."""
        return obj.get_participant_count()
    
    def get_unread_count(self, obj):
        """Get unread count for current user."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            participant = obj.participants.filter(
                user=request.user,
                is_active=True
            ).first()
            if participant:
                return participant.get_unread_count()
        return 0
    
    def get_other_participant(self, obj):
        """Get the other participant for 1:1 DMs."""
        if obj.is_group:
            return None
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            other = obj.participants.filter(
                is_active=True
            ).exclude(
                user=request.user
            ).select_related('user').first()
            if other:
                return UserListSerializer(other.user).data
        return None


class DirectMessageConversationCreateSerializer(serializers.Serializer):
    """Serializer for creating DM conversations."""
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=8,
        help_text='List of user IDs to include in the conversation'
    )
    name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text='Optional name for group DMs'
    )
    
    def validate_participant_ids(self, value):
        """Validate participant IDs."""
        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for pid in value:
            if pid not in seen:
                seen.add(pid)
                unique_ids.append(pid)
        return unique_ids


class FileAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for file attachments."""
    human_readable_size = serializers.CharField(read_only=True)
    
    class Meta:
        model = FileAttachment
        fields = [
            'id', 'file', 'file_name', 'file_size',
            'human_readable_size', 'mime_type', 'file_type',
            'width', 'height', 'thumbnail_url', 'is_deleted',
            'created_at'
        ]
        read_only_fields = [
            'id', 'file_size', 'mime_type', 'file_type',
            'width', 'height', 'thumbnail_url', 'is_deleted',
            'created_at'
        ]


class MessageReactionSerializer(serializers.ModelSerializer):
    """Serializer for message reactions."""
    user = UserListSerializer(read_only=True)
    
    class Meta:
        model = MessageReaction
        fields = ['id', 'user', 'emoji', 'emoji_name', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class DirectMessageSerializer(serializers.ModelSerializer):
    """Serializer for direct messages."""
    sender = UserListSerializer(read_only=True)
    is_own_message = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()
    reactions = MessageReactionSerializer(many=True, read_only=True)
    attachments = FileAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = DirectMessage
        fields = [
            'id', 'conversation', 'sender', 'content',
            'is_edited', 'edited_at', 'is_deleted',
            'is_thread_reply', 'is_thread_parent',
            'reply_count', 'is_own_message',
            'reactions', 'attachments',
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


class DirectMessageCreateSerializer(serializers.Serializer):
    """Serializer for creating direct messages."""
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


class DirectMessageEditSerializer(serializers.Serializer):
    """Serializer for editing direct messages."""
    content = serializers.CharField(
        required=True,
        min_length=1,
        max_length=4000
    )


class ReactionCreateSerializer(serializers.Serializer):
    """Serializer for adding reactions."""
    emoji = serializers.CharField(
        max_length=50,
        help_text='Emoji unicode or shortcode'
    )
    emoji_name = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text='Name for custom emojis'
    )

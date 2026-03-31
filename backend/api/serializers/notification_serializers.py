"""
Notification Serializers - API Layer
Handles serialization for notifications and mentions.
"""
from rest_framework import serializers
from domain.models.notification import Notification, Mention, NotificationType
from api.serializers.user_serializers import UserListSerializer


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications."""
    sender = UserListSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'sender', 'notification_type', 'title', 'body',
            'workspace', 'channel', 'message', 'direct_message', 'dm_conversation',
            'is_read', 'read_at', 'created_at'
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for notification lists."""
    sender_name = serializers.CharField(source='sender.get_short_name', read_only=True)
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'sender_id', 'sender_name', 'notification_type',
            'title', 'body', 'is_read', 'created_at'
        ]


class MentionSerializer(serializers.ModelSerializer):
    """Serializer for mentions."""
    mentioned_user = UserListSerializer(read_only=True)
    message_preview = serializers.SerializerMethodField()
    channel_name = serializers.CharField(source='message.channel.name', read_only=True, default=None)
    
    class Meta:
        model = Mention
        fields = [
            'id', 'mentioned_user', 'mention_type', 'mention_text',
            'message', 'direct_message', 'channel_name',
            'message_preview', 'created_at'
        ]
    
    def get_message_preview(self, obj):
        if obj.message:
            return obj.message.content[:100]
        elif obj.direct_message:
            return obj.direct_message.content[:100]
        return None

"""
Search Serializers - API Layer
Handles serialization for search API responses.
"""
from rest_framework import serializers
from domain.models.channel import Message, Channel
from domain.models.direct_message import DirectMessage
from domain.models.workspace import WorkspaceMembership
from domain.models.user import User
from api.serializers.user_serializers import UserListSerializer
from api.serializers.channel_serializers import MessageSerializer, ChannelListSerializer


class SearchMessageSerializer(serializers.ModelSerializer):
    """Serializer for search result messages."""
    sender = UserListSerializer(read_only=True)
    channel = ChannelListSerializer(read_only=True)
    is_own_message = serializers.SerializerMethodField()
    highlight = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'channel', 'sender', 'content',
            'is_edited', 'edited_at', 'is_thread_reply',
            'is_thread_parent', 'is_own_message', 'highlight',
            'created_at', 'updated_at'
        ]
    
    def get_is_own_message(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender == request.user
        return False
    
    def get_highlight(self, obj):
        """Return highlighted content snippet if available."""
        # Could implement snippet highlighting here
        return None


class SearchDirectMessageSerializer(serializers.ModelSerializer):
    """Serializer for search result direct messages."""
    sender = UserListSerializer(read_only=True)
    conversation_id = serializers.IntegerField(source='conversation.id', read_only=True)
    conversation_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DirectMessage
        fields = [
            'id', 'conversation_id', 'conversation_name',
            'sender', 'content', 'is_edited', 'edited_at',
            'is_thread_reply', 'created_at', 'updated_at'
        ]
    
    def get_conversation_name(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.conversation.get_display_name(for_user=request.user)
        return obj.conversation.name or 'Direct Message'


class SearchMemberSerializer(serializers.ModelSerializer):
    """Serializer for search result workspace members."""
    user = UserListSerializer(read_only=True)
    role = serializers.CharField()
    
    class Meta:
        model = WorkspaceMembership
        fields = [
            'id', 'user', 'role', 'joined_at',
            'is_active', 'notify_mentions', 'notify_all_messages'
        ]


class SearchUserSerializer(serializers.ModelSerializer):
    """Serializer for global user search results."""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'display_name',
            'full_name', 'avatar_url', 'status', 'last_active'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class SearchSuggestionsSerializer(serializers.Serializer):
    """Serializer for search suggestions."""
    channels = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    users = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    recent_searches = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


class SearchCountsSerializer(serializers.Serializer):
    """Serializer for search result counts."""
    messages = serializers.IntegerField()
    people = serializers.IntegerField()
    files = serializers.IntegerField()


class MessageSearchResponseSerializer(serializers.Serializer):
    """Response serializer for message search."""
    count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    messages = SearchMessageSerializer(many=True)
    has_more = serializers.BooleanField()
    query = serializers.CharField()
    limit = serializers.IntegerField()
    offset = serializers.IntegerField()


class PeopleSearchResponseSerializer(serializers.Serializer):
    """Response serializer for people search."""
    count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    members = SearchMemberSerializer(many=True)
    has_more = serializers.BooleanField()
    query = serializers.CharField()
    limit = serializers.IntegerField()
    offset = serializers.IntegerField()


class DMSearchResponseSerializer(serializers.Serializer):
    """Response serializer for DM search."""
    count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    messages = SearchDirectMessageSerializer(many=True)
    has_more = serializers.BooleanField()
    query = serializers.CharField()
    limit = serializers.IntegerField()
    offset = serializers.IntegerField()

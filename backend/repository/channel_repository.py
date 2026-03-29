"""
Channel Repository - Repository Layer
Handles data access operations for Channel entities.
"""
from typing import Optional, List
from django.db.models import Q
from domain.models.channel import Channel, ChannelMembership, Message, ChannelType
from domain.models.workspace import Workspace
from domain.models.user import User


class ChannelRepository:
    """
    Repository for Channel data access operations.
    """
    
    # ========== Channel Operations ==========
    
    @staticmethod
    def get_by_id(channel_id: int) -> Optional[Channel]:
        """Get channel by ID."""
        try:
            return Channel.objects.get(id=channel_id)
        except Channel.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_workspace_and_name(workspace: Workspace, name: str) -> Optional[Channel]:
        """Get channel by workspace and name."""
        try:
            return Channel.objects.get(
                workspace=workspace,
                normalized_name=name.lower()
            )
        except Channel.DoesNotExist:
            return None
    
    @staticmethod
    def get_workspace_channels(workspace: Workspace, 
                               include_archived: bool = False) -> List[Channel]:
        """Get all channels in a workspace."""
        queryset = Channel.objects.filter(workspace=workspace)
        if not include_archived:
            queryset = queryset.filter(is_archived=False)
        return list(queryset)
    
    @staticmethod
    def get_visible_channels(workspace: Workspace, user: User) -> List[Channel]:
        """
        Get channels visible to a user in a workspace.
        - Public channels: all visible
        - Private channels: only if member
        """
        # Get public channels
        public_channels = Channel.objects.filter(
            workspace=workspace,
            channel_type=ChannelType.PUBLIC,
            is_archived=False
        )
        
        # Get private channels where user is member
        private_channel_ids = ChannelMembership.objects.filter(
            channel__workspace=workspace,
            channel__channel_type=ChannelType.PRIVATE,
            channel__is_archived=False,
            user=user,
            is_active=True
        ).values_list('channel_id', flat=True)
        
        # Combine and order
        channels = list(public_channels) + list(
            Channel.objects.filter(id__in=private_channel_ids)
        )
        
        # Sort manually
        channels.sort(key=lambda c: (-c.is_default, c.name))
        return channels
    
    @staticmethod
    def get_user_channels(user: User, workspace: Optional[Workspace] = None) -> List[Channel]:
        """Get channels where user is a member."""
        queryset = Channel.objects.filter(
            memberships__user=user,
            memberships__is_active=True,
            is_archived=False
        )
        if workspace:
            queryset = queryset.filter(workspace=workspace)
        return list(queryset)
    
    @staticmethod
    def name_exists_in_workspace(workspace: Workspace, name: str) -> bool:
        """Check if channel name exists in workspace."""
        return Channel.objects.filter(
            workspace=workspace,
            normalized_name=name.lower()
        ).exists()
    
    @staticmethod
    def create_channel(workspace: Workspace, name: str, created_by: User,
                       channel_type: str = ChannelType.PUBLIC,
                       topic: str = '', description: str = '',
                       is_default: bool = False, **extra_fields) -> Channel:
        """Create a new channel."""
        return Channel.objects.create(
            workspace=workspace,
            name=name,
            normalized_name=name.lower(),
            created_by=created_by,
            channel_type=channel_type,
            topic=topic,
            description=description,
            is_default=is_default,
            **extra_fields
        )
    
    @staticmethod
    def update_channel(channel: Channel, **fields) -> Channel:
        """Update channel fields."""
        for field, value in fields.items():
            if hasattr(channel, field):
                setattr(channel, field, value)
        channel.save()
        return channel
    
    @staticmethod
    def delete_channel(channel_id: int) -> bool:
        """Delete channel by ID."""
        try:
            channel = Channel.objects.get(id=channel_id)
            channel.delete()
            return True
        except Channel.DoesNotExist:
            return False
    
    # ========== Membership Operations ==========
    
    @staticmethod
    def get_membership(channel: Channel, user: User) -> Optional[ChannelMembership]:
        """Get membership for a user in a channel."""
        try:
            return ChannelMembership.objects.get(
                channel=channel,
                user=user,
                is_active=True
            )
        except ChannelMembership.DoesNotExist:
            return None
    
    @staticmethod
    def get_members(channel: Channel) -> List[ChannelMembership]:
        """Get all members of a channel."""
        return list(ChannelMembership.objects.filter(
            channel=channel,
            is_active=True
        ).select_related('user'))
    
    @staticmethod
    def add_member(channel: Channel, user: User, 
                   invited_by: Optional[User] = None) -> ChannelMembership:
        """Add a member to a channel."""
        membership, created = ChannelMembership.objects.get_or_create(
            channel=channel,
            user=user,
            defaults={'invited_by': invited_by, 'is_active': True}
        )
        if not created and not membership.is_active:
            membership.is_active = True
            membership.invited_by = invited_by
            membership.save()
        return membership
    
    @staticmethod
    def remove_member(channel: Channel, user: User) -> bool:
        """Remove a member from a channel."""
        try:
            membership = ChannelMembership.objects.get(
                channel=channel,
                user=user,
                is_active=True
            )
            membership.is_active = False
            membership.save()
            return True
        except ChannelMembership.DoesNotExist:
            return False
    
    # ========== Message Operations ==========
    
    @staticmethod
    def create_message(channel: Channel, sender: User, content: str,
                       parent_message: Optional[Message] = None,
                       is_thread_reply: bool = False) -> Message:
        """Create a new message."""
        return Message.objects.create(
            channel=channel,
            sender=sender,
            content=content,
            parent_message=parent_message,
            is_thread_reply=is_thread_reply
        )
    
    @staticmethod
    def get_message_by_id(message_id: int) -> Optional[Message]:
        """Get message by ID."""
        try:
            return Message.objects.get(id=message_id, is_deleted=False)
        except Message.DoesNotExist:
            return None
    
    @staticmethod
    def get_messages(channel: Channel, limit: int = 50,
                    before_id: Optional[int] = None) -> List[Message]:
        """Get messages from a channel."""
        queryset = Message.objects.filter(
            channel=channel,
            is_deleted=False,
            is_thread_reply=False  # Only top-level messages
        )
        
        if before_id:
            try:
                before_message = Message.objects.get(id=before_id)
                queryset = queryset.filter(created_at__lt=before_message.created_at)
            except Message.DoesNotExist:
                pass
        
        return list(queryset.order_by('-created_at')[:limit])
    
    @staticmethod
    def get_thread_replies(parent_message: Message) -> List[Message]:
        """Get replies to a message."""
        return list(Message.objects.filter(
            parent_message=parent_message,
            is_deleted=False,
            is_thread_reply=True
        ).order_by('created_at'))
    
    @staticmethod
    def search_messages(channel: Channel, query: str, 
                       limit: int = 20) -> List[Message]:
        """Search messages in a channel."""
        return list(Message.objects.filter(
            channel=channel,
            content__icontains=query,
            is_deleted=False
        ).order_by('-created_at')[:limit])

"""
Channel Service - Services Layer
Handles business logic for channel operations.
"""
from typing import List, Optional
from django.db import transaction
from domain.models.channel import Channel, ChannelMembership, Message, ChannelType
from domain.models.workspace import Workspace
from domain.models.user import User
from repository.channel_repository import ChannelRepository


class ChannelError(Exception):
    """Custom exception for channel errors."""
    pass


class PermissionError(ChannelError):
    """Custom exception for permission errors."""
    pass


class ChannelService:
    """
    Service for handling channel business logic.
    """
    
    # ========== Channel CRUD ==========
    
    @staticmethod
    def create_channel(workspace: Workspace, name: str, created_by: User,
                       channel_type: str = ChannelType.PUBLIC,
                       topic: str = '', description: str = '') -> Channel:
        """
        Create a new channel in a workspace.
        
        Args:
            workspace: The workspace
            name: Channel name (without #)
            created_by: User creating the channel
            channel_type: 'public' or 'private'
            topic: Brief topic
            description: Detailed description
            
        Returns:
            Created channel
        """
        # Check if user is workspace member
        if not workspace.has_member(created_by):
            raise PermissionError("Must be a workspace member to create channels")
        
        # Normalize name
        name = name.lower().strip().replace(' ', '-')
        
        # Check for reserved names
        if name in ['general', 'random'] and not workspace.is_admin(created_by):
            raise PermissionError("Only admins can create #general or #random channels")
        
        # Check if channel name exists
        if ChannelRepository.name_exists_in_workspace(workspace, name):
            raise ChannelError(f"Channel #{name} already exists in this workspace")
        
        # Create channel
        channel = ChannelRepository.create_channel(
            workspace=workspace,
            name=name,
            created_by=created_by,
            channel_type=channel_type,
            topic=topic,
            description=description
        )
        
        # Creator automatically joins
        ChannelRepository.add_member(channel, created_by)
        
        return channel
    
    @staticmethod
    def create_default_general_channel(workspace: Workspace, created_by: User) -> Channel:
        """
        Create the default #general channel for a workspace.
        Called automatically when workspace is created.
        """
        channel = ChannelRepository.create_channel(
            workspace=workspace,
            name='general',
            created_by=created_by,
            channel_type=ChannelType.PUBLIC,
            topic='General discussion for the workspace',
            description='This is the default channel for workspace-wide announcements and discussions.',
            is_default=True
        )
        
        # Add all workspace members to general channel
        from repository.workspace_repository import WorkspaceRepository
        members = WorkspaceRepository.get_members(workspace)
        for membership in members:
            ChannelRepository.add_member(channel, membership.user)
        
        return channel
    
    @staticmethod
    def update_channel(channel: Channel, user: User, **data) -> Channel:
        """
        Update channel settings.
        
        Args:
            channel: Channel to update
            user: User making the update
            **data: Fields to update
        """
        if not channel.can_manage(user):
            raise PermissionError("Only channel creators or workspace admins can update channels")
        
        if channel.is_archived:
            raise ChannelError("Cannot modify archived channels")
        
        allowed_fields = ['topic', 'description']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        return ChannelRepository.update_channel(channel, **update_data)
    
    @staticmethod
    def archive_channel(channel: Channel, archived_by: User) -> Channel:
        """Archive a channel (make read-only)."""
        if not channel.can_manage(archived_by):
            raise PermissionError("Only channel creators or workspace admins can archive channels")
        
        if channel.is_default:
            raise ChannelError("Cannot archive the default #general channel")
        
        channel.archive(archived_by)
        return channel
    
    @staticmethod
    def unarchive_channel(channel: Channel, unarchived_by: User) -> Channel:
        """Unarchive a channel."""
        if not channel.can_manage(unarchived_by):
            raise PermissionError("Only channel creators or workspace admins can unarchive channels")
        
        channel.unarchive()
        return channel
    
    @staticmethod
    def delete_channel(channel: Channel, deleted_by: User) -> bool:
        """Delete a channel (only if empty or by admin)."""
        if not channel.can_manage(deleted_by):
            raise PermissionError("Only channel creators or workspace admins can delete channels")
        
        if channel.is_default:
            raise ChannelError("Cannot delete the default #general channel")
        
        # Check if channel has messages
        if channel.messages.filter(is_deleted=False).exists():
            raise ChannelError("Cannot delete channels with messages. Archive it instead.")
        
        return ChannelRepository.delete_channel(channel.id)
    
    # ========== Channel Membership ==========
    
    @staticmethod
    def join_channel(channel: Channel, user: User) -> ChannelMembership:
        """
        Join a public channel.
        
        Args:
            channel: Channel to join
            user: User joining
            
        Returns:
            Membership
        """
        if not channel.can_join(user):
            raise PermissionError("Cannot join this channel. It may be private or you are not a workspace member.")
        
        if channel.is_archived:
            raise ChannelError("Cannot join archived channels")
        
        return ChannelRepository.add_member(channel, user)
    
    @staticmethod
    def leave_channel(channel: Channel, user: User) -> bool:
        """
        Leave a channel.
        
        Args:
            channel: Channel to leave
            user: User leaving
        """
        if channel.is_default:
            raise ChannelError("Cannot leave the default #general channel")
        
        if not channel.has_member(user):
            raise ChannelError("You are not a member of this channel")
        
        return ChannelRepository.remove_member(channel, user)
    
    @staticmethod
    def invite_to_channel(channel: Channel, invited_user: User, invited_by: User) -> ChannelMembership:
        """
        Invite a user to a private channel.
        
        Args:
            channel: Channel to invite to
            invited_user: User being invited
            invited_by: User sending the invite
        """
        if not channel.has_member(invited_by):
            raise PermissionError("Must be a channel member to invite others")
        
        if channel.is_archived:
            raise ChannelError("Cannot invite to archived channels")
        
        # For private channels, only members can invite
        # For public channels, any workspace member can effectively "invite" by having them join
        if channel.is_private and not channel.can_manage(invited_by):
            raise PermissionError("Only channel admins can invite to private channels")
        
        # Check if invited user is workspace member
        if not channel.workspace.has_member(invited_user):
            raise ChannelError("User must be a workspace member first")
        
        return ChannelRepository.add_member(channel, invited_user, invited_by=invited_by)
    
    @staticmethod
    def remove_from_channel(channel: Channel, user_to_remove: User, removed_by: User) -> bool:
        """Remove a user from a channel."""
        if not channel.can_manage(removed_by):
            raise PermissionError("Only channel admins can remove members")
        
        if channel.is_default:
            raise ChannelError("Cannot remove members from default channel")
        
        if channel.created_by == user_to_remove:
            raise ChannelError("Cannot remove the channel creator")
        
        return ChannelRepository.remove_member(channel, user_to_remove)
    
    @staticmethod
    def get_channel_members(channel: Channel, requesting_user: User) -> List[ChannelMembership]:
        """Get members of a channel."""
        if not channel.can_view(requesting_user):
            raise PermissionError("Cannot view this channel")
        
        return ChannelRepository.get_members(channel)
    
    # ========== Channel Listing ==========
    
    @staticmethod
    def list_workspace_channels(workspace: Workspace, user: User) -> List[Channel]:
        """
        List all channels visible to user in a workspace.
        
        Args:
            workspace: The workspace
            user: User requesting the list
            
        Returns:
            List of channels
        """
        if not workspace.has_member(user):
            raise PermissionError("Must be a workspace member to view channels")
        
        return ChannelRepository.get_visible_channels(workspace, user)
    
    @staticmethod
    def get_channel_detail(channel_id: int, user: User) -> Channel:
        """
        Get channel details.
        
        Args:
            channel_id: Channel ID
            user: User requesting details
            
        Returns:
            Channel
        """
        channel = ChannelRepository.get_by_id(channel_id)
        if not channel:
            raise ChannelError("Channel not found")
        
        if not channel.can_view(user):
            raise PermissionError("Cannot view this channel")
        
        return channel
    
    # ========== Messaging ==========
    
    @staticmethod
    def post_message(channel: Channel, sender: User, content: str, 
                     parent_message: Optional[Message] = None) -> Message:
        """
        Post a message to a channel.
        
        Args:
            channel: Channel to post in
            sender: User sending the message
            content: Message content
            parent_message: Parent message for thread replies
            
        Returns:
            Created message
        """
        if not channel.can_post(sender):
            raise PermissionError("Cannot post to this channel")
        
        if channel.is_archived:
            raise ChannelError("Cannot post to archived channels")
        
        message = ChannelRepository.create_message(
            channel=channel,
            sender=sender,
            content=content,
            parent_message=parent_message,
            is_thread_reply=parent_message is not None
        )
        
        # Mark channel as read for sender
        membership = ChannelRepository.get_membership(channel, sender)
        if membership:
            membership.mark_as_read()
        
        return message
    
    @staticmethod
    def edit_message(message: Message, user: User, new_content: str) -> Message:
        """Edit a message."""
        if message.sender != user:
            raise PermissionError("Can only edit your own messages")
        
        if message.is_deleted:
            raise ChannelError("Cannot edit deleted messages")
        
        message.edit(new_content)
        return message
    
    @staticmethod
    def delete_message(message: Message, user: User) -> bool:
        """Delete a message."""
        # Can delete own messages or channel admin can delete any
        if message.sender != user and not message.channel.can_manage(user):
            raise PermissionError("Can only delete your own messages")
        
        message.soft_delete()
        return True
    
    @staticmethod
    def get_channel_messages(channel: Channel, user: User, 
                            limit: int = 50, 
                            before_id: Optional[int] = None) -> List[Message]:
        """
        Get messages from a channel.
        
        Args:
            channel: Channel to get messages from
            user: User requesting messages
            limit: Number of messages to return
            before_id: Get messages before this message ID (pagination)
            
        Returns:
            List of messages
        """
        if not channel.can_view(user):
            raise PermissionError("Cannot view this channel")
        
        return ChannelRepository.get_messages(channel, limit=limit, before_id=before_id)
    
    @staticmethod
    def mark_channel_as_read(channel: Channel, user: User) -> bool:
        """Mark all messages in channel as read for user."""
        membership = ChannelRepository.get_membership(channel, user)
        if membership:
            membership.mark_as_read()
            return True
        return False
    
    @staticmethod
    def get_unread_count(channel: Channel, user: User) -> int:
        """Get unread message count for user in channel."""
        membership = ChannelRepository.get_membership(channel, user)
        if membership:
            return membership.get_unread_count()
        return 0

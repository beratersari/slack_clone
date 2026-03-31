"""
Notification Repository - Repository Layer
Handles data access operations for Notification and Mention entities.
"""
from typing import Optional, List
from django.db.models import Q
from domain.models.notification import Notification, Mention, NotificationType
from domain.models.user import User
from domain.models.workspace import Workspace
from domain.models.channel import Channel, Message
from domain.models.direct_message import DirectMessage, DirectMessageConversation


class NotificationRepository:
    """
    Repository for Notification data access operations.
    """
    
    @staticmethod
    def get_by_id(notification_id: int) -> Optional[Notification]:
        """Get notification by ID."""
        try:
            return Notification.objects.get(id=notification_id)
        except Notification.DoesNotExist:
            return None
    
    @staticmethod
    def get_user_notifications(user: User, unread_only: bool = False,
                               limit: int = 50, offset: int = 0) -> List[Notification]:
        """Get notifications for a user."""
        queryset = Notification.objects.filter(recipient=user)
        
        if unread_only:
            queryset = queryset.filter(is_read=False)
        
        return list(queryset.select_related(
            'sender', 'workspace', 'channel', 'message', 'direct_message', 'dm_conversation'
        )[offset:offset + limit])
    
    @staticmethod
    def get_unread_count(user: User) -> int:
        """Get count of unread notifications for a user."""
        return Notification.objects.filter(recipient=user, is_read=False).count()
    
    @staticmethod
    def create_notification(
        recipient: User,
        sender: Optional[User],
        notification_type: str,
        title: str,
        body: str = '',
        workspace: Optional[Workspace] = None,
        channel: Optional[Channel] = None,
        message: Optional[Message] = None,
        direct_message: Optional[DirectMessage] = None,
        dm_conversation: Optional[DirectMessageConversation] = None
    ) -> Notification:
        """Create a new notification."""
        return Notification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            body=body,
            workspace=workspace,
            channel=channel,
            message=message,
            direct_message=direct_message,
            dm_conversation=dm_conversation
        )
    
    @staticmethod
    def mark_as_read(notification: Notification) -> None:
        """Mark a notification as read."""
        notification.mark_as_read()
    
    @staticmethod
    def mark_all_as_read(user: User) -> int:
        """Mark all notifications as read for a user. Returns count."""
        count = Notification.objects.filter(recipient=user, is_read=False).count()
        Notification.mark_all_as_read(user)
        return count
    
    @staticmethod
    def delete_notification(notification_id: int, user: User) -> bool:
        """Delete a notification (only if it belongs to user)."""
        try:
            notification = Notification.objects.get(id=notification_id, recipient=user)
            notification.delete()
            return True
        except Notification.DoesNotExist:
            return False
    
    @staticmethod
    def delete_all_user_notifications(user: User) -> int:
        """Delete all notifications for a user. Returns count."""
        count, _ = Notification.objects.filter(recipient=user).delete()
        return count


class MentionRepository:
    """
    Repository for Mention data access operations.
    """
    
    @staticmethod
    def get_mentions_for_message(message_id: int) -> List[Mention]:
        """Get all mentions for a channel message."""
        return list(Mention.objects.filter(
            message_id=message_id
        ).select_related('mentioned_user'))
    
    @staticmethod
    def get_mentions_for_dm(direct_message_id: int) -> List[Mention]:
        """Get all mentions for a direct message."""
        return list(Mention.objects.filter(
            direct_message_id=direct_message_id
        ).select_related('mentioned_user'))
    
    @staticmethod
    def get_user_mentions(user: User, limit: int = 20) -> List[Mention]:
        """Get mentions where user was mentioned."""
        return list(Mention.objects.filter(
            mentioned_user=user
        ).select_related(
            'message', 'direct_message', 'message__channel', 'message__sender'
        ).order_by('-created_at')[:limit])
    
    @staticmethod
    def get_channel_mentions_for_user(user: User, workspace: Workspace, 
                                      limit: int = 20) -> List[Mention]:
        """Get @channel/@here mentions in channels user is part of."""
        # Get user's channel IDs
        from domain.models.channel import ChannelMembership
        channel_ids = ChannelMembership.objects.filter(
            user=user,
            channel__workspace=workspace,
            is_active=True
        ).values_list('channel_id', flat=True)
        
        return list(Mention.objects.filter(
            Q(message__channel_id__in=channel_ids) &
            Q(mention_type__in=['channel', 'here'])
        ).select_related(
            'message', 'message__channel', 'message__sender'
        ).order_by('-created_at')[:limit])
    
    @staticmethod
    def create_mentions_for_message(message: Message) -> List[Mention]:
        """Parse and create mentions for a channel message."""
        return Mention.parse_mentions(
            content=message.content,
            message=message,
            direct_message=None
        )
    
    @staticmethod
    def create_mentions_for_dm(direct_message: DirectMessage) -> List[Mention]:
        """Parse and create mentions for a direct message."""
        return Mention.parse_mentions(
            content=direct_message.content,
            message=None,
            direct_message=direct_message
        )

"""
Notification Service - Services Layer
Handles business logic for notifications and mentions.
Similar to Slack's notification system.
"""
from typing import List, Optional
from domain.models.notification import Notification, Mention, NotificationType
from domain.models.user import User
from domain.models.workspace import Workspace
from domain.models.channel import Channel, Message
from domain.models.direct_message import DirectMessage, DirectMessageConversation
from repository.notification_repository import NotificationRepository, MentionRepository
from repository.user_repository import UserRepository


class NotificationService:
    """
    Service for handling notification business logic.
    """
    
    @staticmethod
    def get_user_notifications(
        user: User,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """Get notifications for a user."""
        return NotificationRepository.get_user_notifications(
            user=user,
            unread_only=unread_only,
            limit=limit,
            offset=offset
        )
    
    @staticmethod
    def get_unread_count(user: User) -> int:
        """Get unread notification count."""
        return NotificationRepository.get_unread_count(user)
    
    @staticmethod
    def mark_as_read(notification_id: int, user: User) -> bool:
        """Mark a notification as read."""
        notification = NotificationRepository.get_by_id(notification_id)
        if notification and notification.recipient == user:
            notification.mark_as_read()
            return True
        return False
    
    @staticmethod
    def mark_all_as_read(user: User) -> int:
        """Mark all notifications as read."""
        return NotificationRepository.mark_all_as_read(user)
    
    @staticmethod
    def delete_notification(notification_id: int, user: User) -> bool:
        """Delete a notification."""
        return NotificationRepository.delete_notification(notification_id, user)
    
    @staticmethod
    def create_mention_notifications(message: Message, sender: User, workspace: Workspace) -> List[Notification]:
        """
        Create notifications for users mentioned in a channel message.
        Handles @username, @channel, @here, @everyone.
        """
        notifications = []
        
        # Parse mentions from message content
        mentions = MentionRepository.create_mentions_for_message(message)
        
        if not mentions:
            return notifications
        
        # Process each mention
        for mention in mentions:
            if mention.mention_type == Mention.MentionType.USER and mention.mentioned_user:
                # Specific user mention
                if mention.mentioned_user != sender:  # Don't notify self
                    notif = NotificationRepository.create_notification(
                        recipient=mention.mentioned_user,
                        sender=sender,
                        notification_type=NotificationType.MENTION,
                        title=f"{sender.get_short_name()} mentioned you",
                        body=message.content[:100],
                        workspace=workspace,
                        channel=message.channel,
                        message=message
                    )
                    notifications.append(notif)
            
            elif mention.mention_type in [Mention.MentionType.CHANNEL, Mention.MentionType.HERE]:
                # @channel or @here - notify all channel members
                from repository.channel_repository import ChannelRepository
                members = ChannelRepository.get_members(message.channel)
                
                for membership in members:
                    member = membership.user
                    if member != sender:  # Don't notify self
                        notif = NotificationRepository.create_notification(
                            recipient=member,
                            sender=sender,
                            notification_type=NotificationType.MENTION,
                            title=f"{sender.get_short_name()} mentioned @{'channel' if mention.mention_type == Mention.MentionType.CHANNEL else 'here'}",
                            body=message.content[:100],
                            workspace=workspace,
                            channel=message.channel,
                            message=message
                        )
                        notifications.append(notif)
        
        return notifications
    
    @staticmethod
    def create_dm_notification(direct_message: DirectMessage, sender: User, 
                                conversation: DirectMessageConversation) -> List[Notification]:
        """
        Create notifications for DM recipients.
        """
        notifications = []
        
        # Parse mentions in DM
        mentions = MentionRepository.create_mentions_for_dm(direct_message)
        
        # Get all participants except sender
        participants = conversation.participants.filter(is_active=True).select_related('user')
        
        for participant in participants:
            if participant.user == sender:
                continue  # Don't notify self
            
            # Check if user was mentioned
            was_mentioned = any(
                m.mentioned_user == participant.user 
                for m in mentions 
                if m.mention_type == Mention.MentionType.USER
            )
            
            notif_type = NotificationType.MENTION if was_mentioned else NotificationType.DM_MESSAGE
            title = f"{sender.get_short_name()} mentioned you" if was_mentioned else f"New message from {sender.get_short_name()}"
            
            notif = NotificationRepository.create_notification(
                recipient=participant.user,
                sender=sender,
                notification_type=notif_type,
                title=title,
                body=direct_message.content[:100],
                workspace=conversation.workspace,
                dm_conversation=conversation,
                direct_message=direct_message
            )
            notifications.append(notif)
        
        return notifications
    
    @staticmethod
    def create_reaction_notification(message: Message, reactor: User, emoji: str):
        """Create notification when someone reacts to your message."""
        if message.sender == reactor:
            return None  # Don't notify self
        
        return NotificationRepository.create_notification(
            recipient=message.sender,
            sender=reactor,
            notification_type=NotificationType.REACTION,
            title=f"{reactor.get_short_name()} reacted with {emoji}",
            body=message.content[:100],
            workspace=message.channel.workspace,
            channel=message.channel,
            message=message
        )
    
    @staticmethod
    def create_thread_reply_notification(parent_message: Message, replier: User, reply_content: str):
        """Create notification when someone replies to a thread you participated in."""
        if parent_message.sender == replier:
            return None  # Don't notify self
        
        return NotificationRepository.create_notification(
            recipient=parent_message.sender,
            sender=replier,
            notification_type=NotificationType.THREAD_REPLY,
            title=f"{replier.get_short_name()} replied to your thread",
            body=reply_content[:100],
            workspace=parent_message.channel.workspace,
            channel=parent_message.channel,
            message=parent_message
        )

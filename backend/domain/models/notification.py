"""
Notification Model - Domain Layer
Defines the Notification and Mention entities for Slack-like notifications.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class NotificationType(models.TextChoices):
    """Enumeration of notification types."""
    MENTION = 'mention', _('Mention')
    CHANNEL_MESSAGE = 'channel_message', _('Channel Message')
    DM_MESSAGE = 'dm_message', _('Direct Message')
    REACTION = 'reaction', _('Reaction')
    THREAD_REPLY = 'thread_reply', _('Thread Reply')
    WORKSPACE_INVITE = 'workspace_invite', _('Workspace Invite')
    CHANNEL_INVITE = 'channel_invite', _('Channel Invite')


class Notification(models.Model):
    """
    Notification model for user notifications.
    Similar to Slack's notification system.
    
    Types:
    - mention: Someone mentioned you (@username)
    - channel_message: New message in a channel you're in (based on notification settings)
    - dm_message: New DM
    - reaction: Someone reacted to your message
    - thread_reply: Reply to a thread you're in
    - workspace_invite: Workspace invitation
    - channel_invite: Channel invitation
    """
    
    # Recipient
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text=_('User who receives the notification')
    )
    
    # Sender (who triggered the notification)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications_sent',
        null=True,
        blank=True,
        help_text=_('User who triggered the notification')
    )
    
    # Notification type
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        help_text=_('Type of notification')
    )
    
    # Title and body for display
    title = models.CharField(
        max_length=200,
        help_text=_('Notification title')
    )
    body = models.TextField(
        max_length=500,
        blank=True,
        help_text=_('Notification body/preview')
    )
    
    # Links to related objects
    workspace = models.ForeignKey(
        'domain.Workspace',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text=_('Related workspace')
    )
    channel = models.ForeignKey(
        'domain.Channel',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text=_('Related channel')
    )
    message = models.ForeignKey(
        'domain.Message',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text=_('Related channel message')
    )
    direct_message = models.ForeignKey(
        'domain.DirectMessage',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text=_('Related direct message')
    )
    dm_conversation = models.ForeignKey(
        'domain.DirectMessageConversation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text=_('Related DM conversation')
    )
    
    # Status
    is_read = models.BooleanField(
        default=False,
        help_text=_('Whether the notification has been read')
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the notification was read')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['recipient', 'notification_type']),
        ]
    
    def __str__(self):
        return f"Notification for {self.recipient.email}: {self.notification_type}"
    
    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @classmethod
    def mark_all_as_read(cls, user):
        """Mark all notifications as read for a user."""
        cls.objects.filter(
            recipient=user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())


class Mention(models.Model):
    """
    Mention model for tracking @mentions in messages.
    Parses and stores mentions like @username, @channel, @here.
    """
    
    class MentionType(models.TextChoices):
        USER = 'user', _('User Mention')
        CHANNEL = 'channel', _('Channel Mention (@channel)')
        HERE = 'here', _('Here Mention (@here)')
        EVERYONE = 'everyone', _('Everyone Mention (@everyone)')
    
    # Message that contains the mention
    message = models.ForeignKey(
        'domain.Message',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='mentions',
        help_text=_('Channel message with the mention')
    )
    direct_message = models.ForeignKey(
        'domain.DirectMessage',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='mentions',
        help_text=_('Direct message with the mention')
    )
    
    # Who was mentioned
    mentioned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='mentions_received',
        help_text=_('User who was mentioned (null for @channel/@here)')
    )
    
    # Mention type
    mention_type = models.CharField(
        max_length=20,
        choices=MentionType.choices,
        default=MentionType.USER,
        help_text=_('Type of mention')
    )
    
    # Raw mention text (e.g., "@alice")
    mention_text = models.CharField(
        max_length=100,
        help_text=_('Original mention text')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('mention')
        verbose_name_plural = _('mentions')
        db_table = 'mentions'
        indexes = [
            models.Index(fields=['message', 'mention_type']),
            models.Index(fields=['direct_message', 'mention_type']),
            models.Index(fields=['mentioned_user', '-created_at']),
        ]
    
    def __str__(self):
        if self.mentioned_user:
            return f"@{self.mentioned_user.username} in message"
        return f"{self.mention_type} mention"
    
    @classmethod
    def parse_mentions(cls, content, message=None, direct_message=None):
        """
        Parse @mentions from message content and create Mention objects.
        
        Supports:
        - @username - specific user
        - @channel - all channel members
        - @here - all online members
        - @everyone - all members (same as @channel)
        
        Returns:
            List of created Mention objects
        """
        import re
        mentions = []
        
        if not content:
            return mentions
        
        # Find all @mentions
        # Note: special mentions (@channel, @here, @everyone) must come FIRST
        # so they match before username pattern (which would match "channel" from "@channel")
        mention_pattern = r'@(@channel|@here|@everyone|[a-zA-Z0-9_-]+)'
        matches = re.findall(mention_pattern, content)
        
        from domain.models.user import User
        
        for match in matches:
            mention_text = f"@{match}"
            
            # Special mentions (match is without the @ prefix due to regex capture group)
            if match in ('channel', 'everyone'):
                mention = cls.objects.create(
                    message=message,
                    direct_message=direct_message,
                    mentioned_user=None,
                    mention_type=cls.MentionType.CHANNEL,
                    mention_text=mention_text
                )
                mentions.append(mention)
            
            elif match == 'here':
                mention = cls.objects.create(
                    message=message,
                    direct_message=direct_message,
                    mentioned_user=None,
                    mention_type=cls.MentionType.HERE,
                    mention_text=mention_text
                )
                mentions.append(mention)
            
            else:
                # Try to find user by username
                try:
                    mentioned_user = User.objects.get(username__iexact=match)
                    mention = cls.objects.create(
                        message=message,
                        direct_message=direct_message,
                        mentioned_user=mentioned_user,
                        mention_type=cls.MentionType.USER,
                        mention_text=mention_text
                    )
                    mentions.append(mention)
                except User.DoesNotExist:
                    # Unknown username, skip
                    pass
        
        return mentions

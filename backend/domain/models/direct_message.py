"""
Direct Message Model - Domain Layer
Defines the Direct Message entities for Slack-like DM conversations.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class DirectMessageConversation(models.Model):
    """
    Model representing a DM conversation between users.
    Can be 1:1 (is_group=False) or group DM (is_group=True).
    """
    
    # Workspace context (DMs are still within a workspace)
    workspace = models.ForeignKey(
        'domain.Workspace',
        on_delete=models.CASCADE,
        related_name='dm_conversations',
        help_text=_('The workspace this DM belongs to')
    )
    
    # Conversation type
    is_group = models.BooleanField(
        default=False,
        help_text=_('Is this a group DM (more than 2 people)')
    )
    
    # For group DMs, a name is optional
    name = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Optional name for group DMs')
    )
    
    # Creator
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_dm_conversations',
        help_text=_('User who created this conversation')
    )
    
    # Settings
    is_active = models.BooleanField(
        default=True,
        help_text=_('Whether this conversation is active')
    )
    is_archived = models.BooleanField(
        default=False,
        help_text=_('Archived conversations are hidden from the list')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    # For tracking last message (for sorting and preview)
    last_message_at = models.DateTimeField(
        default=timezone.now,
        help_text=_('When the last message was sent')
    )
    last_message_preview = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Preview of the last message')
    )
    
    class Meta:
        verbose_name = _('DM conversation')
        verbose_name_plural = _('DM conversations')
        db_table = 'dm_conversations'
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['workspace', 'is_active']),
            models.Index(fields=['workspace', 'created_by']),
            models.Index(fields=['last_message_at']),
        ]
    
    def __str__(self):
        if self.name:
            return f"{self.name} ({self.workspace.name})"
        participants = self.participants.select_related('user').all()[:3]
        names = [p.user.get_short_name() for p in participants]
        if self.participants.count() > 3:
            names.append(f"+{self.participants.count() - 3}")
        return f"DM: {', '.join(names)}"
    
    def get_display_name(self, for_user=None):
        """Get display name for this conversation."""
        if self.name:
            return self.name
        
        # Get other participants
        participants = self.participants.filter(is_active=True).select_related('user')
        if for_user:
            participants = participants.exclude(user=for_user)
        
        names = [p.user.get_short_name() for p in participants[:3]]
        count = participants.count()
        
        if count > 3:
            names.append(f"+{count - 3} more")
        
        return ', '.join(names) if names else 'Empty conversation'
    
    def has_participant(self, user):
        """Check if user is a participant in this conversation."""
        return self.participants.filter(user=user, is_active=True).exists()
    
    def add_participant(self, user, added_by=None):
        """Add a participant to the conversation."""
        # Check if user is workspace member
        if not self.workspace.has_member(user):
            raise ValueError("User must be a workspace member")
        
        participant, created = DirectMessageParticipant.objects.get_or_create(
            conversation=self,
            user=user,
            defaults={'added_by': added_by, 'is_active': True}
        )
        if not created and not participant.is_active:
            participant.is_active = True
            participant.save()
        return participant
    
    def remove_participant(self, user):
        """Remove a participant from the conversation."""
        try:
            participant = self.participants.get(user=user, is_active=True)
            participant.is_active = False
            participant.left_at = timezone.now()
            participant.save()
            return True
        except DirectMessageParticipant.DoesNotExist:
            return False
    
    def archive(self):
        """Archive the conversation."""
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save(update_fields=['is_archived', 'archived_at'])
    
    def unarchive(self):
        """Unarchive the conversation."""
        self.is_archived = False
        self.archived_at = None
        self.save(update_fields=['is_archived', 'archived_at'])
    
    def update_last_message(self, message):
        """Update last message info."""
        self.last_message_at = message.created_at
        preview = message.content[:200] if len(message.content) > 200 else message.content
        self.last_message_preview = preview
        self.save(update_fields=['last_message_at', 'last_message_preview'])
    
    def get_participant_count(self):
        """Get number of active participants."""
        return self.participants.filter(is_active=True).count()


class DirectMessageParticipant(models.Model):
    """
    Participant in a DM conversation.
    Tracks membership and notification preferences.
    """
    
    conversation = models.ForeignKey(
        DirectMessageConversation,
        on_delete=models.CASCADE,
        related_name='participants',
        help_text=_('The conversation')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dm_participants',
        help_text=_('The participant')
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text=_('Whether the participant is still in the conversation')
    )
    
    # Join info
    joined_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dm_users_added',
        help_text=_('Who added this participant')
    )
    left_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the participant left')
    )
    
    # Notification preferences
    muted = models.BooleanField(
        default=False,
        help_text=_('Mute this conversation')
    )
    notify_mentions_only = models.BooleanField(
        default=False,
        help_text=_('Only notify on mentions')
    )
    
    # Last read tracking
    last_read_at = models.DateTimeField(
        default=timezone.now,
        help_text=_('Last time user read messages')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('DM participant')
        verbose_name_plural = _('DM participants')
        db_table = 'dm_participants'
        unique_together = ['conversation', 'user']
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['conversation', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} in {self.conversation}"
    
    def mark_as_read(self):
        """Update last read timestamp."""
        self.last_read_at = timezone.now()
        self.save(update_fields=['last_read_at', 'updated_at'])
    
    def get_unread_count(self):
        """Get number of unread messages."""
        return self.conversation.messages.filter(
            created_at__gt=self.last_read_at
        ).exclude(sender=self.user).count()


class DirectMessage(models.Model):
    """
    Model representing a direct message.
    Similar to Message but for DMs.
    """
    
    conversation = models.ForeignKey(
        DirectMessageConversation,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text=_('The conversation this message belongs to')
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='direct_messages_sent',
        help_text=_('User who sent the message')
    )
    
    # Content
    content = models.TextField(
        help_text=_('Message content')
    )
    
    # Thread support for DMs
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        help_text=_('Parent message for thread replies')
    )
    is_thread_reply = models.BooleanField(
        default=False,
        help_text=_('Is this a reply in a thread')
    )
    
    # Status
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('direct message')
        verbose_name_plural = _('direct messages')
        db_table = 'direct_messages'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['parent_message', 'created_at']),
        ]
    
    def __str__(self):
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"{self.sender.email}: {preview}"
    
    def edit(self, new_content):
        """Edit message content."""
        self.content = new_content
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save(update_fields=['content', 'is_edited', 'edited_at', 'updated_at'])
    
    def soft_delete(self):
        """Soft delete the message."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    
    @property
    def is_thread_parent(self):
        """Check if this message has replies."""
        return self.replies.filter(is_deleted=False).exists()

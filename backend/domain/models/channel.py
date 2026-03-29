"""
Channel Model - Domain Layer
Defines the Channel entity for Slack-like workspace channels.
"""
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class ChannelType(models.TextChoices):
    """Enumeration of channel types."""
    PUBLIC = 'public', _('Public')
    PRIVATE = 'private', _('Private')


class Channel(models.Model):
    """
    Channel model representing a Slack-like channel within a workspace.
    
    Channels can be:
    - Public: Any workspace member can join/leave
    - Private: Invite-only, hidden from non-members
    
    Each workspace gets a #general channel by default.
    """
    
    # Relations
    workspace = models.ForeignKey(
        'domain.Workspace',
        on_delete=models.CASCADE,
        related_name='channels',
        help_text=_('The workspace this channel belongs to')
    )
    
    # Creator (owner of the channel)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_channels',
        help_text=_('User who created this channel')
    )
    
    # Basic info
    name = models.CharField(
        max_length=80,
        help_text=_('Channel name (without the #)')
    )
    normalized_name = models.CharField(
        max_length=80,
        help_text=_('Lowercase name for uniqueness checks')
    )
    
    # Channel type
    channel_type = models.CharField(
        max_length=10,
        choices=ChannelType.choices,
        default=ChannelType.PUBLIC,
        help_text=_('Public channels are visible to all workspace members')
    )
    
    # Description and topic
    topic = models.CharField(
        max_length=250,
        blank=True,
        help_text=_('Brief topic shown at the top of the channel')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Detailed description of the channel purpose')
    )
    
    # Settings
    is_default = models.BooleanField(
        default=False,
        help_text=_('Is this the default #general channel')
    )
    is_archived = models.BooleanField(
        default=False,
        help_text=_('Archived channels are read-only')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the channel was archived')
    )
    
    class Meta:
        verbose_name = _('channel')
        verbose_name_plural = _('channels')
        ordering = ['-is_default', 'name']
        db_table = 'channels'
        # Unique channel name per workspace
        unique_together = ['workspace', 'normalized_name']
        indexes = [
            models.Index(fields=['workspace', 'channel_type']),
            models.Index(fields=['workspace', 'is_archived']),
            models.Index(fields=['normalized_name']),
        ]
    
    def __str__(self):
        return f"#{self.name} ({self.workspace.name})"
    
    def save(self, *args, **kwargs):
        """Normalize name before saving."""
        if not self.normalized_name:
            self.normalized_name = self.name.lower()
        super().save(*args, **kwargs)
    
    @property
    def display_name(self):
        """Return channel name with # prefix."""
        return f"#{self.name}"
    
    @property
    def is_public(self):
        """Check if channel is public."""
        return self.channel_type == ChannelType.PUBLIC
    
    @property
    def is_private(self):
        """Check if channel is private."""
        return self.channel_type == ChannelType.PRIVATE
    
    def archive(self, archived_by=None):
        """Archive the channel (make read-only)."""
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save(update_fields=['is_archived', 'archived_at'])
    
    def unarchive(self):
        """Unarchive the channel."""
        self.is_archived = False
        self.archived_at = None
        self.save(update_fields=['is_archived', 'archived_at'])
    
    def get_member_count(self):
        """Get total number of members in channel."""
        return self.memberships.filter(is_active=True).count()
    
    def has_member(self, user):
        """Check if user is a member of this channel."""
        return self.memberships.filter(user=user, is_active=True).exists()
    
    def can_join(self, user):
        """Check if user can join this channel."""
        # Check if user is workspace member
        from domain.models.workspace import WorkspaceMembership
        if not WorkspaceMembership.objects.filter(
            workspace=self.workspace,
            user=user,
            is_active=True
        ).exists():
            return False
        
        # Public channels: anyone can join
        if self.is_public:
            return True
        
        # Private channels: must be invited
        return False
    
    def can_view(self, user):
        """Check if user can view this channel."""
        # Public channels: any workspace member can view
        if self.is_public:
            from domain.models.workspace import WorkspaceMembership
            return WorkspaceMembership.objects.filter(
                workspace=self.workspace,
                user=user,
                is_active=True
            ).exists()
        
        # Private channels: only members can view
        return self.has_member(user)
    
    def can_post(self, user):
        """Check if user can post messages."""
        if self.is_archived:
            return False
        return self.has_member(user)
    
    def can_manage(self, user):
        """Check if user can manage channel settings."""
        # Channel creator or workspace admin/owner
        if self.created_by == user:
            return True
        return self.workspace.can_manage(user)


class ChannelMembership(models.Model):
    """
    Channel membership model tracking which users are in which channels.
    """
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name='memberships',
        help_text=_('The channel')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='channel_memberships',
        help_text=_('The member')
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text=_('Whether the membership is active')
    )
    
    # Join info
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='channel_invites_sent',
        help_text=_('User who invited this member (null if joined public channel)')
    )
    
    # Notification preferences
    notify_all_messages = models.BooleanField(
        default=False,
        help_text=_('Notify on all messages (default: only mentions)')
    )
    muted = models.BooleanField(
        default=False,
        help_text=_('Mute this channel')
    )
    
    # Last read tracking
    last_read_at = models.DateTimeField(
        default=timezone.now,
        help_text=_('Last time user read messages in this channel')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('channel membership')
        verbose_name_plural = _('channel memberships')
        db_table = 'channel_memberships'
        unique_together = ['channel', 'user']
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['channel', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} in {self.channel.display_name}"
    
    def mark_as_read(self):
        """Update last read timestamp."""
        self.last_read_at = timezone.now()
        self.save(update_fields=['last_read_at', 'updated_at'])
    
    def get_unread_count(self):
        """Get number of unread messages."""
        return self.channel.messages.filter(
            created_at__gt=self.last_read_at
        ).exclude(sender=self.user).count()


class Message(models.Model):
    """
    Message model representing a post in a channel.
    """
    
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text=_('The channel this message belongs to')
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages_sent',
        help_text=_('User who sent the message')
    )
    
    # Content
    content = models.TextField(
        help_text=_('Message content (supports markdown-like formatting)')
    )
    
    # Thread support (for future threading feature)
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
        verbose_name = _('message')
        verbose_name_plural = _('messages')
        db_table = 'messages'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['channel', 'created_at']),
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


class MessageReaction(models.Model):
    """
    Model representing an emoji reaction to a message.
    Similar to Slack's reaction feature.
    """
    
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='reactions',
        help_text=_('The message being reacted to')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_reactions',
        help_text=_('User who reacted')
    )
    
    # Emoji - can be unicode emoji or custom emoji name
    emoji = models.CharField(
        max_length=50,
        help_text=_('Emoji unicode or shortcode (e.g., ":thumbsup:")')
    )
    emoji_name = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Name of the emoji for custom emojis')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('message reaction')
        verbose_name_plural = _('message reactions')
        db_table = 'message_reactions'
        unique_together = ['message', 'user', 'emoji']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['message', 'emoji']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} reacted with {self.emoji}"


class FileAttachment(models.Model):
    """
    Model representing a file attached to a message.
    """
    
    # Can be attached to either channel message or DM
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='attachments',
        help_text=_('The channel message this file is attached to')
    )
    direct_message = models.ForeignKey(
        'domain.DirectMessage',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='attachments',
        help_text=_('The DM this file is attached to')
    )
    
    # Uploader
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='file_attachments',
        help_text=_('User who uploaded the file')
    )
    
    # File info
    file = models.FileField(
        upload_to='attachments/%Y/%m/',
        help_text=_('The uploaded file')
    )
    file_name = models.CharField(
        max_length=255,
        help_text=_('Original file name')
    )
    file_size = models.BigIntegerField(
        help_text=_('File size in bytes')
    )
    mime_type = models.CharField(
        max_length=100,
        help_text=_('MIME type of the file')
    )
    
    # File type categorization
    class FileType(models.TextChoices):
        IMAGE = 'image', _('Image')
        VIDEO = 'video', _('Video')
        AUDIO = 'audio', _('Audio')
        DOCUMENT = 'document', _('Document')
        CODE = 'code', _('Code')
        ARCHIVE = 'archive', _('Archive')
        OTHER = 'other', _('Other')
    
    file_type = models.CharField(
        max_length=20,
        choices=FileType.choices,
        default=FileType.OTHER,
        help_text=_('Category of the file')
    )
    
    # For images: store dimensions
    width = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_('Image width in pixels')
    )
    height = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_('Image height in pixels')
    )
    
    # Thumbnail for images/videos
    thumbnail_url = models.URLField(
        blank=True,
        null=True,
        help_text=_('URL to thumbnail image')
    )
    
    # Status
    is_deleted = models.BooleanField(
        default=False,
        help_text=_('Whether the file has been deleted')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('file attachment')
        verbose_name_plural = _('file attachments')
        db_table = 'file_attachments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['message', 'created_at']),
            models.Index(fields=['direct_message', 'created_at']),
            models.Index(fields=['uploaded_by', 'created_at']),
            models.Index(fields=['file_type']),
        ]
    
    def __str__(self):
        return f"{self.file_name} ({self.get_file_type_display()})"
    
    @property
    def is_image(self):
        """Check if file is an image."""
        return self.file_type == self.FileType.IMAGE
    
    @property
    def is_video(self):
        """Check if file is a video."""
        return self.file_type == self.FileType.VIDEO
    
    @property
    def is_audio(self):
        """Check if file is audio."""
        return self.file_type == self.FileType.AUDIO
    
    @property
    def human_readable_size(self):
        """Return human-readable file size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024
        return f"{self.file_size:.1f} TB"
    
    def soft_delete(self):
        """Soft delete the attachment."""
        self.is_deleted = True
        self.save(update_fields=['is_deleted', 'updated_at'])

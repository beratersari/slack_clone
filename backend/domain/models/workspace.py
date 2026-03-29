"""
Workspace Model - Domain Layer
Defines the Workspace entity and membership for the Slack Clone.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import secrets
import string


class WorkspaceRole(models.TextChoices):
    """Enumeration of workspace roles."""
    OWNER = 'owner', _('Owner')
    ADMIN = 'admin', _('Admin')
    MEMBER = 'member', _('Member')


class Workspace(models.Model):
    """
    Workspace model representing a Slack workspace.
    
    Any user can create a workspace and becomes its owner.
    Workspaces can have multiple members with different roles.
    """
    
    # Basic info
    name = models.CharField(
        max_length=100,
        help_text=_('Name of the workspace')
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text=_('Unique URL-friendly identifier')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Description of the workspace')
    )
    
    # Owner (creator)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_workspaces',
        help_text=_('User who created and owns this workspace')
    )
    
    # Settings
    is_public = models.BooleanField(
        default=False,
        help_text=_('Whether the workspace is publicly discoverable')
    )
    allow_guests = models.BooleanField(
        default=True,
        help_text=_('Whether guests can be invited to this workspace')
    )
    
    # Branding
    icon_url = models.URLField(
        blank=True,
        null=True,
        help_text=_('Workspace icon URL')
    )
    
    # Invite settings
    invite_code = models.CharField(
        max_length=32,
        unique=True,
        blank=True,
        null=True,
        help_text=_('Unique code for joining the workspace')
    )
    invite_code_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the invite code expires')
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text=_('Whether the workspace is active')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('workspace')
        verbose_name_plural = _('workspaces')
        ordering = ['-created_at']
        db_table = 'workspaces'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['owner']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.slug})"
    
    def save(self, *args, **kwargs):
        """Generate invite code on first save if not provided."""
        if not self.invite_code:
            self.invite_code = self.generate_invite_code()
            self.invite_code_expires_at = timezone.now() + timezone.timedelta(days=30)
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_invite_code(length=16):
        """Generate a unique invite code."""
        alphabet = string.ascii_letters + string.digits
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(length))
            if not Workspace.objects.filter(invite_code=code).exists():
                return code
    
    def regenerate_invite_code(self):
        """Generate a new invite code."""
        self.invite_code = self.generate_invite_code()
        self.invite_code_expires_at = timezone.now() + timezone.timedelta(days=30)
        self.save(update_fields=['invite_code', 'invite_code_expires_at'])
        return self.invite_code
    
    def is_invite_code_valid(self):
        """Check if the invite code is still valid."""
        if not self.invite_code or not self.invite_code_expires_at:
            return False
        return timezone.now() < self.invite_code_expires_at
    
    def get_member_count(self):
        """Get total number of members in the workspace."""
        return self.memberships.filter(is_active=True).count()
    
    def has_member(self, user):
        """Check if a user is a member of this workspace."""
        return self.memberships.filter(user=user, is_active=True).exists()
    
    def get_user_role(self, user):
        """Get the role of a user in this workspace."""
        try:
            membership = self.memberships.get(user=user, is_active=True)
            return membership.role
        except WorkspaceMembership.DoesNotExist:
            return None
    
    def is_owner(self, user):
        """Check if user is the owner of this workspace."""
        return self.owner == user
    
    def is_admin(self, user):
        """Check if user is an admin or owner of this workspace."""
        if self.is_owner(user):
            return True
        role = self.get_user_role(user)
        return role == WorkspaceRole.ADMIN
    
    def can_manage(self, user):
        """Check if user can manage this workspace (owner or admin)."""
        return self.is_admin(user) or self.is_owner(user)


class WorkspaceMembership(models.Model):
    """
    Workspace membership model representing a user's membership in a workspace.
    Tracks role, join date, and status.
    """
    
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='memberships',
        help_text=_('The workspace')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workspace_memberships',
        help_text=_('The member user')
    )
    
    # Role in the workspace
    role = models.CharField(
        max_length=20,
        choices=WorkspaceRole.choices,
        default=WorkspaceRole.MEMBER,
        help_text=_('Role of the user in this workspace')
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
        related_name='sent_invites',
        help_text=_('User who invited this member')
    )
    invited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the invitation was sent')
    )
    
    # Notification preferences
    notify_mentions = models.BooleanField(default=True)
    notify_all_messages = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('workspace membership')
        verbose_name_plural = _('workspace memberships')
        db_table = 'workspace_memberships'
        unique_together = ['workspace', 'user']
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['workspace', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} in {self.workspace.name} ({self.get_role_display()})"
    
    @property
    def is_owner(self):
        """Check if member is the owner."""
        return self.role == WorkspaceRole.OWNER
    
    @property
    def is_admin(self):
        """Check if member is an admin or owner."""
        return self.role in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]
    
    def promote_to_admin(self):
        """Promote member to admin."""
        if self.role == WorkspaceRole.MEMBER:
            self.role = WorkspaceRole.ADMIN
            self.save(update_fields=['role', 'updated_at'])
    
    def demote_to_member(self):
        """Demote admin to member."""
        if self.role == WorkspaceRole.ADMIN:
            self.role = WorkspaceRole.MEMBER
            self.save(update_fields=['role', 'updated_at'])
    
    def deactivate(self):
        """Deactivate membership (remove from workspace)."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
    
    def reactivate(self):
        """Reactivate membership."""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])


class WorkspaceInvite(models.Model):
    """
    Model to track pending workspace invitations sent by email.
    """
    
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='pending_invites',
        help_text=_('The workspace being invited to')
    )
    email = models.EmailField(
        help_text=_('Email address of the invited user')
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workspace_invites_sent',
        help_text=_('User who sent the invitation')
    )
    
    # Invitation token
    token = models.CharField(
        max_length=64,
        unique=True,
        help_text=_('Unique invitation token')
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('declined', 'Declined'),
            ('expired', 'Expired'),
        ],
        default='pending'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('workspace invite')
        verbose_name_plural = _('workspace invites')
        db_table = 'workspace_invites'
        unique_together = ['workspace', 'email']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Invite to {self.workspace.name} for {self.email}"
    
    def save(self, *args, **kwargs):
        """Generate token and expiry on first save."""
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if invitation has expired."""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if invitation is still valid (pending and not expired)."""
        return self.status == 'pending' and not self.is_expired()
    
    def accept(self):
        """Mark invitation as accepted."""
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.save(update_fields=['status', 'accepted_at'])
    
    def decline(self):
        """Mark invitation as declined."""
        self.status = 'declined'
        self.save(update_fields=['status'])

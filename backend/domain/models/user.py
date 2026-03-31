"""
User Model - Domain Layer
Defines the core User entity with different user types for the Slack Clone.
"""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserType(models.TextChoices):
    """Enumeration of user types in the system."""
    ADMIN = 'admin', _('Admin')
    SUPER_USER = 'super_user', _('Super User')
    USER = 'user', _('User')


class UserManager(BaseUserManager):
    """Custom manager for User model."""
    
    def create_user(self, email, username, password=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError('The Email field must be set')
        if not username:
            raise ValueError('The Username field must be set')
        
        email = self.normalize_email(email)
        extra_fields.setdefault('user_type', UserType.USER)
        extra_fields.setdefault('is_active', True)
        
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        """Create and save a superuser (Admin)."""
        extra_fields.setdefault('user_type', UserType.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, username, password, **extra_fields)
    
    def create_super_user(self, email, username, password=None, **extra_fields):
        """Create and save a Super User (workspace manager)."""
        extra_fields.setdefault('user_type', UserType.SUPER_USER)
        extra_fields.setdefault('is_active', True)
        
        return self.create_user(email, username, password, **extra_fields)
    
    def admins(self):
        """Get all admin users."""
        return self.filter(user_type=UserType.ADMIN)
    
    def super_users(self):
        """Get all super users."""
        return self.filter(user_type=UserType.SUPER_USER)
    
    def regular_users(self):
        """Get all regular users."""
        return self.filter(user_type=UserType.USER)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model supporting different user types.
    
    User Types:
    - Admin: Full system access, can manage all users and settings
    - Super User: Can manage workspaces and users within their scope
    - User: Regular user with access to their workspaces and channels
    """
    
    # User type field
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.USER,
        help_text=_('Type of user determining their permissions level')
    )
    
    # Basic fields
    email = models.EmailField(
        _('email address'),
        unique=True,
        help_text=_('Unique email address used for login')
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        help_text=_('Unique username for display')
    )
    first_name = models.CharField(
        _('first name'),
        max_length=150,
        blank=True
    )
    last_name = models.CharField(
        _('last name'),
        max_length=150,
        blank=True
    )
    
    # Profile fields
    display_name = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Display name shown in the application')
    )
    avatar_url = models.URLField(
        blank=True,
        null=True,
        help_text=_('URL to user avatar image')
    )
    status = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('User status message')
    )
    
    # Status fields
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Whether this user account is active')
    )
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Whether user can log into admin site')
    )
    date_joined = models.DateTimeField(
        _('date joined'),
        default=timezone.now
    )
    last_active = models.DateTimeField(
        _('last active'),
        null=True,
        blank=True
    )
    
    # Verification fields
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Settings
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text=_('User preferred timezone')
    )
    language = models.CharField(
        max_length=10,
        default='en',
        help_text=_('User preferred language')
    )
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    
    # Django required fields
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    objects = UserManager()
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['display_name']),
            models.Index(fields=['is_active', 'last_active']),  # For online user queries
        ]
    
    def __str__(self):
        return f"{self.email} ({self.get_user_type_display()})"
    
    def get_full_name(self):
        """Return the full name of the user."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.display_name or self.username
    
    def get_short_name(self):
        """Return the short name of the user."""
        return self.display_name or self.first_name or self.username
    
    @property
    def is_admin(self):
        """Check if user is an admin."""
        return self.user_type == UserType.ADMIN
    
    @property
    def is_super_user(self):
        """Check if user is a super user."""
        return self.user_type == UserType.SUPER_USER
    
    @property
    def is_regular_user(self):
        """Check if user is a regular user."""
        return self.user_type == UserType.USER
    
    def update_last_active(self):
        """Update the last active timestamp."""
        self.last_active = timezone.now()
        self.save(update_fields=['last_active'])
    
    def verify_email(self):
        """Mark email as verified."""
        self.email_verified = True
        self.email_verified_at = timezone.now()
        self.save(update_fields=['email_verified', 'email_verified_at'])

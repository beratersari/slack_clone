"""
Django Admin Configuration
Registers all domain models in the Django admin interface.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from domain.models.user import User, UserType
from domain.models.workspace import Workspace, WorkspaceMembership, WorkspaceInvite, WorkspaceRole
from domain.models.channel import Channel, ChannelMembership, Message


# ============== User Admin ==============

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for User model."""
    
    list_display = [
        'email', 'username', 'get_full_name', 'user_type',
        'is_active', 'email_verified', 'date_joined', 'last_active'
    ]
    list_filter = ['user_type', 'is_active', 'email_verified', 'date_joined']
    search_fields = ['email', 'username', 'first_name', 'last_name', 'display_name']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal info', {
            'fields': ('first_name', 'last_name', 'display_name', 'avatar_url', 'status')
        }),
        ('User Type', {
            'fields': ('user_type',)
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Verification', {
            'fields': ('email_verified', 'email_verified_at'),
        }),
        ('Settings', {
            'fields': ('timezone', 'language', 'email_notifications', 'push_notifications'),
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined', 'last_active'),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'user_type'),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login', 'last_active', 'email_verified_at']
    
    def get_full_name(self, obj):
        """Display full name."""
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'


# ============== Workspace Membership Inline ==============

class WorkspaceMembershipInline(admin.TabularInline):
    """Inline admin for workspace memberships."""
    model = WorkspaceMembership
    extra = 1
    fields = ['user', 'role', 'is_active', 'joined_at']
    readonly_fields = ['joined_at']
    autocomplete_fields = ['user']
    
    def get_formset(self, request, obj=None, **kwargs):
        """Customize formset - default to Member role for new entries."""
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['role'].initial = WorkspaceRole.MEMBER
        return formset


class WorkspaceInviteInline(admin.TabularInline):
    """Inline admin for workspace invites."""
    model = WorkspaceInvite
    extra = 0
    fields = ['email', 'invited_by', 'status', 'created_at', 'expires_at']
    readonly_fields = ['created_at', 'token']


class ChannelInline(admin.TabularInline):
    """Inline admin for channels."""
    model = Channel
    extra = 0
    fields = ['name', 'channel_type', 'is_default', 'is_archived', 'created_by']
    readonly_fields = ['is_default']


# ============== Workspace Admin ==============

@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    """Admin configuration for Workspace model."""
    
    list_display = [
        'name', 'slug', 'owner', 'member_count_display',
        'is_public', 'is_active', 'created_at'
    ]
    list_filter = ['is_public', 'is_active', 'created_at', 'allow_guests']
    search_fields = ['name', 'slug', 'description', 'owner__email', 'owner__username']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'description', 'owner')
        }),
        ('Settings', {
            'fields': ('is_public', 'allow_guests', 'is_active'),
        }),
        ('Branding', {
            'fields': ('icon_url',),
        }),
        ('Invite Code', {
            'fields': ('invite_code', 'invite_code_expires_at'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['invite_code', 'invite_code_expires_at', 'created_at', 'updated_at']
    autocomplete_fields = ['owner']
    
    inlines = [WorkspaceMembershipInline, ChannelInline, WorkspaceInviteInline]
    
    def member_count_display(self, obj):
        """Display member count."""
        count = obj.get_member_count()
        return format_html(
            '<span style="font-weight: bold;">{}</span> members',
            count
        )
    member_count_display.short_description = 'Members'
    
    def save_model(self, request, obj, form, change):
        """Auto-generate slug on creation."""
        if not change:
            from django.utils.text import slugify
            base_slug = slugify(obj.name)
            slug = base_slug
            counter = 1
            while Workspace.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            obj.slug = slug
        super().save_model(request, obj, form, change)


# ============== Workspace Membership Admin ==============

@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    """Admin configuration for WorkspaceMembership model."""
    
    list_display = [
        'user', 'workspace', 'role', 'is_active', 'joined_at', 'invited_by'
    ]
    list_filter = ['role', 'is_active', 'joined_at']
    search_fields = [
        'user__email', 'user__username',
        'workspace__name', 'workspace__slug'
    ]
    ordering = ['-joined_at']
    date_hierarchy = 'joined_at'
    
    fieldsets = (
        ('Membership', {
            'fields': ('workspace', 'user', 'role', 'is_active')
        }),
        ('Invite Info', {
            'fields': ('invited_by', 'invited_at'),
        }),
        ('Settings', {
            'fields': ('notify_mentions', 'notify_all_messages'),
        }),
        ('Timestamps', {
            'fields': ('joined_at', 'created_at', 'updated_at'),
        }),
    )
    
    readonly_fields = ['joined_at', 'created_at', 'updated_at']
    autocomplete_fields = ['workspace', 'user', 'invited_by']
    list_select_related = ['workspace', 'user', 'invited_by']


# ============== Workspace Invite Admin ==============

@admin.register(WorkspaceInvite)
class WorkspaceInviteAdmin(admin.ModelAdmin):
    """Admin configuration for WorkspaceInvite model."""
    
    list_display = [
        'email', 'workspace', 'status', 'invited_by', 'created_at', 'is_expired_display'
    ]
    list_filter = ['status', 'created_at']
    search_fields = [
        'email', 'workspace__name', 'workspace__slug',
        'invited_by__email', 'invited_by__username'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Invitation', {
            'fields': ('workspace', 'email', 'invited_by', 'status')
        }),
        ('Token', {
            'fields': ('token',),
            'classes': ('collapse',),
        }),
        ('Dates', {
            'fields': ('created_at', 'expires_at', 'accepted_at'),
        }),
    )
    
    readonly_fields = ['token', 'created_at', 'expires_at', 'accepted_at']
    autocomplete_fields = ['workspace', 'invited_by']
    
    def is_expired_display(self, obj):
        """Display if invite is expired."""
        if obj.status != 'pending':
            return format_html('<span style="color: gray;">-</span>')
        if obj.is_expired():
            return format_html('<span style="color: red;">Expired</span>')
        return format_html('<span style="color: green;">Valid</span>')
    is_expired_display.short_description = 'Validity'


# ============== Channel Admin ==============

class ChannelMembershipInline(admin.TabularInline):
    """Inline admin for channel memberships."""
    model = ChannelMembership
    extra = 0
    fields = ['user', 'joined_at', 'muted']
    readonly_fields = ['joined_at']
    autocomplete_fields = ['user']


class MessageInline(admin.TabularInline):
    """Inline admin for messages."""
    model = Message
    extra = 0
    fields = ['sender', 'content_preview', 'created_at', 'is_deleted']
    readonly_fields = ['content_preview', 'created_at']
    autocomplete_fields = ['sender']
    max_num = 10
    
    def content_preview(self, obj):
        """Show message preview."""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    """Admin configuration for Channel model."""
    
    list_display = [
        'display_name', 'workspace', 'channel_type', 'created_by',
        'member_count_display', 'is_default', 'is_archived', 'created_at'
    ]
    list_filter = ['channel_type', 'is_default', 'is_archived', 'created_at']
    search_fields = [
        'name', 'topic', 'description',
        'workspace__name', 'created_by__email'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('workspace', 'name', 'normalized_name', 'created_by')
        }),
        ('Type & Status', {
            'fields': ('channel_type', 'is_default', 'is_archived', 'archived_at'),
        }),
        ('Details', {
            'fields': ('topic', 'description'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['normalized_name', 'archived_at', 'created_at', 'updated_at']
    autocomplete_fields = ['workspace', 'created_by']
    list_select_related = ['workspace', 'created_by']
    
    inlines = [ChannelMembershipInline]
    
    def member_count_display(self, obj):
        """Display member count."""
        count = obj.get_member_count()
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            count
        )
    member_count_display.short_description = 'Members'


@admin.register(ChannelMembership)
class ChannelMembershipAdmin(admin.ModelAdmin):
    """Admin configuration for ChannelMembership model."""
    
    list_display = [
        'user', 'channel', 'joined_at', 'muted', 'notify_all_messages'
    ]
    list_filter = ['muted', 'notify_all_messages', 'joined_at']
    search_fields = [
        'user__email', 'user__username',
        'channel__name', 'channel__workspace__name'
    ]
    ordering = ['-joined_at']
    
    fieldsets = (
        ('Membership', {
            'fields': ('channel', 'user', 'is_active')
        }),
        ('Settings', {
            'fields': ('muted', 'notify_all_messages', 'last_read_at'),
        }),
        ('Timestamps', {
            'fields': ('joined_at', 'created_at', 'updated_at'),
        }),
    )
    
    readonly_fields = ['joined_at', 'last_read_at', 'created_at', 'updated_at']
    autocomplete_fields = ['channel', 'user', 'invited_by']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin configuration for Message model."""
    
    list_display = [
        'content_preview', 'channel', 'sender', 'created_at',
        'is_edited', 'is_deleted', 'is_thread_reply'
    ]
    list_filter = ['is_edited', 'is_deleted', 'is_thread_reply', 'created_at']
    search_fields = [
        'content', 'sender__email', 'sender__username',
        'channel__name'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Message', {
            'fields': ('channel', 'sender', 'content')
        }),
        ('Thread', {
            'fields': ('parent_message', 'is_thread_reply'),
        }),
        ('Status', {
            'fields': ('is_edited', 'edited_at', 'is_deleted', 'deleted_at'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    
    readonly_fields = ['edited_at', 'deleted_at', 'created_at', 'updated_at']
    autocomplete_fields = ['channel', 'sender', 'parent_message']
    
    def content_preview(self, obj):
        """Show message preview."""
        if obj.is_deleted:
            return format_html('<span style="color: red;">[deleted]</span>')
        preview = obj.content[:60] + '...' if len(obj.content) > 60 else obj.content
        return preview
    content_preview.short_description = 'Content'

"""
Django Signals for Domain Models
Ensures proper setup when models are created outside the service layer.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify

from domain.models.workspace import Workspace, WorkspaceMembership, WorkspaceRole
from domain.models.channel import Channel, ChannelType, ChannelMembership


@receiver(post_save, sender=Workspace)
def create_workspace_defaults(sender, instance, created, **kwargs):
    """
    When a workspace is created (even through admin), automatically:
    1. Add the owner as a workspace member
    2. Create the default #general channel
    3. Add the owner to #general channel
    """
    if created:
        # Add owner as workspace member if not already
        membership, _ = WorkspaceMembership.objects.get_or_create(
            workspace=instance,
            user=instance.owner,
            defaults={
                'role': WorkspaceRole.OWNER,
                'is_active': True
            }
        )
        
        # Create default #general channel if it doesn't exist
        general_channel, channel_created = Channel.objects.get_or_create(
            workspace=instance,
            is_default=True,
            defaults={
                'name': 'general',
                'normalized_name': 'general',
                'created_by': instance.owner,
                'channel_type': ChannelType.PUBLIC,
                'topic': 'General discussion for the workspace',
                'description': 'This is the default channel for workspace-wide announcements and discussions.',
            }
        )
        
        # Add owner to general channel
        if channel_created:
            ChannelMembership.objects.get_or_create(
                channel=general_channel,
                user=instance.owner,
                defaults={'is_active': True}
            )


@receiver(post_save, sender=WorkspaceMembership)
def add_to_general_channel(sender, instance, created, **kwargs):
    """
    When a user joins a workspace, automatically add them to #general channel.
    """
    if created and instance.is_active:
        # Find the general channel
        try:
            general_channel = Channel.objects.get(
                workspace=instance.workspace,
                is_default=True
            )
            # Add user to general channel
            ChannelMembership.objects.get_or_create(
                channel=general_channel,
                user=instance.user,
                defaults={'is_active': True}
            )
        except Channel.DoesNotExist:
            # General channel doesn't exist, it will be created by workspace signal
            pass

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
    
    Note: The default #general channel is created by the service layer
    (WorkspaceService.create_workspace) to avoid duplicate creation when
    using the API. This signal only handles the workspace membership.
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

"""
Management command to generate massive amounts of data for testing search.
Creates millions of messages for performance testing.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.conf import settings
import random
from datetime import timedelta
import time

from domain.models.user import User
from domain.models.workspace import Workspace, WorkspaceMembership, WorkspaceRole
from domain.models.channel import Channel, ChannelMembership, ChannelType, Message
from domain.models.direct_message import (
    DirectMessageConversation,
    DirectMessageParticipant,
    DirectMessage
)


class Command(BaseCommand):
    """
    Generate massive amounts of data for testing search performance.
    Usage: python manage.py generate_massive_data --messages 1000000
    """
    help = 'Generate millions of messages for testing search performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--messages',
            type=int,
            default=100000,
            help='Total number of messages to create (default: 100000)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10000,
            help='Batch size for bulk inserts (default: 10000)',
        )
        parser.add_argument(
            '--workspace-id',
            type=int,
            default=None,
            help='Target specific workspace ID (default: first workspace)',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing test messages before generating new ones',
        )

    def handle(self, *args, **options):
        total_messages = options['messages']
        batch_size = options['batch_size']
        workspace_id = options['workspace_id']
        reset = options['reset']
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Massive Data Generator for Search Performance Testing'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Target messages: {total_messages:,}')
        self.stdout.write(f'Batch size: {batch_size:,}')
        
        # Get workspace
        if workspace_id:
            try:
                workspace = Workspace.objects.get(id=workspace_id)
            except Workspace.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Workspace {workspace_id} not found'))
                return
        else:
            workspace = Workspace.objects.first()
            if not workspace:
                self.stdout.write(self.style.ERROR('No workspaces found. Create one first.'))
                return
        
        self.stdout.write(f'Target workspace: {workspace.name} (ID: {workspace.id})')
        
        # Get or create channels
        channels = list(Channel.objects.filter(workspace=workspace))
        if not channels:
            self.stdout.write(self.style.WARNING('No channels found. Creating default channels...'))
            channels = self._create_default_channels(workspace)
        
        self.stdout.write(f'Found {len(channels)} channels')
        
        # Get workspace members
        members = list(
            WorkspaceMembership.objects.filter(
                workspace=workspace,
                is_active=True
            ).values_list('user_id', flat=True)
        )
        
        if not members:
            self.stdout.write(self.style.ERROR('No workspace members found.'))
            return
        
        self.stdout.write(f'Found {len(members)} workspace members')
        
        # Reset if requested
        if reset:
            self._reset_messages(workspace)
        
        # Generate messages
        start_time = time.time()
        
        self.stdout.write('\nGenerating messages...')
        self._generate_messages(
            workspace=workspace,
            channels=channels,
            member_ids=members,
            total_count=total_messages,
            batch_size=batch_size
        )
        
        elapsed = time.time() - start_time
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Data Generation Complete!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Time elapsed: {elapsed:.2f} seconds')
        self.stdout.write(f'Messages generated: {total_messages:,}')
        self.stdout.write(f'Rate: {total_messages / elapsed:,.0f} messages/second')
        
        # Print summary
        self._print_summary(workspace)

    def _create_default_channels(self, workspace):
        """Create default channels if none exist."""
        channels = []
        channel_names = ['general', 'random', 'announcements', 'engineering', 'design']
        
        for name in channel_names:
            channel, created = Channel.objects.get_or_create(
                workspace=workspace,
                normalized_name=name,
                defaults={
                    'name': name,
                    'channel_type': ChannelType.PUBLIC,
                    'topic': f'{name.title()} discussions',
                    'description': f'Discussions about {name}',
                    'created_by': workspace.owner
                }
            )
            if created:
                # Add all workspace members
                members = WorkspaceMembership.objects.filter(
                    workspace=workspace, is_active=True
                ).values_list('user', flat=True)
                for user_id in members:
                    ChannelMembership.objects.create(
                        channel=channel,
                        user_id=user_id,
                        is_active=True
                    )
            channels.append(channel)
        
        return channels

    def _reset_messages(self, workspace):
        """Delete existing test messages."""
        self.stdout.write('Resetting existing messages...')
        
        # Get channel IDs for this workspace
        channel_ids = Channel.objects.filter(
            workspace=workspace
        ).values_list('id', flat=True)
        
        # Delete messages in batches to avoid memory issues
        deleted = 0
        while True:
            batch = list(Message.objects.filter(
                channel_id__in=channel_ids
            )[:10000].values_list('id', flat=True))
            
            if not batch:
                break
            
            Message.objects.filter(id__in=batch).delete()
            deleted += len(batch)
            self.stdout.write(f'  Deleted {deleted:,} messages...', ending='\r')
        
        self.stdout.write(f'  Deleted {deleted:,} messages total')

    def _generate_messages(self, workspace, channels, member_ids, total_count, batch_size):
        """Generate messages in batches."""
        sample_messages = [
            "Hey team, just wanted to share an update on the project status.",
            "Can someone help me with the API integration? Having some issues.",
            "Great work everyone on the sprint! We hit all our targets.",
            "Reminder: Team sync at 3pm today in the main conference room.",
            "I've reviewed the latest PRs. Looks good, just a few minor comments.",
            "The deployment went smoothly. No issues reported from production.",
            "New feature request came in from the client. Let's discuss tomorrow.",
            "Server performance improved by 40% after the latest optimization.",
            "Quick question: Anyone know the best way to handle rate limiting?",
            "Just pushed the hotfix. Should be live in a few minutes.",
            "The design mockups are ready for review. Check the Figma link.",
            "Meeting notes from today's standup are in the shared doc.",
            "We need to prioritize the bug fixes before the release.",
            "Customer feedback on the new feature has been very positive!",
            "Taking PTO next week. Will be back on the 15th.",
        ]
        
        hashtags = ['#urgent', '#update', '#question', '#info', '#release', '#bug']
        emojis = ['🎉', '👍', '🚀', '💡', '📝', '✅', '🔧', '⚡']
        
        total_created = 0
        batch = []
        
        for i in range(total_count):
            # Pick random channel and sender
            channel = random.choice(channels)
            sender_id = random.choice(member_ids)
            
            # Generate message content
            base_msg = random.choice(sample_messages)
            
            # Add some variety
            if random.random() < 0.3:
                base_msg += f" {random.choice(hashtags)}"
            if random.random() < 0.2:
                base_msg += f" {random.choice(emojis)}"
            
            # Randomly add more content
            if random.random() < 0.1:
                base_msg += " " + " ".join(random.choices(sample_messages, k=random.randint(1, 3)))
            
            # Create message object (not saved yet)
            msg = Message(
                channel_id=channel.id,
                sender_id=sender_id,
                content=base_msg,
                is_thread_reply=False,
                is_edited=random.random() < 0.05,
                is_deleted=False,
                created_at=timezone.now() - timedelta(
                    days=random.randint(0, 365),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
            )
            batch.append(msg)
            
            # Bulk create when batch is full
            if len(batch) >= batch_size:
                Message.objects.bulk_create(batch, ignore_conflicts=True)
                total_created += len(batch)
                batch = []
                
                # Progress update
                if total_created % 50000 == 0:
                    self.stdout.write(f'  Created {total_created:,} messages...')
        
        # Create remaining messages
        if batch:
            Message.objects.bulk_create(batch, ignore_conflicts=True)
            total_created += len(batch)
        
        self.stdout.write(f'  Created {total_created:,} messages total')

    def _print_summary(self, workspace):
        """Print summary of data."""
        self.stdout.write('')
        self.stdout.write('Current database state:')
        self.stdout.write(f'  Workspaces:         {Workspace.objects.count()}')
        self.stdout.write(f'  Users:              {User.objects.count()}')
        self.stdout.write(f'  Channels:           {Channel.objects.filter(workspace=workspace).count()}')
        self.stdout.write(f'  Messages:           {Message.objects.filter(channel__workspace=workspace).count()}')
        self.stdout.write(f'  DM Conversations:   {DirectMessageConversation.objects.filter(workspace=workspace).count()}')
        
        # Channel breakdown
        self.stdout.write('')
        self.stdout.write('Messages per channel:')
        for channel in Channel.objects.filter(workspace=workspace):
            count = Message.objects.filter(channel=channel).count()
            self.stdout.write(f'  #{channel.name}: {count:,}')

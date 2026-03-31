"""
Management command to create comprehensive mock data for testing.
Creates 10+ records for all major entities.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
import random
from datetime import timedelta

from domain.models.user import User, UserType
from domain.models.workspace import Workspace, WorkspaceMembership, WorkspaceRole
from domain.models.channel import Channel, ChannelMembership, ChannelType, Message
from domain.models.direct_message import (
    DirectMessageConversation,
    DirectMessageParticipant,
    DirectMessage
)
from repository.user_repository import UserRepository


class Command(BaseCommand):
    """Create comprehensive mock data for all entities."""
    help = 'Create mock data for testing (10+ records for all entities)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing mock data before creating new data',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Creating Mock Data for Slack Clone'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        if options['reset']:
            self._reset_data()

        # Create entities in order (respecting foreign keys)
        self._create_users()
        # Get ALL users from database (not just newly created)
        all_users = list(User.objects.filter(is_active=True))
        workspaces = self._create_workspaces(all_users)
        self._create_workspace_memberships(all_users, workspaces)
        channels = self._create_channels(workspaces, all_users)
        self._create_channel_memberships(all_users, channels)
        self._create_messages(all_users, channels)
        self._create_dm_conversations(all_users, workspaces)
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Mock Data Created Successfully!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self._print_summary()

    def _reset_data(self):
        """Delete all existing data (except admin users)."""
        self.stdout.write('Resetting existing data...')
        # Delete in reverse dependency order
        DirectMessage.objects.all().delete()
        DirectMessageParticipant.objects.all().delete()
        DirectMessageConversation.objects.all().delete()
        Message.objects.all().delete()
        ChannelMembership.objects.all().delete()
        Channel.objects.all().delete()
        WorkspaceMembership.objects.all().delete()
        Workspace.objects.all().delete()
        # Keep admin users but delete other mock users
        User.objects.filter(email__startswith='mock').delete()
        User.objects.filter(email__startswith='user').filter(
            email__regex=r'user\d+@'
        ).delete()
        self.stdout.write(self.style.WARNING('  Existing mock data cleared'))

    def _create_users(self):
        """Create 15 mock users (10+ required)."""
        self.stdout.write('\n👥 Creating Users...')
        
        users = []
        
        # Create 3 admin users
        for i in range(1, 4):
            email = f'admin{i}@slackclone.com'
            if not User.objects.filter(email=email).exists():
                user = UserRepository.create_admin(
                    email=email,
                    username=f'admin{i}',
                    password='Admin@123!',
                    first_name='Admin',
                    last_name=f'User{i}',
                    display_name=f'Admin {i}',
                    status='System administrator'
                )
                users.append(user)
        
        # Create 3 super users
        for i in range(1, 4):
            email = f'superuser{i}@slackclone.com'
            if not User.objects.filter(email=email).exists():
                user = UserRepository.create_super_user(
                    email=email,
                    username=f'superuser{i}',
                    password='SuperUser@123!',
                    first_name='Super',
                    last_name=f'User{i}',
                    display_name=f'Super User {i}',
                    status='Workspace manager'
                )
                users.append(user)
        
        # Create 9 regular users (total 15 users)
        first_names = ['Alice', 'Bob', 'Carol', 'David', 'Emma', 'Frank', 'Grace', 'Henry', 'Ivy', 'Jack']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
        
        for i in range(1, 10):
            email = f'user{i}@slackclone.com'
            if not User.objects.filter(email=email).exists():
                user = UserRepository.create_user(
                    email=email,
                    username=f'user{i}',
                    password='User@123!',
                    first_name=first_names[i-1],
                    last_name=last_names[i-1],
                    display_name=f'{first_names[i-1]} {last_names[i-1]}',
                    status=random.choice(['Working hard!', 'On vacation', 'Available', 'Busy', 'In a meeting'])
                )
                users.append(user)
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {len(users)} users'))
        return users

    def _create_workspaces(self, users):
        """Create 10 mock workspaces."""
        self.stdout.write('\n🏢 Creating Workspaces...')
        
        workspace_names = [
            'Acme Corp', 'TechStart Inc', 'Design Studio', 'Marketing Hub',
            'Engineering Team', 'Product Launch', 'Sales Force', 'Support Central',
            'Creative Agency', 'Research Lab', 'DevOps Squad', 'Finance Dept'
        ]
        
        workspaces = []
        # Get owners from users list (admins and super users)
        owners = [u for u in users if u.user_type in ['admin', 'super_user']]
        
        for i, name in enumerate(workspace_names[:10]):
            slug = slugify(name) + f'-{i}'
            if not Workspace.objects.filter(slug=slug).exists():
                workspace = Workspace.objects.create(
                    name=name,
                    slug=slug,
                    description=f'This is the {name} workspace for collaboration and communication.',
                    owner=random.choice(owners),
                    is_public=random.choice([True, False]),
                    allow_guests=True,
                    invite_code=f'MOCK{str(i).zfill(4)}',
                    is_active=True
                )
                workspaces.append(workspace)
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {len(workspaces)} workspaces'))
        return workspaces

    def _create_workspace_memberships(self, users, workspaces):
        """Create workspace memberships (users in workspaces)."""
        self.stdout.write('\n👥 Creating Workspace Memberships...')
        
        count = 0
        for workspace in workspaces:
            # Add owner
            if not WorkspaceMembership.objects.filter(workspace=workspace, user=workspace.owner).exists():
                WorkspaceMembership.objects.create(
                    workspace=workspace,
                    user=workspace.owner,
                    role=WorkspaceRole.OWNER,
                    is_active=True
                )
                count += 1
            
            # Add some random members
            other_users = [u for u in users if u != workspace.owner]
            members = random.sample(other_users, min(random.randint(5, 10), len(other_users)))
            
            for user in members:
                if not WorkspaceMembership.objects.filter(workspace=workspace, user=user).exists():
                    role = random.choice([WorkspaceRole.ADMIN, WorkspaceRole.MEMBER, WorkspaceRole.MEMBER])
                    WorkspaceMembership.objects.create(
                        workspace=workspace,
                        user=user,
                        role=role,
                        is_active=True
                    )
                    count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {count} workspace memberships'))

    def _create_channels(self, workspaces, users):
        """Create 10+ channels across workspaces."""
        self.stdout.write('\n📢 Creating Channels...')
        
        channel_templates = [
            ('general', 'General discussion', 'All team discussions'),
            ('random', 'Random chatter', 'Off-topic conversations'),
            ('announcements', 'Announcements', 'Important updates'),
            ('engineering', 'Engineering', 'Technical discussions'),
            ('design', 'Design', 'UI/UX and design'),
            ('marketing', 'Marketing', 'Marketing strategies'),
            ('sales', 'Sales', 'Sales team coordination'),
            ('support', 'Support', 'Customer support'),
            ('product', 'Product', 'Product planning'),
            ('devops', 'DevOps', 'Infrastructure and CI/CD'),
            ('qa', 'QA Testing', 'Quality assurance'),
            ('hr', 'HR & Culture', 'Human resources'),
        ]
        
        channels = []
        for workspace in workspaces:
            # Create #general as default
            if not Channel.objects.filter(workspace=workspace, name='general').exists():
                channel = Channel.objects.create(
                    workspace=workspace,
                    name='general',
                    normalized_name='general',
                    channel_type=ChannelType.PUBLIC,
                    topic='General workspace discussion',
                    description='All team members are in this channel',
                    is_default=True,
                    created_by=workspace.owner
                )
                channels.append(channel)
            
            # Create other channels
            for name, topic, desc in channel_templates[1:]:
                if not Channel.objects.filter(workspace=workspace, name=name).exists():
                    channel = Channel.objects.create(
                        workspace=workspace,
                        name=name,
                        normalized_name=name,
                        channel_type=random.choice([ChannelType.PUBLIC, ChannelType.PUBLIC, ChannelType.PRIVATE]),
                        topic=topic,
                        description=desc,
                        is_default=False,
                        created_by=workspace.owner
                    )
                    channels.append(channel)
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {len(channels)} channels'))
        return channels

    def _create_channel_memberships(self, users, channels):
        """Create channel memberships."""
        self.stdout.write('\n👥 Creating Channel Memberships...')
        
        count = 0
        for channel in channels:
            workspace_members = list(WorkspaceMembership.objects.filter(
                workspace=channel.workspace,
                is_active=True
            ).values_list('user', flat=True))
            
            # Add some members to each channel
            members = random.sample(workspace_members, min(random.randint(3, 8), len(workspace_members)))
            
            for user_id in members:
                user = User.objects.get(id=user_id)
                if not ChannelMembership.objects.filter(channel=channel, user=user).exists():
                    ChannelMembership.objects.create(
                        channel=channel,
                        user=user,
                        is_active=True,
                        notify_all_messages=random.choice([True, False]),
                        muted=False
                    )
                    count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {count} channel memberships'))

    def _create_messages(self, users, channels):
        """Create 10+ messages per channel."""
        self.stdout.write('\n💬 Creating Messages...')
        
        sample_messages = [
            "Hey team! How's everyone doing today?",
            "Just pushed the latest changes. Let me know if you see any issues.",
            "Quick reminder: team sync at 3pm today.",
            "Has anyone looked at the new design mockups?",
            "The deployment went smoothly. No issues reported.",
            "Can someone help me with the API integration?",
            "Great work on the last sprint everyone! 🎉",
            "Don't forget to update the documentation.",
            "I've reviewed the PRs. Looks good!",
            "We hit our target metrics this quarter.",
            "New feature request came in. Let's discuss.",
            "Taking a quick break. Back in 15 mins.",
            "The client approved the changes. Yay!",
            "Any volunteers for the hackathon next week?",
            "Server performance has improved by 40%.",
        ]
        
        count = 0
        for channel in channels:
            # Get members of this channel
            members = list(ChannelMembership.objects.filter(
                channel=channel,
                is_active=True
            ).values_list('user', flat=True))
            
            if not members:
                continue
            
            # Create 10-15 messages per channel
            num_messages = random.randint(10, 15)
            for i in range(num_messages):
                user = User.objects.get(id=random.choice(members))
                content = random.choice(sample_messages)
                
                # Add some variety
                if random.random() < 0.2:
                    content += f" #{random.choice(['urgent', 'update', 'question', 'info'])}"
                
                Message.objects.create(
                    channel=channel,
                    sender=user,
                    content=content,
                    is_thread_reply=False,
                    is_edited=random.random() < 0.1,
                    is_deleted=False
                )
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {count} messages'))

    def _create_dm_conversations(self, users, workspaces):
        """Create 10+ DM conversations and messages."""
        self.stdout.write('\n📬 Creating DM Conversations...')
        
        dm_count = 0
        msg_count = 0
        
        sample_dm_messages = [
            "Hey, can you take a look at this?",
            "Quick question about the deadline",
            "Thanks for the help earlier!",
            "Did you see the latest update?",
            "Lunch at 12:30?",
            "I'll send you the docs shortly",
            "Meeting got rescheduled to tomorrow",
            "Great job on the presentation!",
            "Let me know when you're free to chat",
            "The files are in the shared drive",
        ]
        
        for workspace in workspaces:
            # Get workspace members
            members = list(WorkspaceMembership.objects.filter(
                workspace=workspace,
                is_active=True
            ).values_list('user', flat=True))
            
            if len(members) < 2:
                continue
            
            # Create 10-15 DM conversations per workspace
            num_dms = random.randint(10, 15)
            for _ in range(num_dms):
                # Pick 2-4 participants
                num_participants = random.randint(2, min(4, len(members)))
                participants = random.sample(members, num_participants)
                
                # Check if this DM already exists (same participants)
                existing = DirectMessageConversation.objects.filter(
                    workspace=workspace,
                    is_group=(num_participants > 2)
                )
                # Simple check - skip if too many DMs already
                if existing.count() > 20:
                    continue
                
                creator = User.objects.get(id=participants[0])
                
                dm = DirectMessageConversation.objects.create(
                    workspace=workspace,
                    is_group=(num_participants > 2),
                    name=f'Group DM {dm_count}' if num_participants > 2 else '',
                    created_by=creator,
                    is_active=True,
                    last_message_at=timezone.now() - timedelta(hours=random.randint(1, 48))
                )
                
                # Add participants
                for user_id in participants:
                    user = User.objects.get(id=user_id)
                    DirectMessageParticipant.objects.create(
                        conversation=dm,
                        user=user,
                        is_active=True,
                        added_by=creator
                    )
                
                dm_count += 1
                
                # Create 5-15 messages per DM
                num_msgs = random.randint(5, 15)
                for i in range(num_msgs):
                    sender = User.objects.get(id=random.choice(participants))
                    content = random.choice(sample_dm_messages)
                    
                    DirectMessage.objects.create(
                        conversation=dm,
                        sender=sender,
                        content=content,
                        is_thread_reply=False,
                        is_edited=random.random() < 0.1,
                        is_deleted=False
                    )
                    msg_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {dm_count} DM conversations with {msg_count} messages'))

    def _print_summary(self):
        """Print summary of created data."""
        self.stdout.write('')
        self.stdout.write('Summary:')
        self.stdout.write(f'  Users:                    {User.objects.count()}')
        self.stdout.write(f'  Workspaces:               {Workspace.objects.count()}')
        self.stdout.write(f'  Workspace Memberships:    {WorkspaceMembership.objects.count()}')
        self.stdout.write(f'  Channels:                 {Channel.objects.count()}')
        self.stdout.write(f'  Channel Memberships:      {ChannelMembership.objects.count()}')
        self.stdout.write(f'  Messages:                 {Message.objects.count()}')
        self.stdout.write(f'  DM Conversations:         {DirectMessageConversation.objects.count()}')
        self.stdout.write(f'  DM Participants:          {DirectMessageParticipant.objects.count()}')
        self.stdout.write(f'  Direct Messages:          {DirectMessage.objects.count()}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Credentials for testing:'))
        self.stdout.write('  Admin:       admin@slackclone.com / Admin@123!')
        self.stdout.write('  User:        user1@slackclone.com / User@123!')
        self.stdout.write('')
        self.stdout.write('You can run: python tests/test_websocket.py')

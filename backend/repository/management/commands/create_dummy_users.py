"""
Management command to create dummy users for each user type.
"""
from django.core.management.base import BaseCommand
from domain.models.user import UserType
from repository.user_repository import UserRepository


class Command(BaseCommand):
    """Create dummy users for testing each user type."""
    help = 'Create dummy users for Admin, Super User, and User types'

    def handle(self, *args, **options):
        self.stdout.write('Creating dummy users...')
        
        # Admin user
        if not UserRepository.email_exists('admin@slackclone.com'):
            admin = UserRepository.create_admin(
                email='admin@slackclone.com',
                username='admin',
                password='Admin@123!',
                first_name='System',
                last_name='Administrator',
                display_name='Admin',
                status='Managing the system'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created Admin: {admin.email} / password: Admin@123!')
            )
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists'))
        
        # Super User
        if not UserRepository.email_exists('superuser@slackclone.com'):
            superuser = UserRepository.create_super_user(
                email='superuser@slackclone.com',
                username='superuser',
                password='SuperUser@123!',
                first_name='Super',
                last_name='User',
                display_name='Super User',
                status='Managing workspaces'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created Super User: {superuser.email} / password: SuperUser@123!')
            )
        else:
            self.stdout.write(self.style.WARNING('Super User already exists'))
        
        # Regular User
        if not UserRepository.email_exists('user@slackclone.com'):
            user = UserRepository.create_user(
                email='user@slackclone.com',
                username='user',
                password='User@123!',
                first_name='John',
                last_name='Doe',
                display_name='John Doe',
                status='Working hard!'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created User: {user.email} / password: User@123!')
            )
        else:
            self.stdout.write(self.style.WARNING('User already exists'))
        
        self.stdout.write(self.style.SUCCESS('\nDummy users created successfully!'))
        self.stdout.write('\nLogin credentials:')
        self.stdout.write('  Admin:       admin@slackclone.com / Admin@123!')
        self.stdout.write('  Super User:  superuser@slackclone.com / SuperUser@123!')
        self.stdout.write('  User:        user@slackclone.com / User@123!')

# Generated migration for User model

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('user_type', models.CharField(choices=[('admin', 'Admin'), ('super_user', 'Super User'), ('user', 'User')], default='user', help_text='Type of user determining their permissions level', max_length=20)),
                ('email', models.EmailField(help_text='Unique email address used for login', max_length=254, unique=True, verbose_name='email address')),
                ('username', models.CharField(help_text='Unique username for display', max_length=150, unique=True)),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('display_name', models.CharField(blank=True, help_text='Display name shown in the application', max_length=100)),
                ('avatar_url', models.URLField(blank=True, help_text='URL to user avatar image', null=True)),
                ('status', models.CharField(blank=True, help_text='User status message', max_length=100)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this user account is active', verbose_name='active')),
                ('is_staff', models.BooleanField(default=False, help_text='Whether user can log into admin site', verbose_name='staff status')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('last_active', models.DateTimeField(blank=True, null=True, verbose_name='last active')),
                ('email_verified', models.BooleanField(default=False)),
                ('email_verified_at', models.DateTimeField(blank=True, null=True)),
                ('timezone', models.CharField(default='UTC', help_text='User preferred timezone', max_length=50)),
                ('language', models.CharField(default='en', help_text='User preferred language', max_length=10)),
                ('email_notifications', models.BooleanField(default=True)),
                ('push_notifications', models.BooleanField(default=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'db_table': 'users',
                'ordering': ['-date_joined'],
            },
        ),
    ]

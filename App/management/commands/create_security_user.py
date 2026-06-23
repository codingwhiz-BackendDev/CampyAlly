"""
Django management command to create a security user with default credentials

Usage:
    python manage.py create_security_user

This creates a security user with:
    - Username: security
    - Password: 0102
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a security user with default credentials (username: security, password: 0102)'

    def handle(self, *args, **kwargs):
        username = 'security'
        password = '0102'

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.WARNING(f'User "{username}" already exists. Password has been reset to "{password}"')
            )
        else:
            user = User.objects.create_user(username=username, password=password)
            self.stdout.write(
                self.style.SUCCESS(f'✅ Security user created successfully')
            )

        self.stdout.write(f'   Username: {username}')
        self.stdout.write(f'   Password: {password}')
        self.stdout.write(self.style.WARNING('⚠  Please change the password after first login for security'))

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from accounts.models import Role, Profile


class Command(BaseCommand):
    help = "Create or update a user by email and password, optionally set role and superuser flags."

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help='User email (unique)')
        parser.add_argument('--password', required=True, help='User password (unicode supported)')
        parser.add_argument('--role', choices=['admin', 'student', 'instructor'], default='student', help='Assign a role to the user')
        parser.add_argument('--superuser', action='store_true', help='Make the user a superuser/admin')
        parser.add_argument('--staff', action='store_true', help='Give staff permissions for admin site')

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        password = options['password']
        role_code = options['role']
        make_superuser = options['superuser']
        make_staff = options['staff'] or make_superuser

        User = get_user_model()

        # Derive username from email local part and ensure uniqueness
        base_username = email.split('@')[0]
        username = base_username
        suffix = 1
        while User.objects.filter(username=username).exclude(email=email).exists():
            suffix += 1
            username = f"{base_username}{suffix}"

        user, created = User.objects.get_or_create(email=email, defaults={
            'username': username,
        })

        # Set password (update even if user existed)
        user.set_password(password)

        # Assign role if available
        role_obj = Role.objects.filter(code=role_code).first()
        if role_obj:
            user.role = role_obj

        # Staff/superuser flags
        user.is_staff = make_staff
        user.is_superuser = make_superuser

        user.save()

        # Ensure profile exists
        Profile.objects.update_or_create(user=user)

        action = 'created' if created else 'updated'
        self.stdout.write(self.style.SUCCESS(
            f"User {action}: email={user.email}, username={user.username}, role={getattr(user.role, 'code', None)}, staff={user.is_staff}, superuser={user.is_superuser}"
        ))
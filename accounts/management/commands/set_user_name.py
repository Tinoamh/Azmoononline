from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Set a user's first and last name by email"

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help='User email')
        parser.add_argument('--first-name', help='First name')
        parser.add_argument('--last-name', help='Last name')
        parser.add_argument('--full-name', help='Full name (will be split into first and last)')

    def handle(self, *args, **options):
        User = get_user_model()
        email = options['email'].strip().lower()
        first_name = options.get('first_name')
        last_name = options.get('last_name')
        full_name = options.get('full_name')

        if full_name and (not first_name or not last_name):
            parts = full_name.strip().split()
            if parts:
                first_name = parts[0]
                last_name = " ".join(parts[1:]) if len(parts) > 1 else ''

        if first_name is None or last_name is None:
            raise CommandError('Please provide --first-name and --last-name, or --full-name')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f'User with email {email} does not exist')

        user.first_name = first_name
        user.last_name = last_name
        user.save(update_fields=['first_name', 'last_name'])

        self.stdout.write(self.style.SUCCESS(
            f"Updated name for {email} -> first_name='{user.first_name}', last_name='{user.last_name}'"
        ))


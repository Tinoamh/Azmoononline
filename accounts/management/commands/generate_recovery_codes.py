from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from accounts.models import RecoveryCode
import secrets
import string


class Command(BaseCommand):
    help = 'Generate single-use recovery codes for a user and print them.'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help='User email')
        parser.add_argument('--count', type=int, default=5, help='Number of codes to generate')

    def handle(self, *args, **options):
        User = get_user_model()
        email = options['email']
        count = options['count']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError('User with email %s does not exist' % email)

        alphabet = string.ascii_letters + string.digits
        codes = []
        for _ in range(count):
            code = ''.join(secrets.choice(alphabet) for _ in range(10))
            RecoveryCode.objects.create(user=user, code_hash=make_password(code))
            codes.append(code)

        self.stdout.write(self.style.SUCCESS('Generated %d recovery codes for %s:' % (count, email)))
        for c in codes:
            self.stdout.write(c)
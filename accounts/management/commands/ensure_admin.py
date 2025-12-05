from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Role


class Command(BaseCommand):
    help = "Ensure an admin user exists with the given email and password."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Admin user's email")
        parser.add_argument(
            "--password",
            required=True,
            help="Admin user's password (will be hashed, not stored in plaintext)",
        )

    def handle(self, *args, **options):
        email = options["email"].strip()
        password = options["password"]

        User = get_user_model()

        # Ensure the 'admin' role exists
        role, _ = Role.objects.get_or_create(
            code="admin",
            defaults={"name": "ادمین", "description": "Admin role"},
        )

        # Create or update the user by email
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                # Use email as username to avoid collisions
                "username": email,
                "is_superuser": True,
                "is_staff": True,
                "role": role,
            },
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Admin user created: {email}"))
            return

        # If user exists, ensure it has admin privileges and role
        updated_fields = []
        if not user.is_superuser:
            user.is_superuser = True
            updated_fields.append("is_superuser")
        if not user.is_staff:
            user.is_staff = True
            updated_fields.append("is_staff")
        if user.role_id != role.id:
            user.role = role
            updated_fields.append("role")

        # Update password as requested
        if password:
            user.set_password(password)
            updated_fields.append("password")

        user.save()
        if updated_fields:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Admin user updated: {email} (" + ", ".join(updated_fields) + ")"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"Admin user already up-to-date: {email}"))


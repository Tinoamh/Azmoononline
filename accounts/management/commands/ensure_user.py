from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Role


class Command(BaseCommand):
    help = "Ensure a user exists with given email, password, and role."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="User email")
        parser.add_argument("--password", required=True, help="User password")
        parser.add_argument(
            "--role",
            default="student",
            help="Role code (default: student). Options: student, instructor, admin",
        )

    def handle(self, *args, **options):
        email = options["email"].strip()
        password = options["password"]
        role_code = options["role"].strip()

        User = get_user_model()

        # Ensure role exists
        role_defaults = {
            "student": {"name": "دانشجو", "description": "Student role"},
            "instructor": {"name": "استاد", "description": "Instructor role"},
            "admin": {"name": "ادمین", "description": "Admin role"},
        }
        defaults = role_defaults.get(role_code, {"name": role_code, "description": role_code})
        role, _ = Role.objects.get_or_create(code=role_code, defaults=defaults)

        # Create or update user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "role": role,
            },
        )

        updated_fields = []
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"User created: {email} (role={role_code})"))
            return

        # Update role if changed
        if user.role_id != role.id:
            user.role = role
            updated_fields.append("role")

        # Update password
        if password:
            user.set_password(password)
            updated_fields.append("password")

        user.save()
        if updated_fields:
            self.stdout.write(
                self.style.SUCCESS(
                    f"User updated: {email} (" + ", ".join(updated_fields) + ")"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"User already up-to-date: {email}"))


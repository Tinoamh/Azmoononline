import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oes.settings")

try:
    import django
    django.setup()
except Exception as e:
    print("django_setup_error=", e)
    sys.exit(1)

from django.test import Client
from django.contrib.auth import get_user_model
from accounts.models import Role


def main():
    U = get_user_model()
    try:
        u = U.objects.get(email="mmmos@gmail.com")
    except U.DoesNotExist:
        print("user_not_found")
        return

    # Ensure role is student
    try:
        student_role = Role.objects.get(code="student")
        if u.role_id != student_role.id:
            u.role = student_role
            u.save()
            print("role_set_to_student")
    except Role.DoesNotExist:
        print("role_student_missing")

    c = Client()
    c.force_login(u)

    resp = c.get("/accounts/exams/")
    html = resp.content.decode("utf-8", errors="ignore")
    print("status=", resp.status_code)

    # Detect start buttons/links
    start_ids = re.findall(r"/accounts/exams/(\d+)/start/", html)
    print("start_ids=", start_ids)

    has_btn = ("btn-start" in html) or ("start" in html and "/accounts/exams/" in html)
    print("has_start_btn=", has_btn)

    # Count basic cards
    card_count = html.count('class="item"') + html.count("card")
    print("card_count=", card_count)

    # Show a small snippet for visual confirmation
    idx = html.find("/accounts/exams/")
    snippet = html[idx - 120 : idx + 120] if idx != -1 else html[:240]
    print("snippet=", snippet.replace("\n", " ")[:240])


if __name__ == "__main__":
    main()

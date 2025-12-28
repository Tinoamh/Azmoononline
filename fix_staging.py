import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oes.settings')
django.setup()

from accounts.models import Classroom

print("Starting cleanup...")
# List all classrooms
all_classes = list(Classroom.objects.all())
print(f"Found {len(all_classes)} classrooms.")

# Names of classes that user explicitly mentioned as 'real'
# Adjust these names based on exact strings if needed, or I'll just print them first to be safe.
# User said: "123" and "کلاس ریاضی"
REAL_CLASS_NAMES = ['123', 'کلاس ریاضی']

for c in all_classes:
    print(f"Checking ID={c.id} Name='{c.name}' Current Staging={c.is_staging}")
    
    if c.name in REAL_CLASS_NAMES:
        if c.is_staging:
            c.is_staging = False
            c.save()
            print(f" -> UPDATED: Set {c.name} to REAL (is_staging=False)")
        else:
            print(f" -> OK: {c.name} is already REAL")
    else:
        # Default assumption: If it's not one of the named ones, it's an exam-wrapper
        if not c.is_staging:
            c.is_staging = True
            c.save()
            print(f" -> UPDATED: Set {c.name} to STAGING/HIDDEN (is_staging=True)")
        else:
            print(f" -> OK: {c.name} is already HIDDEN")

print("Cleanup finished.")

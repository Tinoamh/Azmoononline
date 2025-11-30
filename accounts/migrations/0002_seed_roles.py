from django.db import migrations


def create_roles(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    defaults = [
        ('student', 'دانشجو'),
        ('instructor', 'استاد'),
        ('admin', 'ادمین'),
    ]
    for code, name in defaults:
        Role.objects.get_or_create(code=code, defaults={'name': name})


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_roles, migrations.RunPython.noop),
    ]
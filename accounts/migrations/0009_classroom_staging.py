from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_exam_source_assignment'),
    ]

    operations = [
        migrations.AddField(
            model_name='classroom',
            name='is_staging',
            field=models.BooleanField(default=False),
        ),
    ]


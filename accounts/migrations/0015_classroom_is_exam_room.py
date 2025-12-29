from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_exam_end_time_exam_start_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='classroom',
            name='is_exam_room',
            field=models.BooleanField(default=False),
        ),
    ]
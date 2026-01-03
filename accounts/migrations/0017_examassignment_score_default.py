from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0016_question_image_questionoptionimage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='examassignment',
            name='score',
            field=models.FloatField(default=0, null=True, blank=True),
        ),
    ]

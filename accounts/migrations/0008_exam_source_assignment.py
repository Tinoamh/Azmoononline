from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_question'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='source_exam',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='derived_exams', to='accounts.exam'),
        ),
        migrations.AddField(
            model_name='exam',
            name='shuffle_per_student',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='ExamAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('selected_question_ids', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('exam', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='accounts.exam')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exam_assignments', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='examassignment',
            unique_together={('exam', 'student')},
        ),
    ]


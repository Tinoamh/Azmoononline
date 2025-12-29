from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone


class Role(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "نقش"
        verbose_name_plural = "نقش‌ها"

    def __str__(self):
        return self.name


class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "پروفایل"
        verbose_name_plural = "پروفایل‌ها"

    def __str__(self):
        return f"پروفایل {self.user.username}"

class Classroom(models.Model):
    name = models.CharField(max_length=200)
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_classes')
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='classes', blank=True)
    is_staging = models.BooleanField(default=False)
    # Marks classrooms that are auto-created per exam definition and should
    # not appear in the general classes listing/selectors.
    is_exam_room = models.BooleanField(default=False)

    class Meta:
        verbose_name = "کلاس"
        verbose_name_plural = "کلاس‌ها"
        constraints = []

    def __str__(self):
        return f"{self.name} - {getattr(self.instructor, 'username', '')}"

class Exam(models.Model):
    name = models.CharField(max_length=200)
    classroom = models.ForeignKey('Classroom', on_delete=models.CASCADE, related_name='exams')
    num_questions = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_exams')
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='exams', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    source_exam = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='derived_exams')
    shuffle_per_student = models.BooleanField(default=True)
    duration = models.PositiveIntegerField(default=60, help_text="Duration in minutes")
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "آزمون"
        verbose_name_plural = "آزمون‌ها"

    def __str__(self):
        return f"آزمون {self.name} ({self.num_questions})"

class Question(models.Model):
    KIND_CHOICES = (
        ('des', 'تشریحی'),
        ('mcq', 'تستی'),
    )
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    kind = models.CharField(max_length=4, choices=KIND_CHOICES)
    text = models.TextField()
    # For descriptive
    answer_text = models.TextField(blank=True)
    # For MCQ
    options = models.JSONField(blank=True, null=True)
    correct_index = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "سوال"
        verbose_name_plural = "سوال‌ها"

    def __str__(self):
        return f"سوال {self.exam.name} - {self.kind}"
class ExamAssignment(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='assignments')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_assignments')
    selected_question_ids = models.JSONField()
    score = models.FloatField(null=True, blank=True)
    student_answers = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exam', 'student')
class RecoveryCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recovery_codes')
    code_hash = models.CharField(max_length=128)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "کد بازیابی"
        verbose_name_plural = "کدهای بازیابی"

    def __str__(self):
        status = 'استفاده‌شده' if self.used else 'فعال'
        return f"کد بازیابی {self.user.email} - {status}"

class PasswordResetAttempt(models.Model):
    email = models.EmailField()
    requested_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "تلاش بازنشانی رمز"
        verbose_name_plural = "تلاش‌های بازنشانی رمز"
        indexes = [
            models.Index(fields=["email", "requested_at"]),
        ]

    def __str__(self):
        return f"تلاش بازنشانی برای {self.email} در {self.requested_at}"

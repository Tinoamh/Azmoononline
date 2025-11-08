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

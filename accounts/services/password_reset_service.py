"""
سرویس امن «بازنشانی رمز عبور» با تولید رمز رندوم ۸ کاراکتری و ارسال ایمیل.

وابستگی‌ها:
- Django (ORM و ایمیل)
- python-decouple (اختیاری؛ اگر نصب نبود، از os.environ استفاده می‌شود)

تنظیمات محیطی (در فایل `.env`، بدون قرار دادن هیچ مقدار محرمانه در کد):
- SMTP_HOST
- SMTP_PORT
- SMTP_USER
- SMTP_PASS  (محرمانه؛ App Password یا گذرواژه SMTP)
- EMAIL_FROM (مثلاً "OES Support <samexamweb@gmail.com>")
- APP_NAME   (مثلاً "OES")

نمونهٔ تست محلی:
- اجرای مستقیم این فایل با تعیین `DJANGO_SETTINGS_MODULE` و فراخوانی تابع `request_password_reset(email)`.
"""

import os
import sys
import logging
import string
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.db import transaction

try:
    from decouple import config as env_config
except ImportError:  # fallback به os.environ اگر decouple نصب نباشد
    def env_config(key, default=None, cast=None):
        val = os.environ.get(key, default)
        if cast is int and val is not None:
            try:
                return int(val)
            except ValueError:
                return default
        if cast is bool and val is not None:
            return str(val).strip().lower() in {"1", "true", "yes", "on"}
        return val


logger = logging.getLogger(__name__)


def generate_random_password(length: int = 8) -> str:
    """رمز رندوم امن ۸ کاراکتری از حروف بزرگ/کوچک و ارقام تولید می‌کند."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _get_smtp_connection():
    """خواندن تنظیمات SMTP از env و ساخت کانکشن SMTP Django.

    هیچ‌گاه مقادیر محرمانه را لاگ یا چاپ نمی‌کنیم.
    """
    host = env_config("SMTP_HOST", default=None)
    port = env_config("SMTP_PORT", cast=int, default=None)
    user = env_config("SMTP_USER", default=None)
    password = env_config("SMTP_PASS", default=None)
    use_tls = env_config("SMTP_USE_TLS", cast=bool, default=True)
    from_addr = env_config("EMAIL_FROM", default=getattr(settings, "DEFAULT_FROM_EMAIL", None))

    if not all([host, port, user, password, from_addr]):
        # بدون افشای مقدار دقیق، فقط اعلام ناقص بودن پیکربندی
        raise RuntimeError("تنظیمات SMTP ناقص است. متغیرهای محیطی لازم را تنظیم کنید.")

    conn = get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=host,
        port=port,
        username=user,
        password=password,
        use_tls=use_tls,
        fail_silently=False,
    )
    return conn, from_addr


def _send_reset_email(to_email: str, new_password: str):
    """ارسال ایمیل حاوی رمز جدید به کاربر. هیچ‌گاه رمز را لاگ نمی‌کنیم."""
    app_name = env_config("APP_NAME", default="MyApp")
    connection, from_addr = _get_smtp_connection()

    subject = f"بازنشانی رمز عبور — {app_name}"
    body = (
        "سلام،\n"
        f"رمز عبور جدید حساب شما: {new_password}\n"
        "لطفاً پس از ورود، فوراً آن را به یک رمز دلخواه و امن‌تر تغییر دهید.\n"
        "اگر شما این درخواست را ارسال نکرده‌اید، لطفاً سریعاً با پشتیبانی تماس بگیرید.\n"
    )

    email = EmailMessage(subject, body, from_addr, [to_email], connection=connection)
    # در صورت خطا exception رخ می‌دهد و تراکنش (در صورت استفاده) برگشت می‌خورد
    email.send(fail_silently=False)


def invalidate_user_sessions(user):
    """نشست‌های فعال کاربر را بی‌اعتبار می‌کند تا لاگین‌های قدیمی از کار بیفتند."""
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    for s in sessions:
        data = s.get_decoded()
        if str(data.get("_auth_user_id")) == str(user.id):
            s.delete()


def _is_rate_limited(email: str, window_seconds: int = 300, max_requests: int = 3) -> bool:
    """بررسی ریت‌لیمیت: حداکثر ۳ درخواست در ۵ دقیقه برای هر ایمیل."""
    from accounts.models import PasswordResetAttempt  # import محلی برای جلوگیری از حلقه‌ی وابستگی

    now = timezone.now()
    window_start = now - timedelta(seconds=window_seconds)
    count = (
        PasswordResetAttempt.objects
        .filter(email__iexact=email.strip(), requested_at__gte=window_start)
        .count()
    )
    return count >= max_requests


def _record_attempt(email: str) -> None:
    from accounts.models import PasswordResetAttempt
    PasswordResetAttempt.objects.create(email=email.strip(), requested_at=timezone.now())


def request_password_reset(email: str) -> dict:
    """
    تولید رمز جدید رندوم ۸ کاراکتری، ست‌کردن امن برای کاربر، ارسال ایمیل اطلاع‌رسانی.

    خروجی عمومی و غیر افشاگر:
    { "success": bool, "message": str }
    """
    email = (email or "").strip()
    if not email:
        return {"success": False, "message": "ایمیل نامعتبر است."}

    # ریت‌لیمیت قبل از رکورد تلاش
    if _is_rate_limited(email):
        logger.info(f"Password reset rate-limited for {email}")
        return {"success": False, "message": "تعداد درخواست‌ها بیش از حد مجاز است. لطفاً بعداً تلاش کنید."}

    # ثبت تلاش برای این ایمیل (بدون افشا در پاسخ)
    _record_attempt(email)

    User = get_user_model()
    qs = User.objects.filter(email__iexact=email)

    if not qs.exists():
        # پاسخ عمومی و غیر افشاگر (همیشه یکسان)
        logger.info(f"Password reset requested for {email}")
        return {"success": True, "message": "اگر ایمیل در سیستم ثبت شده باشد، رمز جدید به ایمیل ارسال شد."}

    user = qs.first()
    new_password = generate_random_password(8)

    try:
        # با atomic تضمین می‌کنیم در صورت خطا، تغییر رمز اعمال نشود
        with transaction.atomic():
            user.set_password(new_password)
            user.save(update_fields=["password"])  # ذخیره هش رمز، نه plaintext

            # تلاش برای ارسال ایمیل؛ اگر خطا رخ دهد، تراکنش رول‌بک می‌شود
            _send_reset_email(to_email=user.email, new_password=new_password)

            # پس از موفقیت ارسال ایمیل، نشست‌های فعال را بی‌اعتبار می‌کنیم
            invalidate_user_sessions(user)

        logger.info(f"Password reset processed for {email}")
        return {"success": True, "message": "اگر ایمیل در سیستم ثبت شده باشد، رمز جدید به ایمیل ارسال شد."}

    except Exception as exc:
        # عدم افشای جزئیات حساس؛ فقط summary کوتاه
        logger.warning(f"Email send failed for {email}: {type(exc).__name__}")
        return {"success": False, "message": "ارسال ایمیل ناموفق بود. لطفاً بعداً تلاش کنید."}


if __name__ == "__main__":
    """
    اجرای محلی برای تست سریع:
    - پیش‌نیاز: ایجاد فایل `.env` با متغیرهای SMTP_* و تنظیم `DJANGO_SETTINGS_MODULE=oes.settings`.
    - اجرا: `py -3 accounts/services/password_reset_service.py user@example.com`
    """
    # اطمینان از راه‌اندازی محیط Django برای اجرای مستقل
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oes.settings")
    try:
        import django
        django.setup()
    except Exception as e:
        print("راه‌اندازی Django ناموفق بود:", type(e).__name__)
        sys.exit(1)

    target_email = None
    if len(sys.argv) > 1:
        target_email = sys.argv[1]
    else:
        target_email = input("ایمیل کاربر برای reset: ").strip()

    res = request_password_reset(target_email)
    # فقط نتیجهٔ کلی را چاپ می‌کنیم؛ هیچ دادهٔ حساس یا رمز چاپ نمی‌شود.
    print(res)
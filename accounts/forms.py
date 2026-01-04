from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import authenticate
from .models import User, Role, Profile
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
import string
import secrets
from django.contrib.auth.hashers import check_password
from .models import RecoveryCode


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True, label="نام")
    last_name = forms.CharField(max_length=150, required=True, label="نام خانوادگی")
    email = forms.EmailField(required=True, label="ایمیل")
    phone = forms.CharField(max_length=20, required=False, label="شماره تماس")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "email", "password1", "password2", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # فیلد نام کاربری را مخفی و غیرضروری می‌کنیم؛ در ذخیره از ایمیل تولید می‌شود
        if 'username' in self.fields:
            self.fields['username'].required = False
            self.fields['username'].widget = forms.HiddenInput()
        # راهنمای گذرواژه فقط هنگام فوکوس در قالب نمایش داده می‌شود
        self.fields['password1'].help_text = "حداقل ۸ کاراکتر؛ غیرقابل پیش‌بینی؛ ترکیب حروف و اعداد"
        self.fields['password2'].help_text = "تکرار گذرواژه برای تایید"
        # placeholderها برای تطابق با UI فیگما
        self.fields['first_name'].widget.attrs.update({
            'placeholder': 'نام', 'class': 'input'
        })
        self.fields['last_name'].widget.attrs.update({
            'placeholder': 'نام خانوادگی', 'class': 'input'
        })
        self.fields['email'].widget.attrs.update({
            'placeholder': 'ایمیل', 'class': 'input'
        })
        self.fields['phone'].widget.attrs.update({
            'placeholder': 'شماره تماس', 'class': 'input'
        })
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'گذرواژه', 'class': 'input'
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'تایید گذرواژه', 'class': 'input'
        })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get("first_name")
        user.last_name = self.cleaned_data.get("last_name")
        user.email = self.cleaned_data.get("email")
        # تولید نام‌کاربری از ایمیل اگر خالی باشد
        if not user.username:
            base = user.email.split('@')[0]
            suffix = 1
            candidate = base
            while User.objects.filter(username=candidate).exists():
                suffix += 1
                candidate = f"{base}{suffix}"
            user.username = candidate
        # نقش پیش‌فرض: دانشجو
        student_role = Role.objects.filter(code='student').first()
        if student_role:
            user.role = student_role
        if commit:
            user.save()
            Profile.objects.update_or_create(user=user, defaults={
                "phone": self.cleaned_data.get("phone", ""),
            })
        return user


class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField(label="ایمیل")
    password = forms.CharField(widget=forms.PasswordInput, label="گذرواژه")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'placeholder': 'ایمیل', 'class': 'input'
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': 'گذرواژه', 'class': 'input'
        })

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get('email')
        password = cleaned.get('password')
        if email and password:
            user = authenticate(email=email, password=password)
            if user is None:
                raise forms.ValidationError("ایمیل یا گذرواژه نادرست است.")
            cleaned['user'] = user
        return cleaned


class AzmonPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Style the email field similar to login page
        self.fields['email'].widget.attrs.update({
            'placeholder': 'ایمیل', 'class': 'input'
        })

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None, html_email_template_name=None,
             extra_email_context=None):
        """
        Generate a random 8-character alphanumeric password, set it for the user,
        and email it along with a standard reset link so the user can change it.
        """
        email = self.cleaned_data["email"]
        # Collect users associated with provided email per Django's behavior
        users = list(self.get_users(email))
        if not users:
            return

        current_site = get_current_site(request)
        for user in users:
            # Generate new temporary password
            alphabet = string.ascii_letters + string.digits
            new_password = ''.join(secrets.choice(alphabet) for _ in range(8))
            user.set_password(new_password)
            user.save()

            # Build context for email
            context = {
                'email': email,
                'domain': domain_override or current_site.domain,
                'site_name': current_site.name or 'سام آزمون',
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
                'generated_password': new_password,
            }
            if extra_email_context is not None:
                context.update(extra_email_context)

            # Send combined email (text or html if provided)
            self.send_mail(subject_template_name, email_template_name,
                           context, from_email, email,
                           html_email_template_name=html_email_template_name)


class RecoveryCodeResetForm(SetPasswordForm):
    email = forms.EmailField(label="ایمیل")
    recovery_code = forms.CharField(label="کد بازیابی", max_length=64)

    def __init__(self, *args, **kwargs):
        self.user_cache = None
        super().__init__(None, *args, **kwargs)  # user is unknown until validation
        # Style
        self.fields['email'].widget.attrs.update({'placeholder': 'ایمیل', 'class': 'input'})
        self.fields['recovery_code'].widget.attrs.update({'placeholder': 'کد بازیابی', 'class': 'input'})
        self.fields['new_password1'].widget.attrs.update({'placeholder': 'گذرواژه جدید', 'class': 'input'})
        self.fields['new_password2'].widget.attrs.update({'placeholder': 'تکرار گذرواژه جدید', 'class': 'input'})

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get('email')
        code = cleaned.get('recovery_code')
        if not email or not code:
            return cleaned
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise forms.ValidationError("کاربری با این ایمیل یافت نشد.")

        # Find a matching active recovery code
        match = None
        for rc in RecoveryCode.objects.filter(user=user, used=False).order_by('-created_at'):
            if check_password(code, rc.code_hash):
                match = rc
                break
        if not match:
            raise forms.ValidationError("کد بازیابی نامعتبر یا استفاده‌شده است.")

        # set user for SetPasswordForm logic
        self.user_cache = user
        self.user = user
        self.cleaned_data['recovery_code_obj'] = match
        return cleaned

class ExamProfileForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=True, label="نام")
    last_name = forms.CharField(max_length=150, required=True, label="نام خانوادگی")
    email = forms.EmailField(required=True, label="ایمیل")
    phone = forms.CharField(max_length=20, required=False, label="شماره تماس")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user is not None:
            self.fields['first_name'].initial = getattr(self.user, 'first_name', '')
            self.fields['last_name'].initial = getattr(self.user, 'last_name', '')
            self.fields['email'].initial = getattr(self.user, 'email', '')
            profile = getattr(self.user, 'profile', None)
            self.fields['phone'].initial = getattr(profile, 'phone', '') if profile else ''
        self.fields['first_name'].widget.attrs.update({'placeholder': 'نام', 'class': 'input'})
        self.fields['last_name'].widget.attrs.update({'placeholder': 'نام خانوادگی', 'class': 'input'})
        self.fields['email'].widget.attrs.update({'placeholder': 'ایمیل', 'class': 'input'})
        self.fields['phone'].widget.attrs.update({'placeholder': 'شماره تماس', 'class': 'input'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            return email
        from .models import User
        qs = User.objects.filter(email=email)
        if self.user is not None:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email

    def save(self, user):
        from .models import Profile
        user.first_name = self.cleaned_data.get('first_name', user.first_name)
        user.last_name = self.cleaned_data.get('last_name', user.last_name)
        user.email = self.cleaned_data.get('email', user.email)
        user.save()
        Profile.objects.update_or_create(user=user, defaults={
            'phone': self.cleaned_data.get('phone', ''),
        })
        return user

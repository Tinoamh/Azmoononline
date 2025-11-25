from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView
from .forms import RegisterForm, EmailAuthenticationForm
from .forms import ExamProfileForm
from .models import Role
from .models import Profile
from .forms import RecoveryCodeResetForm
from .models import RecoveryCode


class RegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("exam_profile")

    def form_valid(self, form):
        user = form.save()
        # Ensure backend is set: authenticate with email/password then login
        auth_user = authenticate(email=user.email, password=form.cleaned_data.get("password1"))
        if auth_user is not None:
            login(self.request, auth_user)
        else:
            # Fallback: explicitly specify backend if authentication didn't return a user
            login(self.request, user, backend='accounts.backends.EmailBackend')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("home")


@method_decorator(login_required, name="dispatch")
class DashboardView(TemplateView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["role"] = getattr(self.request.user, "role", None)
        return ctx


@method_decorator(login_required, name="dispatch")
class ProfileView(TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["profile"] = getattr(self.request.user, "profile", None)
        return ctx


class EmailLoginView(FormView):
    template_name = "accounts/login.html"
    form_class = EmailAuthenticationForm
    success_url = reverse_lazy("exam_profile")

    def form_valid(self, form):
        user = form.cleaned_data['user']
        login(self.request, user)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("home")


def seed_roles(request):
    # Helper to create default roles quickly (Student, Instructor, Admin)
    defaults = [
        ("student", "دانشجو"),
        ("instructor", "استاد"),
        ("admin", "ادمین"),
    ]
    for code, name in defaults:
        Role.objects.get_or_create(code=code, defaults={"name": name})
    return redirect("/")


class RecoveryCodeResetView(FormView):
    template_name = "registration/password_reset_code.html"
    form_class = RecoveryCodeResetForm
    success_url = reverse_lazy("password_reset_complete")

    def form_valid(self, form):
        # Set new password via SetPasswordForm parent
        user = form.user_cache
        form.save()
        # Mark code as used
        rc = form.cleaned_data.get('recovery_code_obj')
        if rc:
            rc.used = True
            rc.save()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class ExamProfileView(FormView):
    template_name = "accounts/exam_profile.html"
    form_class = ExamProfileForm
    success_url = reverse_lazy("exam_profile")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save(self.request.user)
        return super().form_valid(form)

def logout_to_home(request):
    # Explicitly log out and redirect to home page
    logout(request)
    return redirect('home')

# Create your views here.

from django.urls import path
from django.contrib.auth import views as auth_views
from .views import RegisterView, DashboardView, ProfileView, EmailLoginView, RecoveryCodeResetView, ExamProfileView, logout_to_home
from .forms import AzmonPasswordResetForm

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', EmailLoginView.as_view(), name='login'),
    path('logout/', logout_to_home, name='logout'),

    # Password reset flow using built-in views with custom form and templates
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            form_class=AzmonPasswordResetForm,
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            html_email_template_name='registration/password_reset_email.html',
    ),
    name='password_reset'
    ),
    # Recovery code (no-email) flow
    path('password-reset-code/', RecoveryCodeResetView.as_view(), name='password_reset_code'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Authenticated pages
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('exam-profile/', ExamProfileView.as_view(), name='exam_profile'),
]
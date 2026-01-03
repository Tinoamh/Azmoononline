from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    RegisterView,
    DashboardView,
    ProfileView,
    ProfileEditView,
    EmailLoginView,
    RecoveryCodeResetView,
    ExamProfileView,
    ExamTakeView,
    ExamSubmitView,
    ExamResultView,
    StudentScoresView,
    logout_to_home,
    UsersListView,
    StudentsListView,
    ClassroomManageView,
    ClassesListView,
    ExamsListView,
    ExamDefineView,
    classroom_toggle_member,
    classroom_remove_student,
    user_update_role,
    user_delete,
    api_create_exam,
    api_latest_exam,
    api_my_exams,
    api_csrf,
    question_bank,
    question_bank_new,
    question_bank_create,
    question_bank_edit,
    question_bank_delete,
    api_add_question,
    api_exam_questions,
    api_question_delete,
    api_question_update,
    # Added minimal implementations in views.py
    admin_exam_delete_view,
    instructor_results_list_view,
    student_class_list_view,
)
from .admin_views_temp import admin_exam_list_view, admin_exam_edit_view
from .admin_report_view_temp import admin_exam_report_view
from .admin_class_views_temp import admin_class_list_view, admin_class_edit_view
from .instructor_report_view_temp import instructor_exam_report_view
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
    path('profile/edit/', ProfileEditView.as_view(), name='profile_edit'),
    path('exam-profile/', ExamProfileView.as_view(), name='exam_profile'),
    path('users/', UsersListView.as_view(), name='users'),
    path('students/', StudentsListView.as_view(), name='students'),
    path('classroom/', ClassroomManageView.as_view(), name='classroom'),
    path('exam-define/', ExamDefineView.as_view(), name='exam_define'),
    path('classes/', ClassesListView.as_view(), name='classes_list'),
    path('my-classes/', student_class_list_view, name='student_classes_list'),
    path('exams/', ExamsListView.as_view(), name='exam_list'),
    
    path('admin/exams/', admin_exam_list_view, name='admin_exam_list'),
    path('admin/exams/<int:pk>/edit/', admin_exam_edit_view, name='admin_exam_edit'),
    path('admin/exams/<int:pk>/delete/', admin_exam_delete_view, name='admin_exam_delete'),
    path('admin/exams/<int:exam_id>/report/', admin_exam_report_view, name='admin_exam_report'),
    
    path('admin/classes/', admin_class_list_view, name='admin_class_list'),
    path('admin/classes/new/', admin_class_edit_view, name='admin_class_new'),
    path('admin/classes/<int:pk>/edit/', admin_class_edit_view, name='admin_class_edit'),

    path('exams/<int:exam_id>/start/', ExamTakeView.as_view(), name='exam_start'),
    path('exams/<int:exam_id>/submit/', ExamSubmitView.as_view(), name='exam_submit'),
    path('exams/<int:exam_id>/result/', ExamResultView.as_view(), name='exam_result'),
    path('student/scores/', StudentScoresView.as_view(), name='student_scores'),
    path('classroom/toggle-member/', classroom_toggle_member, name='classroom_toggle_member'),
    path('classroom/<int:class_id>/remove-student/<int:student_id>/', classroom_remove_student, name='classroom_remove_student'),
    path('users/<int:pk>/role/', user_update_role, name='user_update_role'),
    path('users/<int:pk>/delete/', user_delete, name='user_delete'),
    # API endpoints for exam and questions
    path('api/create-exam/', api_create_exam, name='api_create_exam'),
    path('api/latest-exam/', api_latest_exam, name='api_latest_exam'),
    path('api/csrf/', api_csrf, name='api_csrf'),
    path('api/my-exams/', api_my_exams, name='api_my_exams'),
    path('api/exams/<int:exam_id>/add-question/', api_add_question, name='api_add_question'),
    path('api/exams/<int:exam_id>/questions/', api_exam_questions, name='api_exam_questions'),
    path('api/questions/<int:question_id>/delete/', api_question_delete, name='api_question_delete'),
    path('api/questions/<int:question_id>/update/', api_question_update, name='api_question_update'),
    path('instructor/results/', instructor_results_list_view, name='instructor_results_list'),
    path('instructor/exams/<int:exam_id>/report/', instructor_exam_report_view, name='instructor_exam_report'),
    path('question-bank/', question_bank, name='question_bank'),
    path('question-bank/new/', question_bank_new, name='question_bank_new'),
    path('question-bank/create/', question_bank_create, name='question_bank_create'),
    path('question-bank/<int:exam_id>/edit/', question_bank_edit, name='question_bank_edit'),
    path('question-bank/<int:exam_id>/delete/', question_bank_delete, name='question_bank_delete'),
]

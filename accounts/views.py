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
<<<<<<< Updated upstream
from .models import Classroom, Exam
=======
from .models import Classroom, Exam, Question
>>>>>>> Stashed changes
from .forms import RecoveryCodeResetForm
from .models import RecoveryCode
from .models import User
from django.views.decorators.http import require_POST
<<<<<<< Updated upstream
=======
from django.http import JsonResponse, HttpResponseBadRequest
from django.middleware.csrf import get_token
from django.db.models import Count
>>>>>>> Stashed changes


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

    # No inline edit on profile page per latest requirements


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

<<<<<<< Updated upstream
=======
def api_csrf(request):
    # Ensure CSRF cookie exists and return it
    token = get_token(request)
    return JsonResponse({'csrfToken': token})

@login_required
def question_bank(request):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return redirect('dashboard')
    qs = Question.objects.select_related('exam').filter(exam__created_by=u).order_by('-created_at')
    total_questions = qs.count()
    des_count = qs.filter(kind='des').count()
    mcq_count = qs.filter(kind='mcq').count()
    exams = Exam.objects.filter(created_by=u, questions__isnull=False).distinct().values('id','name')
    return render(request, 'accounts/question_bank.html', {
        'questions': qs,
        'exams': list(exams),
        'total_questions': total_questions,
        'des_count': des_count,
        'mcq_count': mcq_count,
    })

>>>>>>> Stashed changes

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

@method_decorator(login_required, name="dispatch")
class UsersListView(TemplateView):
    template_name = "accounts/users_list.html"

    def dispatch(self, request, *args, **kwargs):
        u = request.user
        is_admin = (getattr(getattr(u, 'role', None), 'code', '') == 'admin')
        if not is_admin:
            return redirect('profile')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['users'] = User.objects.select_related('role', 'profile').all()
        ctx['roles'] = list(Role.objects.filter(code__in=['admin','student','instructor']))
        return ctx

@method_decorator(login_required, name="dispatch")
class StudentsListView(TemplateView):
    template_name = "accounts/users_list.html"

    def dispatch(self, request, *args, **kwargs):
        u = request.user
        is_admin = (getattr(getattr(u, 'role', None), 'code', '') == 'admin')
        is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
        if not (is_admin or is_instructor):
            return redirect('profile')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['users'] = User.objects.select_related('role', 'profile').filter(role__code='student')
        ctx['roles'] = list(Role.objects.filter(code__in=['admin','student','instructor']))
        ctx['listing_students_only'] = True
        return ctx

@method_decorator(login_required, name="dispatch")
class ClassroomManageView(TemplateView):
    template_name = "accounts/classroom_manage.html"

    def dispatch(self, request, *args, **kwargs):
        u = request.user
        is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
        if not is_instructor:
            return redirect('profile')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        classroom, _ = Classroom.objects.get_or_create(instructor=u, defaults={'name': 'کلاس جدید'})
        students = User.objects.select_related('role', 'profile').filter(role__code='student')
        member_ids = set(classroom.students.values_list('id', flat=True))
        ctx['classroom'] = classroom
        ctx['students'] = students
        ctx['member_ids'] = member_ids
        return ctx

    def post(self, request, *args, **kwargs):
        u = request.user
        classroom, _ = Classroom.objects.get_or_create(instructor=u, defaults={'name': 'کلاس جدید'})
        name = request.POST.get('class_name', '').strip()
        if name:
            classroom.name = name
            classroom.save()
        try:
            numq = int(request.POST.get('num_questions', '0'))
        except ValueError:
            numq = 0
        exam = Exam.objects.create(name=classroom.name, classroom=classroom, num_questions=numq, created_by=u)
        exam.students.set(classroom.students.all())
        return redirect('classroom')

@login_required
@require_POST
def classroom_toggle_member(request):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return redirect('profile')
    classroom, _ = Classroom.objects.get_or_create(instructor=u, defaults={'name': 'کلاس جدید'})
    sid = request.POST.get('student_id')
    try:
        student = User.objects.get(pk=sid, role__code='student')
    except User.DoesNotExist:
        return redirect('classroom')
    if classroom.students.filter(pk=student.pk).exists():
        classroom.students.remove(student)
    else:
        classroom.students.add(student)
    return redirect('classroom')

@login_required
@require_POST
def user_update_role(request, pk: int):
    u = request.user
    is_admin = (getattr(getattr(u, 'role', None), 'code', '') == 'admin')
    if not is_admin:
        return redirect('profile')
    try:
        target = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return redirect('users')
    code = request.POST.get('role_code')
    role = Role.objects.filter(code=code).first()
    if role:
        target.role = role
        target.save()
    return redirect('users')

@login_required
@require_POST
def user_delete(request, pk: int):
    u = request.user
    is_admin = (getattr(getattr(u, 'role', None), 'code', '') == 'admin')
    if not is_admin:
        return redirect('profile')
    if u.pk == pk:
        return redirect('users')
    try:
        target = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return redirect('users')
    target.delete()
    return redirect('users')

# Create your views here.

@login_required
@require_POST
def api_create_exam(request):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return JsonResponse({'error': 'forbidden'}, status=403)
    classroom, _ = Classroom.objects.get_or_create(instructor=u, defaults={'name': 'کلاس جدید'})
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'invalid_name'}, status=400)
    exam = Exam.objects.create(name=name, classroom=classroom, created_by=u)
    exam.students.set(classroom.students.all())
    return JsonResponse({'ok': True, 'exam': {'id': exam.id, 'name': exam.name}})

@login_required
def api_latest_exam(request):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return JsonResponse({'error': 'forbidden'}, status=403)
    exam = Exam.objects.filter(created_by=u).order_by('-created_at').first()
    if not exam:
        return JsonResponse({'exam': None})
    return JsonResponse({'exam': {'id': exam.id, 'name': exam.name, 'num_questions': exam.num_questions}})

@login_required
def api_my_exams(request):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return JsonResponse({'error': 'forbidden'}, status=403)
    exams = Exam.objects.filter(created_by=u).order_by('-created_at')
    data = [
        {
            'id': e.id,
            'name': e.name,
            'num_questions': e.num_questions,
            'created_at': e.created_at.isoformat(),
        }
        for e in exams
    ]
    return JsonResponse({'exams': data})

@login_required
@require_POST
def api_add_question(request, exam_id: int):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return JsonResponse({'error': 'forbidden'}, status=403)
    try:
        exam = Exam.objects.get(pk=exam_id, created_by=u)
    except Exam.DoesNotExist:
        return JsonResponse({'error': 'exam_not_found'}, status=404)
    kind = request.POST.get('kind')
    text = request.POST.get('text', '').strip()
    if not kind or not text:
        return JsonResponse({'error': 'invalid_payload'}, status=400)
    if kind == 'des':
        answer_text = request.POST.get('answer_text', '').strip()
        q = exam.questions.create(kind='des', text=text, answer_text=answer_text)
    elif kind == 'mcq':
        # options can be provided as JSON string or multiple fields options[]
        import json
        options_raw = request.POST.get('options')
        options_list = None
        if options_raw:
            try:
                options_list = json.loads(options_raw)
            except Exception:
                options_list = None
        if options_list is None:
            options_list = request.POST.getlist('options[]')
        try:
            correct_index = int(request.POST.get('correct_index'))
        except (TypeError, ValueError):
            correct_index = None
        if not options_list or correct_index is None or correct_index < 0 or correct_index >= len(options_list):
            return JsonResponse({'error': 'invalid_options'}, status=400)
        q = exam.questions.create(kind='mcq', text=text, options=options_list, correct_index=correct_index)
    else:
        return JsonResponse({'error': 'invalid_kind'}, status=400)
    # increment exam.num_questions
    exam.num_questions = exam.questions.count()
    exam.save(update_fields=['num_questions'])
    return JsonResponse({'ok': True, 'question': {'id': q.id}})

@login_required
def api_exam_questions(request, exam_id: int):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return JsonResponse({'error': 'forbidden'}, status=403)
    try:
        exam = Exam.objects.get(pk=exam_id, created_by=u)
    except Exam.DoesNotExist:
        return JsonResponse({'error': 'exam_not_found'}, status=404)
    qs = exam.questions.order_by('created_at')
    data = []
    for q in qs:
        data.append({
            'id': q.id,
            'kind': q.kind,
            'text': q.text,
            'answer_text': q.answer_text,
            'options': q.options or [],
            'correct_index': q.correct_index,
            'created_at': q.created_at.isoformat(),
        })
    return JsonResponse({'questions': data})

@login_required
@require_POST
def api_question_delete(request, question_id: int):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return JsonResponse({'error': 'forbidden'}, status=403)
    try:
        q = Question.objects.select_related('exam').get(pk=question_id, exam__created_by=u)
    except Question.DoesNotExist:
        return JsonResponse({'error': 'question_not_found'}, status=404)
    exam = q.exam
    q.delete()
    exam.num_questions = exam.questions.count()
    exam.save(update_fields=['num_questions'])
    return JsonResponse({'ok': True})

@login_required
@require_POST
def api_question_update(request, question_id: int):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return JsonResponse({'error': 'forbidden'}, status=403)
    try:
        q = Question.objects.select_related('exam').get(pk=question_id, exam__created_by=u)
    except Question.DoesNotExist:
        return JsonResponse({'error': 'question_not_found'}, status=404)
    text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({'error': 'invalid_payload'}, status=400)
    q.text = text
    if q.kind == 'des':
        q.answer_text = request.POST.get('answer_text', '').strip()
    elif q.kind == 'mcq':
        import json
        options_raw = request.POST.get('options')
        options_list = None
        if options_raw:
            try:
                options_list = json.loads(options_raw)
            except Exception:
                options_list = None
        if options_list is None:
            options_list = request.POST.getlist('options[]')
        try:
            correct_index = int(request.POST.get('correct_index'))
        except (TypeError, ValueError):
            correct_index = None
        if not options_list or correct_index is None or correct_index < 0 or correct_index >= len(options_list):
            return JsonResponse({'error': 'invalid_options'}, status=400)
        q.options = options_list
        q.correct_index = correct_index
    q.save()
    return JsonResponse({'ok': True, 'question': {
        'id': q.id,
        'kind': q.kind,
        'text': q.text,
        'answer_text': q.answer_text,
        'options': q.options or [],
        'correct_index': q.correct_index,
    }})

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
from .models import Classroom, Exam, Question, ExamAssignment, QuestionOptionImage
from .forms import RecoveryCodeResetForm
from .models import RecoveryCode
from .models import User
from .utils import compress_image
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.middleware.csrf import get_token
from django.db.models import Count
from django.utils import timezone


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
    # Only show defined question banks: exams with no source (root banks)
    banks = (Exam.objects
             .filter(created_by=u, source_exam__isnull=True)
             .annotate(q_count=Count('questions'))
             .order_by('-created_at'))
    # Stats only over bank exams
    totals = Question.objects.filter(exam__created_by=u, exam__source_exam__isnull=True)
    total_questions = totals.count()
    des_count = totals.filter(kind='des').count()
    mcq_count = totals.filter(kind='mcq').count()
    return render(request, 'accounts/question_bank.html', {
        'banks': banks,
        'total_questions': total_questions,
        'des_count': des_count,
        'mcq_count': mcq_count,
    })

@login_required
def question_bank_new(request):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return redirect('dashboard')
    return render(request, 'accounts/question_bank_new.html')

@login_required
@require_POST
def question_bank_create(request):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return redirect('dashboard')
    name = request.POST.get('name', '').strip()
    if not name:
        return redirect('question_bank')
    classroom = Classroom.objects.filter(instructor=u).order_by('id').first()
    if classroom is None:
        classroom = Classroom.objects.create(instructor=u, name='کلاس جدید', is_staging=True)
    Exam.objects.create(name=name, classroom=classroom, created_by=u)
    return redirect('question_bank')

@login_required
def question_bank_edit(request, exam_id: int):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return redirect('dashboard')
    try:
        exam = Exam.objects.get(pk=exam_id, created_by=u)
    except Exam.DoesNotExist:
        return redirect('question_bank')
    return render(request, 'accounts/question_bank_edit.html', {'exam': exam})

@login_required
@require_POST
def question_bank_delete(request, exam_id: int):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return redirect('dashboard')
    try:
        exam = Exam.objects.get(pk=exam_id, created_by=u)
    except Exam.DoesNotExist:
        return redirect('question_bank')
    exam.delete()
    return redirect('question_bank')


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
        u = self.request.user
        
        # Populate classes for the filter tabs
        is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
        if is_instructor:
            ctx['classes'] = Classroom.objects.filter(instructor=u, is_staging=False, is_exam_room=False).order_by('name')
        
        class_id = self.request.GET.get('class_id')
        selected_class = None
        if class_id and is_instructor:
            try:
                selected_class = Classroom.objects.get(pk=class_id, instructor=u)
                ctx['users'] = selected_class.students.select_related('role', 'profile').all()
                ctx['current_class'] = selected_class
                ctx['selected_class_id'] = int(class_id)
            except (ValueError, Classroom.DoesNotExist):
                # Fallback to all students if invalid class
                ctx['users'] = User.objects.select_related('role', 'profile').filter(role__code='student')
        else:
            ctx['users'] = User.objects.select_related('role', 'profile').filter(role__code='student')

        ctx['roles'] = list(Role.objects.filter(code__in=['admin','student','instructor']))
        ctx['listing_students_only'] = True
        return ctx

@login_required
@require_POST
def classroom_remove_student(request, class_id: int, student_id: int):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return redirect('dashboard')
    
    try:
        classroom = Classroom.objects.get(pk=class_id, instructor=u)
        student = User.objects.get(pk=student_id)
        classroom.students.remove(student)
    except (Classroom.DoesNotExist, User.DoesNotExist):
        pass
        
    return redirect(f'/accounts/students/?class_id={class_id}')

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
        classroom, _ = Classroom.objects.get_or_create(instructor=u, is_staging=True, defaults={'name': 'کلاس موقت'})
        if self.request.GET.get('reset') == '1':
            classroom.students.clear()
            classroom.name = 'کلاس جدید'
            classroom.save(update_fields=['name'])
        students = User.objects.select_related('role', 'profile').filter(role__code='student')
        member_ids = set(classroom.students.values_list('id', flat=True))
        ctx['classroom'] = classroom
        ctx['students'] = students
        ctx['member_ids'] = member_ids
        from django.db.models import Count
        banks = Exam.objects.filter(created_by=u).annotate(q_count=Count('questions')).order_by('-created_at')
        ctx['banks'] = banks
        return ctx

    def post(self, request, *args, **kwargs):
        u = request.user
        staging, _ = Classroom.objects.get_or_create(instructor=u, is_staging=True, defaults={'name': 'کلاس موقت'})
        name = request.POST.get('exam_name', '').strip()
        new_class = Classroom.objects.create(instructor=u, name=(name or 'آزمون جدید'), is_staging=False)
        new_class.students.set(staging.students.all())
        try:
            numq = int(request.POST.get('num_questions', '0'))
        except ValueError:
            numq = 0
        src_id = request.POST.get('source_exam_id')
        src = None
        if src_id:
            try:
                src = Exam.objects.get(pk=src_id, created_by=u)
            except Exam.DoesNotExist:
                src = None
        if src:
            exam = Exam.objects.create(name=(name or 'آزمون جدید'), classroom=new_class, num_questions=numq, created_by=u, source_exam=src)
            exam.students.set(new_class.students.all())
            import random
            src_qs = list(src.questions.values_list('id', flat=True))
            for s in new_class.students.all():
                sel = src_qs[:]
                random.shuffle(sel)
                if numq and numq > 0:
                    sel = sel[:numq]
                ExamAssignment.objects.create(exam=exam, student=s, selected_question_ids=sel)
        return redirect('exam_list')

@method_decorator(login_required, name="dispatch")
class ClassesListView(TemplateView):
    template_name = "accounts/classes_list.html"

    def dispatch(self, request, *args, **kwargs):
        u = request.user
        is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
        if not is_instructor:
            return redirect('profile')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        # Show only real classes (exclude staging and per-exam classrooms)
        ctx['classes'] = Classroom.objects.filter(instructor=u, is_staging=False, is_exam_room=False).order_by('name')
        return ctx

@method_decorator(login_required, name="dispatch")
class ExamsListView(TemplateView):
    template_name = "accounts/exam_list.html"

    def dispatch(self, request, *args, **kwargs):
        u = request.user
        is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
        is_student = (getattr(getattr(u, 'role', None), 'code', '') == 'student')
        if not (is_instructor or is_student):
            return redirect('profile')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        is_student = (getattr(getattr(u, 'role', None), 'code', '') == 'student')
        
        ctx['now'] = timezone.now()
        
        if is_student:
            ctx['is_student_view'] = True
            # Fetch assigned exams
            assignments = ExamAssignment.objects.filter(student=u).select_related('exam').order_by('-created_at')
            exams = []
            completed_ids = []
            
            for asm in assignments:
                exams.append(asm.exam)
                if asm.completed_at:
                    completed_ids.append(asm.exam.id)
            
            ctx['exams'] = exams
            ctx['completed_exam_ids'] = completed_ids
        else:
            ctx['exams'] = Exam.objects.filter(created_by=u).order_by('-created_at')
            
        return ctx

@method_decorator(login_required, name="dispatch")
class ExamDefineView(TemplateView):
    template_name = "accounts/exam_define.html"

    def dispatch(self, request, *args, **kwargs):
        u = request.user
        is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
        if not is_instructor:
            return redirect('profile')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        from django.db.models import Count

        # Classes owned by instructor
        classes = Classroom.objects.filter(instructor=u, is_staging=False, is_exam_room=False).order_by('name')
        selected_class_id = self.request.GET.get('class_id')
        selected_class = None
        if selected_class_id:
            try:
                selected_class = classes.get(pk=int(selected_class_id))
            except (ValueError, Classroom.DoesNotExist):
                selected_class = None

        # Students list: show class members if class selected, otherwise all students
        if selected_class:
            students = selected_class.students.select_related('role').filter(role__code='student')
        else:
            students = User.objects.select_related('role').filter(role__code='student')

        # Banks: exams with no assigned students (used as question banks)
        banks = (
            Exam.objects.filter(created_by=u, students__isnull=True)
            .annotate(q_count=Count('questions'))
            .order_by('-created_at')
            .distinct()
        )

        ctx['classes'] = classes
        ctx['selected_class_id'] = selected_class.id if selected_class else None
        ctx['students'] = students
        ctx['banks'] = banks
        return ctx

    def post(self, request, *args, **kwargs):
        u = request.user
        name = request.POST.get('exam_name', '').strip()
        try:
            numq = int(request.POST.get('num_questions', '0'))
        except ValueError:
            numq = 0
        src_id = request.POST.get('source_exam_id')
        sel_ids = request.POST.getlist('student_ids')

        # New: validate duration/start/end and compute defaults
        duration_str = request.POST.get('duration', '').strip()
        start_time_str = request.POST.get('start_time', '').strip()
        end_time_str = request.POST.get('end_time', '').strip()

        error_message = None
        from datetime import datetime, timedelta

        # Parse duration
        duration_val = None
        if not duration_str:
            error_message = "مدت زمان آزمون الزامی است."
        else:
            try:
                duration_val = int(duration_str)
                if duration_val < 1:
                    error_message = "مدت زمان آزمون باید حداقل ۱ دقیقه باشد."
            except ValueError:
                error_message = "مدت زمان آزمون مقدار صحیحی نیست."

        # Parse start_time
        start_dt = None
        if not error_message:
            if not start_time_str:
                error_message = "تاریخ و ساعت شروع آزمون الزامی است."
            else:
                try:
                    start_dt = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    error_message = "قالب تاریخ/ساعت شروع نامعتبر است."

        # Parse or compute end_time
        end_dt = None
        if not error_message:
            if end_time_str:
                try:
                    end_dt = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    error_message = "قالب تاریخ/ساعت پایان نامعتبر است."
            else:
                # Auto-set end time = start + duration
                end_dt = start_dt + timedelta(minutes=duration_val or 0)

        # Validate time difference >= duration
        if not error_message and start_dt and end_dt and duration_val is not None:
            min_end = start_dt + timedelta(minutes=duration_val)
            if end_dt < min_end:
                error_message = "فاصله زمان پایان و شروع نباید کمتر از مدت آزمون باشد."

        # Validate bank question count if source exam selected
        src = None
        src_q_count = None
        if not error_message and src_id:
            try:
                src = Exam.objects.get(pk=src_id, created_by=u)
                src_q_count = src.questions.count()
                if numq and numq > src_q_count:
                    error_message = "تعداد سوالات انتخابی بیشتر از تعداد سوالات بانک است."
            except Exam.DoesNotExist:
                src = None

        if error_message:
            # Re-render with error and context
            from django.db.models import Count
            ctx = {
                'students': User.objects.select_related('role').filter(role__code='student'),
                'banks': Exam.objects.filter(created_by=u).annotate(q_count=Count('questions')).order_by('-created_at'),
                'error_message': error_message,
            }
            return render(request, 'accounts/exam_define.html', ctx)

        # Use selected classroom if provided, otherwise create a per-exam classroom
        class_id = request.POST.get('class_id')
        classroom = None
        if class_id:
            try:
                classroom = Classroom.objects.get(pk=int(class_id), instructor=u)
            except (ValueError, Classroom.DoesNotExist):
                classroom = None
        if classroom is None:
            classroom = Classroom.objects.create(instructor=u, name=(name or 'آزمون جدید'), is_staging=False, is_exam_room=True)
            students_qs = User.objects.filter(id__in=sel_ids)
            classroom.students.set(students_qs)

        exam = Exam.objects.create(
            name=(name or 'آزمون جدید'),
            classroom=classroom,
            num_questions=numq,
            created_by=u,
            source_exam=src,
            duration=(duration_val or 60),
            start_time=start_dt,
            end_time=end_dt,
        )
        exam.students.set(classroom.students.all())

        # Random selection per student from source exam if provided
        if src:
            import random
            src_qs = list(src.questions.values_list('id', flat=True))
            for s in classroom.students.all():
                sel = src_qs[:]
                random.shuffle(sel)
                if numq and numq > 0:
                    sel = sel[:numq]
                ExamAssignment.objects.create(exam=exam, student=s, selected_question_ids=sel)

        return redirect('exam_list')

@login_required
@require_POST
def classroom_toggle_member(request):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return redirect('profile')
    classroom, _ = Classroom.objects.get_or_create(instructor=u, is_staging=True, defaults={'name': 'کلاس موقت'})
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
    
    # Use existing classroom or create one safely (without unique constraints on instructor alone)
    # We prefer to find a "default" classroom if possible, or create one.
    # The previous logic used 'get_or_create' which fails if multiple exist.
    classroom = Classroom.objects.filter(instructor=u, name='کلاس جدید').first()
    if not classroom:
        # Try any classroom? Or just create a new one?
        # Let's create one if not exists to be safe, or pick the first one available.
        classroom = Classroom.objects.filter(instructor=u).first()
        if not classroom:
            classroom = Classroom.objects.create(instructor=u, name='کلاس جدید')
            
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
        # If there's an image, text can be optional (or we can use a placeholder)
        img_file = request.FILES.get('image')
        if not img_file and not text:
             return JsonResponse({'error': 'invalid_payload'}, status=400)
        if not text:
             text = "سوال تصویری"

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
        
        # Allow empty option text if image exists for that index?
        # The frontend logic sends empty strings.
        # We need to check if EITHER text OR image exists for at least 2 options.
        # But here we don't easily know about option images yet (they are processed after).
        # However, we can check request.FILES for option_image_X.
        
        # Let's relax the validation: if options_list has enough entries (even empty), check if they have content OR image.
        
        try:
            correct_index = int(request.POST.get('correct_index'))
        except (TypeError, ValueError):
            correct_index = None
            
        if not options_list or correct_index is None or correct_index < 0 or correct_index >= len(options_list):
             return JsonResponse({'error': 'invalid_options'}, status=400)
             
        # Validate that at least 2 options have content (text or image)
        valid_opts_count = 0
        for idx, opt_text in enumerate(options_list):
            has_text = bool(opt_text.strip())
            has_img = bool(request.FILES.get(f'option_image_{idx}'))
            if has_text or has_img:
                valid_opts_count += 1
        
        if valid_opts_count < 2:
             return JsonResponse({'error': 'invalid_options_count'}, status=400)

        q = exam.questions.create(kind='mcq', text=text, options=options_list, correct_index=correct_index)
    else:
        return JsonResponse({'error': 'invalid_kind'}, status=400)

    # Handle Question Image
    img_file = request.FILES.get('image')
    if img_file:
        q.image = compress_image(img_file)
        q.save(update_fields=['image'])

    # Handle Option Images (for MCQ)
    if kind == 'mcq' and options_list:
        for idx in range(len(options_list)):
            opt_img_file = request.FILES.get(f'option_image_{idx}')
            if opt_img_file:
                compressed = compress_image(opt_img_file)
                QuestionOptionImage.objects.create(question=q, image=compressed, option_index=idx)

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
    qs = exam.questions.order_by('created_at').prefetch_related('option_images')
    data = []
    for q in qs:
        # Map option images: index -> url
        opt_imgs = {oi.option_index: oi.image.url for oi in q.option_images.all() if oi.image}
        
        data.append({
            'id': q.id,
            'kind': q.kind,
            'text': q.text,
            'image': q.image.url if q.image else None,
            'answer_text': q.answer_text,
            'options': q.options or [],
            'option_images': opt_imgs,
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
    
    # Update Question Image
    img_file = request.FILES.get('image')
    if img_file:
        q.image = compress_image(img_file)
    
    # Update Option Images
    if q.kind == 'mcq' and (q.options or []):
        for idx in range(len(q.options)):
            opt_img_file = request.FILES.get(f'option_image_{idx}')
            if opt_img_file:
                # Remove old if exists for this index
                QuestionOptionImage.objects.filter(question=q, option_index=idx).delete()
                compressed = compress_image(opt_img_file)
                QuestionOptionImage.objects.create(question=q, image=compressed, option_index=idx)
    
    q.save()
    return JsonResponse({'ok': True, 'question': {
        'id': q.id,
        'kind': q.kind,
        'text': q.text,
        'image': q.image.url if q.image else None,
        'answer_text': q.answer_text,
        'options': q.options or [],
        'correct_index': q.correct_index,
    }})

# --- Minimal views added to satisfy URL imports and enable project run ---
@method_decorator(login_required, name="dispatch")
class ProfileEditView(TemplateView):
    template_name = "accounts/profile_edit.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["profile"] = getattr(self.request.user, "profile", None)
        return ctx

@method_decorator(login_required, name="dispatch")
class ExamTakeView(TemplateView):
    template_name = "accounts/exam_take.html"

    def dispatch(self, request, *args, **kwargs):
        exam_id = kwargs.get("exam_id")
        try:
            exam = Exam.objects.get(pk=exam_id)
        except Exam.DoesNotExist:
            return redirect("dashboard")
        u = request.user
        now = timezone.now()
        assignment = ExamAssignment.objects.filter(exam_id=exam_id, student=u).first()
        if not assignment:
            if exam.source_exam_id:
                order_ids = list(exam.questions.values_list("id", flat=True))
            else:
                order_ids = list(exam.questions.values_list("id", flat=True))
            assignment = ExamAssignment.objects.create(exam=exam, student=u, selected_question_ids=order_ids)
        if exam.start_time and now < exam.start_time:
            return redirect("exam_result", exam_id=exam.id)
        if exam.end_time and now > exam.end_time:
            if not assignment.completed_at:
                assignment.score = 0
                assignment.completed_at = exam.end_time
                assignment.student_answers = {}
                assignment.save()
            return redirect("exam_result", exam_id=exam.id)
        if assignment.completed_at:
            return redirect("exam_result", exam_id=exam.id)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        exam_id = self.kwargs.get("exam_id")
        exam = Exam.objects.filter(pk=exam_id).first()
        assignment = ExamAssignment.objects.filter(exam_id=exam_id, student=self.request.user).first()
        ctx["exam"] = exam
        ctx["assignment"] = assignment
        
        if assignment:
            # Fetch questions in the order defined in assignment
            q_ids = assignment.selected_question_ids
            # Prefetch option images
            qs = Question.objects.filter(id__in=q_ids).prefetch_related('option_images')
            q_map = {q.id: q for q in qs}
            questions = []
            for qid in q_ids:
                if qid in q_map:
                    questions.append(q_map[qid])
            ctx["questions"] = questions
        else:
            ctx["questions"] = []
            
        return ctx

@method_decorator(login_required, name="dispatch")
class ExamSubmitView(TemplateView):
    template_name = "accounts/exam_resault.html"

    def dispatch(self, request, *args, **kwargs):
        exam_id = kwargs.get("exam_id")
        if not Exam.objects.filter(pk=exam_id).exists():
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        exam_id = self.kwargs.get("exam_id")
        ctx["exam"] = Exam.objects.filter(pk=exam_id).first()
        return ctx

    def post(self, request, *args, **kwargs):
        exam_id = kwargs.get("exam_id")
        exam = Exam.objects.filter(pk=exam_id).first()
        if not exam:
            return redirect("dashboard")
        assignment = ExamAssignment.objects.filter(exam=exam, student=request.user).first()
        if not assignment:
            assignment = ExamAssignment.objects.create(exam=exam, student=request.user, selected_question_ids=list(exam.questions.values_list("id", flat=True)))
        now = timezone.now()
        if assignment.completed_at:
            return redirect("exam_result", exam_id=exam.id)
        if exam.end_time and now > exam.end_time:
            assignment.score = 0
            assignment.completed_at = exam.end_time
            assignment.student_answers = {}
            assignment.save()
            return redirect("exam_result", exam_id=exam.id)
        answers = {}
        for k, v in request.POST.items():
            if k.startswith("q"):
                try:
                    qid = int(k[1:])
                    answers[qid] = v
                except ValueError:
                    pass
        correct = 0
        incorrect = 0
        unanswered = 0
        order_ids = assignment.selected_question_ids or list(exam.questions.values_list("id", flat=True))
        qs = Question.objects.filter(id__in=order_ids)
        qmap = {q.id: q for q in qs}
        question_details = []
        for qid in order_ids:
            q = qmap.get(qid)
            if not q:
                continue
            ans = answers.get(qid, "")
            if q.kind == "mcq":
                if ans == "":
                    unanswered += 1
                else:
                    try:
                        ai = int(ans)
                        if q.correct_index is not None and ai == q.correct_index:
                            correct += 1
                        else:
                            incorrect += 1
                        question_details.append({
                            "id": qid,
                            "text": q.text,
                            "options": q.options or [],
                            "correct_index": q.correct_index,
                            "chosen_index": ai,
                        })
                    except ValueError:
                        incorrect += 1
                        question_details.append({
                            "id": qid,
                            "text": q.text,
                            "options": q.options or [],
                            "correct_index": q.correct_index,
                            "chosen_index": None,
                        })
            else:
                if ans == "":
                    unanswered += 1
                question_details.append({
                    "id": qid,
                    "text": q.text,
                    "options": [],
                    "correct_index": None,
                    "chosen_index": None,
                })
        total = len(order_ids)
        score = (correct / total * 100) if total else 0
        assignment.student_answers = answers
        assignment.score = score
        assignment.completed_at = timezone.now()
        assignment.save()
        class_asms = ExamAssignment.objects.filter(exam=exam, completed_at__isnull=False).exclude(score__isnull=True)
        import statistics
        scores = [a.score for a in class_asms]
        class_avg = statistics.mean(scores) if scores else 0
        class_max = max(scores) if scores else 0
        class_min = min(scores) if scores else 0
        hist = ExamAssignment.objects.filter(student=request.user, completed_at__isnull=False).select_related("exam").order_by("completed_at")
        history_data = [{"exam_name": h.exam.name, "score": h.score or 0} for h in hist]
        best_exam = hist.order_by("-score").first()
        worst_exam = hist.order_by("score").first()
        ctx = {
            "exam": exam,
            "score_percent": score,
            "correct_count": correct,
            "incorrect_count": incorrect,
            "unanswered_count": unanswered,
            "total_questions": total,
            "class_avg": class_avg,
            "class_max": class_max,
            "class_min": class_min,
            "history_data": history_data,
            "best_exam": best_exam,
            "worst_exam": worst_exam,
            "question_details": question_details,
        }
        return render(request, "accounts/exam_result.html", ctx)

@method_decorator(login_required, name="dispatch")
class ExamResultView(TemplateView):
    template_name = "accounts/exam_result.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        exam_id = self.kwargs.get("exam_id")
        exam = Exam.objects.filter(pk=exam_id).first()
        if not exam:
            return ctx
        assignment = ExamAssignment.objects.filter(exam=exam, student=self.request.user).first()
        now = timezone.now()
        if not assignment and exam.end_time and now > exam.end_time:
            order_ids = list(exam.questions.values_list("id", flat=True))
            assignment = ExamAssignment.objects.create(exam=exam, student=self.request.user, selected_question_ids=order_ids, score=0, student_answers={}, completed_at=exam.end_time)
        correct = 0
        incorrect = 0
        unanswered = 0
        total = 0
        question_details = []
        if assignment:
            order_ids = assignment.selected_question_ids or list(exam.questions.values_list("id", flat=True))
            qs = Question.objects.filter(id__in=order_ids)
            qmap = {q.id: q for q in qs}
            total = len(order_ids)
            answers = assignment.student_answers or {}
            for qid in order_ids:
                q = qmap.get(qid)
                if not q:
                    continue
                ans = answers.get(str(qid), answers.get(qid))
                if q.kind == "mcq":
                    if ans in ("", None):
                        unanswered += 1
                        question_details.append({
                            "id": qid,
                            "text": q.text,
                            "options": q.options or [],
                            "correct_index": q.correct_index,
                            "chosen_index": None,
                        })
                    else:
                        try:
                            ai = int(ans)
                            if q.correct_index is not None and ai == q.correct_index:
                                correct += 1
                            else:
                                incorrect += 1
                            question_details.append({
                                "id": qid,
                                "text": q.text,
                                "options": q.options or [],
                                "correct_index": q.correct_index,
                                "chosen_index": ai,
                            })
                        except ValueError:
                            incorrect += 1
                            question_details.append({
                                "id": qid,
                                "text": q.text,
                                "options": q.options or [],
                                "correct_index": q.correct_index,
                                "chosen_index": None,
                            })
                else:
                    if not ans:
                        unanswered += 1
                    question_details.append({
                        "id": qid,
                        "text": q.text,
                        "options": [],
                        "correct_index": None,
                        "chosen_index": None,
                    })
        score = (correct / total * 100) if total else (assignment.score or 0 if assignment else 0)
        class_asms = ExamAssignment.objects.filter(exam=exam, completed_at__isnull=False).exclude(score__isnull=True)
        import statistics
        scores = [a.score for a in class_asms]
        class_avg = statistics.mean(scores) if scores else 0
        class_max = max(scores) if scores else 0
        class_min = min(scores) if scores else 0
        hist = ExamAssignment.objects.filter(student=self.request.user, completed_at__isnull=False).select_related("exam").order_by("completed_at")
        history_data = [{"exam_name": h.exam.name, "score": h.score or 0} for h in hist]
        best_exam = hist.order_by("-score").first()
        worst_exam = hist.order_by("score").first()
        ctx.update({
            "exam": exam,
            "score_percent": score,
            "correct_count": correct,
            "incorrect_count": incorrect,
            "unanswered_count": unanswered,
            "total_questions": total or exam.questions.count(),
            "class_avg": class_avg,
            "class_max": class_max,
            "class_min": class_min,
            "history_data": history_data,
            "best_exam": best_exam,
            "worst_exam": worst_exam,
            "question_details": question_details,
        })
        return ctx

@method_decorator(login_required, name="dispatch")
class StudentScoresView(TemplateView):
    template_name = "accounts/student_scores.html"

    def dispatch(self, request, *args, **kwargs):
        u = request.user
        if getattr(getattr(u, 'role', None), 'code', '') != 'student':
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        assignments = ExamAssignment.objects.filter(
            student=self.request.user,
            completed_at__isnull=False
        ).select_related('exam').order_by('-completed_at')
        ctx['assignments'] = assignments
        return ctx

@login_required
def admin_exam_delete_view(request, pk: int):
    u = request.user
    is_admin = (getattr(getattr(u, 'role', None), 'code', '') == 'admin')
    if not is_admin:
        return redirect('profile')
    try:
        exam = Exam.objects.get(pk=pk)
        exam.delete()
    except Exam.DoesNotExist:
        pass
    return redirect('admin_exam_list')

@login_required
def instructor_results_list_view(request):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return redirect('dashboard')
    exams = list(Exam.objects.filter(created_by=u).order_by('-created_at'))
    for e in exams:
        e.total_assigned = e.students.count()
        e.participant_count = ExamAssignment.objects.filter(exam=e, completed_at__isnull=False).count()
    return render(request, 'accounts/instructor_results_list.html', {'exams': exams})

@login_required
def student_class_list_view(request):
    u = request.user
    is_student = (getattr(getattr(u, 'role', None), 'code', '') == 'student')
    if not is_student:
        return redirect('dashboard')
    
    classes = Classroom.objects.filter(students__in=[u]).order_by('-id')
    classes_data = []
    now = timezone.now()
    
    for cls in classes:
        # Get assignments for this student in this class
        assignments = ExamAssignment.objects.filter(student=u, exam__classroom=cls).select_related('exam')
        
        cls_exams = []
        for asm in assignments:
            exam = asm.exam
            
            status = 'pending'
            if asm.completed_at:
                status = 'completed'
            # If start_time passed and not completed?
            
            is_active = True
            if exam.start_time and now < exam.start_time:
                is_active = False
            if exam.end_time and now > exam.end_time:
                is_active = False
            
            # If expired and not completed -> what?
            
            cls_exams.append({
                'exam': exam,
                'status': status,
                'is_active': is_active
            })
            
        classes_data.append({
            'classroom': cls,
            'exams': cls_exams
        })
        
    return render(request, 'accounts/student_classes_list.html', {'classes_data': classes_data})

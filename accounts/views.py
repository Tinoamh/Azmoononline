from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views.generic import FormView, TemplateView, View
from .forms import RegisterForm, EmailAuthenticationForm
from .forms import ExamProfileForm, SimpleProfileEditForm
from .models import Role
from .models import Profile
from .models import Classroom, Exam, Question, ExamAssignment
from .forms import RecoveryCodeResetForm
from .models import RecoveryCode
from .models import User
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.middleware.csrf import get_token
from django.db.models import Count, Q
from django.views.generic import TemplateView


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


@method_decorator(login_required, name="dispatch")
class ProfileEditView(FormView):
    template_name = "accounts/profile_edit.html"
    form_class = SimpleProfileEditForm
    success_url = reverse_lazy("profile")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save(self.request.user)
        return super().form_valid(form)


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
    banks = (Exam.objects
             .filter(created_by=u, source_exam__isnull=True)
             .annotate(q_count=Count('questions'))
             .order_by('-created_at'))
    totals = Question.objects.filter(exam__created_by=u)
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
    exam = Exam.objects.create(name=name, classroom=classroom, created_by=u)

    # Process questions from hidden input
    import json
    q_data = request.POST.get('questions_data')
    if q_data:
        try:
            questions_list = json.loads(q_data)
            for q_item in questions_list:
                kind = q_item.get('kind')
                text = q_item.get('text', '').strip()
                if not text:
                    continue
                
                if kind == 'des':
                    exam.questions.create(
                        kind='des',
                        text=text,
                        answer_text=q_item.get('answer_text', '').strip()
                    )
                elif kind == 'mcq':
                    options = q_item.get('options', [])
                    correct_index = q_item.get('correct_index')
                    # Basic validation
                    if not options or correct_index is None:
                        continue
                    exam.questions.create(
                        kind='mcq',
                        text=text,
                        options=options,
                        correct_index=correct_index
                    )
            
            # Update exam question count
            exam.num_questions = exam.questions.count()
            exam.save(update_fields=['num_questions'])

        except Exception as e:
            # In production, log this error properly
            print(f"Error saving questions for exam {exam.id}: {e}")

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
            exam = Exam.objects.create(name=(name or new_class.name), classroom=new_class, num_questions=numq, created_by=u, source_exam=src)
            exam.students.set(new_class.students.all())
            import random
            src_qs = list(src.questions.values_list('id', flat=True))
            for s in new_class.students.all():
                sel = src_qs[:]
                random.shuffle(sel)
                if numq and numq > 0:
                    sel = sel[:numq]
                ExamAssignment.objects.create(exam=exam, student=s, selected_question_ids=sel)
        return redirect('exams_list')

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
        ctx['classes'] = Classroom.objects.filter(instructor=u).order_by('name')
        return ctx

@method_decorator(login_required, name="dispatch")
class ExamsListView(TemplateView):
    template_name = "accounts/exams_list.html"

    def dispatch(self, request, *args, **kwargs):
        u = request.user
        role_code = getattr(getattr(u, 'role', None), 'code', '')
        if role_code == 'instructor':
            return super().dispatch(request, *args, **kwargs)
        elif role_code == 'student':
            exams_qs = Exam.objects.filter(Q(students=u) | Q(assignments__student=u)).distinct().order_by('-created_at')
            if exams_qs.count() == 1:
                e = exams_qs.first()
                return redirect('exam_start', exam_id=e.id)
            return super().dispatch(request, *args, **kwargs)
        else:
            return redirect('profile')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        role_code = getattr(getattr(u, 'role', None), 'code', '')
        if role_code == 'instructor':
            ctx['exams'] = Exam.objects.filter(created_by=u, source_exam__isnull=False).order_by('-created_at')
            ctx['is_student_view'] = False
        elif role_code == 'student':
            exams = Exam.objects.filter(Q(students=u) | Q(assignments__student=u)).distinct().order_by('-created_at')
            ctx['exams'] = exams
            ctx['is_student_view'] = True
            ctx['now'] = timezone.now()
            
            # Find completed exams
            completed_ids = ExamAssignment.objects.filter(
                student=u, 
                exam__in=exams, 
                completed_at__isnull=False
            ).values_list('exam_id', flat=True)
            ctx['completed_exam_ids'] = set(completed_ids)
        else:
            ctx['exams'] = Exam.objects.none()
            ctx['is_student_view'] = False
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
        students = User.objects.select_related('role').filter(role__code='student')
        from django.db.models import Count
        banks = (Exam.objects
                 .filter(created_by=u, source_exam__isnull=True)
                 .annotate(q_count=Count('questions'))
                 .order_by('-created_at'))
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

        # Build classroom specific to this exam
        classroom = Classroom.objects.create(instructor=u, name=(name or 'آزمون جدید'), is_staging=False)
        students = User.objects.filter(id__in=sel_ids)
        classroom.students.set(students)

        src = None
        if src_id:
            try:
                src = Exam.objects.get(pk=src_id, created_by=u)
            except Exam.DoesNotExist:
                src = None
        
        try:
            duration = int(request.POST.get('duration', '60'))
        except ValueError:
            duration = 60

        from datetime import datetime
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')
        start_time = None
        end_time = None
        if start_time_str:
            try:
                start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        if end_time_str:
            try:
                end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        exam = Exam.objects.create(
            name=(name or classroom.name), 
            classroom=classroom, 
            num_questions=numq, 
            created_by=u, 
            source_exam=src,
            duration=duration,
            start_time=start_time,
            end_time=end_time
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

        return redirect('exams_list')

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

@method_decorator(login_required, name="dispatch")
class ExamTakeView(TemplateView):
    template_name = "accounts/exam_take.html"

    def dispatch(self, request, *args, **kwargs):
        u = request.user
        is_student = (getattr(getattr(u, 'role', None), 'code', '') == 'student')
        if not is_student:
            return redirect('profile')

        exam_id = kwargs.get('exam_id')
        try:
            exam = Exam.objects.get(pk=exam_id)
        except Exam.DoesNotExist:
            return redirect('exams_list')

        # Access allowed if student is a member of the exam or has an assignment
        has_membership = exam.students.filter(pk=u.pk).exists()
        has_assignment = ExamAssignment.objects.filter(exam=exam, student=u).exists()
        if not (has_membership or has_assignment):
            return redirect('exams_list')

        # Check if exam has started
        if exam.start_time and timezone.now() < exam.start_time:
             # You might want to show a specific error page or message
             # For now, redirecting back to list is safest as the list will show the timer
             return redirect('exams_list')

        self.exam = exam
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        exam = getattr(self, 'exam', None)
        if not exam:
            return ctx

        # Prefer questions from assignment. For derived exams, fetch questions from source_exam.
        assignment = ExamAssignment.objects.filter(exam=exam, student=self.request.user).first()
        if exam.source_exam_id:
            base_qs = exam.source_exam.questions
        else:
            base_qs = exam.questions

        if assignment and assignment.selected_question_ids:
            qs = base_qs.filter(id__in=assignment.selected_question_ids).order_by('created_at')
        else:
            qs = base_qs.order_by('created_at')
        ctx['exam'] = exam
        ctx['questions'] = qs
        return ctx

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

@method_decorator(login_required, name="dispatch")
class ExamSubmitView(View):
    def post(self, request, exam_id):
        u = request.user
        try:
            exam = Exam.objects.get(pk=exam_id)
        except Exam.DoesNotExist:
            return redirect('exams_list')

        # Check assignment
        try:
            assignment = ExamAssignment.objects.get(exam=exam, student=u)
        except ExamAssignment.DoesNotExist:
            return redirect('exams_list')

        # Get questions
        if exam.source_exam_id:
            base_qs = exam.source_exam.questions
        else:
            base_qs = exam.questions
        
        if assignment.selected_question_ids:
            questions = base_qs.filter(id__in=assignment.selected_question_ids).order_by('created_at')
        else:
            questions = base_qs.order_by('created_at')

        student_answers = {}
        correct_count = 0
        total_questions = 0

        for q in questions:
            total_questions += 1
            # Form field name: q{id}
            ans = request.POST.get(f'q{q.id}')
            
            if q.kind == 'mcq':
                if ans is not None:
                    try:
                        selected_idx = int(ans)
                        student_answers[str(q.id)] = selected_idx
                        if q.correct_index is not None and selected_idx == q.correct_index:
                            correct_count += 1
                    except ValueError:
                        pass # Invalid input
            else:
                # Descriptive
                if ans:
                    student_answers[str(q.id)] = ans

        if total_questions > 0:
            score = (correct_count / total_questions) * 100
        else:
            score = 0

        assignment.score = score
        assignment.student_answers = student_answers
        assignment.completed_at = timezone.now()
        assignment.save()

        return redirect('exam_result', exam_id=exam.id)


@method_decorator(login_required, name="dispatch")
class ExamResultView(TemplateView):
    template_name = "accounts/exam_result.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        exam_id = kwargs.get('exam_id')
        try:
            exam = Exam.objects.get(pk=exam_id)
        except Exam.DoesNotExist:
            return ctx
        
        try:
            assignment = ExamAssignment.objects.get(exam=exam, student=u)
        except ExamAssignment.DoesNotExist:
            return ctx

        # Re-fetch questions to display details
        if exam.source_exam_id:
            base_qs = exam.source_exam.questions
        else:
            base_qs = exam.questions
        
        if assignment.selected_question_ids:
            qs_list = base_qs.filter(id__in=assignment.selected_question_ids).order_by('created_at')
        else:
            qs_list = base_qs.order_by('created_at')

        # Prepare detailed results
        results = []
        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0
        total_questions = 0
        
        answers = assignment.student_answers or {}

        for q in qs_list:
            total_questions += 1
            user_ans = answers.get(str(q.id))
            is_correct = False
            
            if q.kind == 'mcq':
                if user_ans is not None:
                    try:
                        user_ans = int(user_ans)
                    except:
                        pass
                
                    if q.correct_index is not None and user_ans == q.correct_index:
                        is_correct = True
                        correct_count += 1
                    else:
                        incorrect_count += 1
                else:
                    unanswered_count += 1
            else:
                # For non-MCQ, if answer exists but logic not defined, treat as answered
                if user_ans:
                    # We don't increment correct_count unless we have logic
                    incorrect_count += 1 
                else:
                    unanswered_count += 1
            
            results.append({
                'question': q,
                'user_answer': user_ans,
                'is_correct': is_correct,
                'correct_index': q.correct_index,
                'options': q.options
            })

        ctx['exam'] = exam
        ctx['score_percent'] = assignment.score
        ctx['correct_count'] = correct_count
        ctx['incorrect_count'] = incorrect_count
        ctx['unanswered_count'] = unanswered_count
        ctx['total_questions'] = total_questions
        ctx['results'] = results

        # Class Statistics
        all_assignments = ExamAssignment.objects.filter(exam=exam, completed_at__isnull=False)
        scores = [a.score for a in all_assignments if a.score is not None]
        class_avg = sum(scores) / len(scores) if scores else 0
        class_max = max(scores) if scores else 0
        class_min = min(scores) if scores else 0
        
        ctx['class_avg'] = class_avg
        ctx['class_max'] = class_max
        ctx['class_min'] = class_min
        
        # History Statistics
        history_qs = ExamAssignment.objects.filter(student=u, completed_at__isnull=False).order_by('completed_at')
        history_data = []
        best_assign = None
        worst_assign = None

        if history_qs.exists():
            # We use a helper list to find max/min easily
            # Filter out None scores just in case
            valid_assignments = [h for h in history_qs if h.score is not None]
            if valid_assignments:
                best_assign = max(valid_assignments, key=lambda x: x.score)
                worst_assign = min(valid_assignments, key=lambda x: x.score)

        for h in history_qs:
            history_data.append({
                'exam_name': h.exam.name,
                'score': h.score if h.score is not None else 0,
                'date': h.completed_at.strftime('%Y-%m-%d')
            })
        
        ctx['history_data'] = history_data
        ctx['best_exam'] = best_assign
        ctx['worst_exam'] = worst_assign

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
def admin_exam_list_view(request):
    u = request.user
    is_admin = (getattr(getattr(u, 'role', None), 'code', '') == 'admin')
    if not is_admin:
        return redirect('profile')
    
    from django.utils import timezone
    now = timezone.now()
    
    exams = Exam.objects.select_related('created_by').all().order_by('-created_at')
    
    total_count = exams.count()
    completed_count = 0
    not_completed_count = 0
    
    exams_data = []
    
    for e in exams:
        is_completed = False
        if e.end_time and e.end_time < now:
            is_completed = True
        
        if is_completed:
            completed_count += 1
        else:
            not_completed_count += 1
            
        exams_data.append({
            'obj': e,
            'is_completed': is_completed,
            'instructor_name': f"{e.created_by.first_name} {e.created_by.last_name}" if e.created_by else "-",
            'student_count': e.students.count()
        })
        
    context = {
        'total_count': total_count,
        'completed_count': completed_count,
        'not_completed_count': not_completed_count,
        'exams': exams_data
    }
    return render(request, 'accounts/admin_exam_list.html', context)

@login_required
def admin_exam_edit_view(request, pk):
    u = request.user
    is_admin = (getattr(getattr(u, 'role', None), 'code', '') == 'admin')
    if not is_admin:
        return redirect('profile')
        
    from django.shortcuts import get_object_or_404
    exam = get_object_or_404(Exam, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')
        duration = request.POST.get('duration')
        
        if name:
            exam.name = name
        
        from datetime import datetime
        if start_time_str:
            try:
                exam.start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        else:
            exam.start_time = None
            
        if end_time_str:
            try:
                exam.end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        else:
            exam.end_time = None
            
        if duration:
            try:
                exam.duration = int(duration)
            except ValueError:
                pass
        
        exam.save()
        
        selected_student_ids = request.POST.getlist('student_ids')
        students = User.objects.filter(pk__in=selected_student_ids)
        exam.students.set(students)
        
        # Sync assignments
        current_students = set(exam.students.values_list('id', flat=True))
        for s in students:
            ExamAssignment.objects.get_or_create(exam=exam, student=s)
            
        # Optional: remove assignments for removed students
        ExamAssignment.objects.filter(exam=exam).exclude(student__in=students).delete()
        
        return redirect('admin_exam_list')
    
    all_students = User.objects.filter(role__code='student')
    exam_student_ids = set(exam.students.values_list('id', flat=True))
    
    return render(request, 'accounts/admin_exam_edit.html', {
        'exam': exam,
        'all_students': all_students,
        'exam_student_ids': exam_student_ids
    })
@login_required
def admin_exam_report_view(request, exam_id):
    u = request.user
    is_admin = (getattr(getattr(u, 'role', None), 'code', '') == 'admin')
    if not is_admin:
        return JsonResponse({'error': 'forbidden'}, status=403)
        
    from django.shortcuts import get_object_or_404
    exam = get_object_or_404(Exam, pk=exam_id)
    
    assignments = ExamAssignment.objects.filter(exam=exam, completed_at__isnull=False).select_related('student').order_by('-score')
    
    results = []
    rank = 1
    for a in assignments:
        score_percent = a.score if a.score is not None else 0
        # Assuming max score is 20 for display purposes as per screenshot "18/20"
        # If score is percent (0-100), then score/5 is out of 20.
        score_20 = (score_percent / 100) * 20
        
        results.append({
            'rank': rank,
            'student_name': f"{a.student.first_name} {a.student.last_name}",
            'score_percent': round(score_percent, 1),
            'score_20': round(score_20, 2)
        })
        rank += 1
        
    return render(request, 'accounts/admin_exam_report_partial.html', {
        'exam': exam,
        'results': results
    })

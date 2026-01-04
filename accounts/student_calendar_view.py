from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from .models import Exam, ExamAssignment

@login_required
def student_calendar_view(request):
    u = request.user
    is_student = (getattr(getattr(u, 'role', None), 'code', '') == 'student')
    if not is_student:
        return render(request, '403.html', status=403)

    # Get exams assigned to student
    assignments = ExamAssignment.objects.filter(student=u).select_related('exam')
    
    events = []
    now = timezone.now()
    
    for asm in assignments:
        exam = asm.exam
        if not exam.start_time:
            continue
            
        if exam.end_time and exam.end_time < now:
            status = 'finished'
            color = '#ef4444' # Red
        elif exam.start_time > now:
            status = 'pending'
            color = '#22c55e' # Green
        else:
            status = 'active'
            color = '#3b82f6' # Blue
            
        events.append({
            'title': exam.name,
            'start': exam.start_time.isoformat(),
            'color': color,
            'status': status,
            'time': exam.start_time.strftime('%H:%M'),
            'url': f'/exams/{exam.id}/start/' if status == 'active' else '#'
        })
        
    return render(request, 'accounts/student_calendar.html', {
        'events': events
    })

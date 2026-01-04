from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from .models import Exam

@login_required
def instructor_calendar_view(request):
    u = request.user
    # Ensure only instructors can view this
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return render(request, '403.html', status=403)

    # Get all exams created by this instructor
    exams = Exam.objects.filter(created_by=u).order_by('start_time')
    
    events = []
    now = timezone.now()
    
    for exam in exams:
        if not exam.start_time:
            continue
            
        # Determine status
        if exam.end_time and exam.end_time < now:
            status = 'finished' # Red
            color = '#ef4444'
        elif exam.start_time > now:
            status = 'pending' # Green
            color = '#22c55e'
        else:
            # Active
            status = 'active' # Blue/Green
            color = '#3b82f6'
            
        # Use Gregorian ISO format for FullCalendar (it handles localization)
        # start_time is timezone aware, isoformat() works well
        
        events.append({
            'title': exam.name,
            'start': exam.start_time.isoformat(),
            'color': color,
            'status': status,
            'time': exam.start_time.strftime('%H:%M')
        })
        
    return render(request, 'accounts/instructor_calendar.html', {
        'events': events
    })

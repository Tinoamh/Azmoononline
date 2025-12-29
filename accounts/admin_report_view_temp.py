from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from .models import Exam, ExamAssignment

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

@login_required
def instructor_exam_report_view(request, exam_id):
    u = request.user
    is_instructor = (getattr(getattr(u, 'role', None), 'code', '') == 'instructor')
    if not is_instructor:
        return redirect('dashboard')
        
    from django.shortcuts import get_object_or_404
    exam = get_object_or_404(Exam, pk=exam_id, created_by=u)
    
    assignments = ExamAssignment.objects.filter(exam=exam, completed_at__isnull=False).select_related('student').order_by('-score')
    
    # Calculate stats
    scores = [a.score for a in assignments if a.score is not None]
    
    # Convert scores to 20 scale for display if they are percent (assuming they are 0-100)
    # The system stores percentage in 'score'.
    
    def to_20(val):
        return (val / 100) * 20 if val is not None else 0

    avg_score = sum(scores) / len(scores) if scores else 0
    avg_score_20 = to_20(avg_score)
    
    students_data = []
    
    for a in assignments:
        score_percent = a.score if a.score is not None else 0
        score_20 = to_20(score_percent)
        
        s_data = {
            'name': a.student.first_name,
            'family': a.student.last_name,
            'score_20': round(score_20, 2),
            'obj': a.student
        }
        students_data.append(s_data)
    
    # Separate lists based on average
    above_avg = [x for x in students_data if x['score_20'] >= avg_score_20]
    below_avg = [x for x in students_data if x['score_20'] < avg_score_20]
    
    # Chart data
    chart_labels = [f"{x['name']} {x['family']}" for x in students_data]
    chart_data = [x['score_20'] for x in students_data]
    
    context = {
        'exam': exam,
        'students': students_data,
        'above_avg': above_avg,
        'below_avg': below_avg,
        'avg_score_20': round(avg_score_20, 2),
        'chart_labels': chart_labels,
        'chart_data': chart_data
    }
    return render(request, 'accounts/instructor_exam_report.html', context)

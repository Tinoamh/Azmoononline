from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Exam, ExamAssignment
from collections import defaultdict
from statistics import median, pstdev
from datetime import datetime

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
    participants_count = len(scores)
    max_score_20 = to_20(max(scores) if scores else 0)
    min_score_20 = to_20(min(scores) if scores else 0)
    median_20 = to_20(median(scores)) if scores else 0
    std_20 = to_20(pstdev(scores)) if len(scores) > 1 else 0
    
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

    # Buckets for pie chart (score ranges on 20-scale)
    buckets = {
        'ضعیف (<8)': 0,
        'متوسط (8-12)': 0,
        'خوب (12-16)': 0,
        'عالی (>=16)': 0
    }
    for v in chart_data:
        if v < 8: buckets['ضعیف (<8)'] += 1
        elif v < 12: buckets['متوسط (8-12)'] += 1
        elif v < 16: buckets['خوب (12-16)'] += 1
        else: buckets['عالی (>=16)'] += 1
    pie_labels = list(buckets.keys())
    pie_data = list(buckets.values())

    # Monthly trend of average scores (by completed_at)
    monthly = defaultdict(list)
    for a in assignments:
        if a.completed_at:
            key = a.completed_at.strftime('%Y-%m')
            monthly[key].append(to_20(a.score or 0))
    trend_labels = sorted(monthly.keys())
    trend_data = [round(sum(vals)/len(vals), 2) for key, vals in sorted(monthly.items())]

    # Radar metrics (normalized to 20)
    # Stability: 20 - std_20, Coverage: number of participants scaled, Peak: max, Median
    stability = round(max(0, 20 - std_20), 2)
    coverage = round(min(20, (participants_count / 30) * 20), 2)  # assume class size ~30 for scaling
    radar_labels = ['میانگین', 'میانه', 'پیک', 'ثبات', 'پوشش']
    radar_data = [
        round(avg_score_20,2),
        round(median_20,2),
        round(max_score_20,2),
        stability,
        coverage
    ]
    
    context = {
        'exam': exam,
        'students': students_data,
        'above_avg': above_avg,
        'below_avg': below_avg,
        'avg_score_20': round(avg_score_20, 2),
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        # kpis
        'participants_count': participants_count,
        'max_score_20': round(max_score_20,2),
        'min_score_20': round(min_score_20,2),
        'median_20': round(median_20,2),
        # pie
        'pie_labels': pie_labels,
        'pie_data': pie_data,
        # trend
        'trend_labels': trend_labels,
        'trend_data': trend_data,
        # radar
        'radar_labels': radar_labels,
        'radar_data': radar_data,
    }
    return render(request, 'accounts/instructor_exam_report.html', context)

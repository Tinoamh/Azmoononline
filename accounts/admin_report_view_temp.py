from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from .models import Exam, ExamAssignment
from collections import defaultdict
from statistics import median, pstdev

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
    scores = []
    for a in assignments:
        score_percent = a.score if a.score is not None else 0
        score_20 = (score_percent / 100) * 20
        if a.score is not None:
            scores.append(a.score)
        
        results.append({
            'rank': rank,
            'student_name': f"{a.student.first_name} {a.student.last_name}",
            'score_percent': round(score_percent, 1),
            'score_20': round(score_20, 2)
        })
        rank += 1
    
    # KPIs and analytics
    def to_20(val):
        return (val / 100) * 20 if val is not None else 0
    avg_score = sum(scores) / len(scores) if scores else 0
    avg_score_20 = to_20(avg_score)
    participants_count = len(scores)
    max_score_20 = to_20(max(scores) if scores else 0)
    min_score_20 = to_20(min(scores) if scores else 0)
    median_20 = to_20(median(scores)) if scores else 0
    std_20 = to_20(pstdev(scores)) if len(scores) > 1 else 0
    chart_labels = [r['student_name'] for r in results]
    chart_data = [r['score_20'] for r in results]

    buckets = {'ضعیف (<8)': 0, 'متوسط (8-12)': 0, 'خوب (12-16)': 0, 'عالی (>=16)': 0}
    for v in chart_data:
        if v < 8: buckets['ضعیف (<8)'] += 1
        elif v < 12: buckets['متوسط (8-12)'] += 1
        elif v < 16: buckets['خوب (12-16)'] += 1
        else: buckets['عالی (>=16)'] += 1
    pie_labels = list(buckets.keys())
    pie_data = list(buckets.values())

    monthly = defaultdict(list)
    for a in assignments:
        if a.completed_at:
            key = a.completed_at.strftime('%Y-%m')
            monthly[key].append(to_20(a.score or 0))
    trend_labels = sorted(monthly.keys())
    trend_data = [round(sum(vals)/len(vals), 2) for key, vals in sorted(monthly.items())]

    stability = round(max(0, 20 - std_20), 2)
    coverage = round(min(20, (participants_count / 30) * 20), 2)
    radar_labels = ['میانگین', 'میانه', 'پیک', 'ثبات', 'پوشش']
    radar_data = [
        round(avg_score_20,2),
        round(median_20,2),
        round(max_score_20,2),
        stability,
        coverage
    ]

    return render(request, 'accounts/admin_exam_report_partial.html', {
        'exam': exam,
        'results': results,
        'avg_score_20': round(avg_score_20, 2),
        'participants_count': participants_count,
        'max_score_20': round(max_score_20,2),
        'min_score_20': round(min_score_20,2),
        'median_20': round(median_20,2),
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'pie_labels': pie_labels,
        'pie_data': pie_data,
        'trend_labels': trend_labels,
        'trend_data': trend_data,
        'radar_labels': radar_labels,
        'radar_data': radar_data,
    })

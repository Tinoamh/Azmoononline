
@login_required
def admin_exam_list_view(request):
    u = request.user
    is_admin = (getattr(getattr(u, 'role', None), 'code', '') == 'admin')
    if not is_admin:
        return redirect('profile')
    
    from django.utils import timezone
    now = timezone.now()
    
    # We want exams that are actually assigned/running, so usually created by instructors.
    # But admin might want to see ALL exams.
    # Filter exams that are "instances" (have classroom) or "definitions"?
    # The prompt implies managing exams like "Math Exam - Chapter 1".
    # Let's list all exams that are not just source banks (so source_exam is NOT null? Or shuffle is True? Or have students?)
    # Usually "Banks" are source_exam=None. "Instances" are source_exam != None or created directly.
    # Let's show all for now, or filter based on context. 
    # The screenshot shows "Instructor Name", so these are likely exams created by instructors.
    
    exams = Exam.objects.select_related('created_by').all().order_by('-created_at')
    
    # Filter out "Question Banks" if that's the convention. 
    # In ExamDefineView, banks are `source_exam__isnull=True`.
    # So "Exams" are likely `source_exam__isnull=False` OR exams that have students assigned.
    # Let's just list everything for now to be safe, or filter source_exam__isnull=False.
    # Actually, in the code, `ExamDefineView` creates an exam with `source_exam=src` (if from bank) or `None` (if new?).
    # Wait, `ExamDefineView` creates `source_exam=src` if `src_id` is passed.
    # If no source (new exam from scratch?), `src` is None.
    # But usually exams have students. Banks don't have students (or shouldn't).
    # So filter by `students__isnull=False` distinct?
    
    # Let's stick to: All exams created by instructors (role='instructor')?
    # Or just all exams.
    
    total_count = exams.count()
    completed_count = 0
    not_completed_count = 0
    
    exams_data = []
    
    for e in exams:
        # Determine status
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
        
        # Update students
        # We need a list of all students to show in the UI, and then set the selected ones.
        # But if the list is huge, this is bad. For now assuming small scale.
        selected_student_ids = request.POST.getlist('student_ids')
        students = User.objects.filter(pk__in=selected_student_ids)
        exam.students.set(students)
        
        # Also need to ensure ExamAssignments exist/are removed?
        # If we remove a student from exam, should we delete their assignment?
        # Current logic in ExamDefineView creates assignments.
        # We should sync assignments.
        current_students = set(exam.students.values_list('id', flat=True))
        
        # Create missing assignments
        for s in students:
            ExamAssignment.objects.get_or_create(exam=exam, student=s)
            
        # Remove extra assignments (optional, but good for cleanup)
        ExamAssignment.objects.filter(exam=exam).exclude(student__in=students).delete()
        
        return redirect('admin_exam_list')
    
    all_students = User.objects.filter(role__code='student')
    exam_student_ids = set(exam.students.values_list('id', flat=True))
    
    return render(request, 'accounts/admin_exam_edit.html', {
        'exam': exam,
        'all_students': all_students,
        'exam_student_ids': exam_student_ids
    })

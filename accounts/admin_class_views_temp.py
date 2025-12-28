@login_required
def admin_class_list_view(request):
    u = request.user
    is_admin = (getattr(getattr(u, 'role', None), 'code', '') == 'admin')
    if not is_admin:
        return redirect('profile')
        
    classes = Classroom.objects.select_related('instructor').annotate(student_count=models.Count('students')).order_by('-id')
    
    return render(request, 'accounts/admin_class_list.html', {
        'classes': classes
    })

@login_required
def admin_class_edit_view(request, pk=None):
    u = request.user
    is_admin = (getattr(getattr(u, 'role', None), 'code', '') == 'admin')
    if not is_admin:
        return redirect('profile')
    
    if pk:
        from django.shortcuts import get_object_or_404
        classroom = get_object_or_404(Classroom, pk=pk)
    else:
        classroom = Classroom()
        
    if request.method == 'POST':
        name = request.POST.get('name')
        instructor_id = request.POST.get('instructor_id')
        student_ids = request.POST.getlist('student_ids')
        
        if name:
            classroom.name = name
        
        if instructor_id:
            try:
                instructor = User.objects.get(pk=instructor_id, role__code='instructor')
                classroom.instructor = instructor
            except User.DoesNotExist:
                pass
        elif not classroom.instructor_id:
            # If creating new and no instructor selected, maybe default to admin or require it?
            # Assuming required, but for now let's skip if missing to avoid crash
            pass
            
        if not classroom.instructor_id:
             # Basic validation failure
             pass 
        else:
            classroom.save()
            students = User.objects.filter(pk__in=student_ids, role__code='student')
            classroom.students.set(students)
            return redirect('admin_class_list')

    # Context data
    instructors = User.objects.filter(role__code='instructor')
    all_students = User.objects.filter(role__code='student')
    
    current_student_ids = []
    if classroom.pk:
        current_student_ids = set(classroom.students.values_list('id', flat=True))
        
    return render(request, 'accounts/admin_class_edit.html', {
        'classroom': classroom,
        'instructors': instructors,
        'all_students': all_students,
        'current_student_ids': current_student_ids
    })

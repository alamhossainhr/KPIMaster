from .models import AssignedTask, DailyWork

def pending_notifications(request):
    if not request.user.is_authenticated:
        return {}
    
    current_employee = getattr(request.user, 'employee_profile', None)
    if not current_employee:
        return {}

    # Pending assigned tasks for this employee (ordered by assigned_date)
    my_pending_tasks = AssignedTask.objects.filter(
        employee=current_employee,
        status__in=['Assigned', 'In Progress']
    ).select_related('assigned_by').order_by('-assigned_date')

    # Pending approvals for Supervisors / Dept Heads
    supervisor_approvals_count = DailyWork.objects.filter(
        employee__supervisor=current_employee,
        status='Submitted'
    ).count()

    return {
        'my_pending_tasks': my_pending_tasks,
        'pending_tasks_count': my_pending_tasks.count(),
        'supervisor_approvals_count': supervisor_approvals_count,
    }
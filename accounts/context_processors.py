def user_role_context(request):
    """Provides user_role and role helper flags across all templates."""
    if not request.user.is_authenticated:
        return {'user_role': 'ANONYMOUS', 'is_manager_or_above': False, 'is_supervisor_or_above': False}

    if request.user.is_superuser:
        role = 'SUPER_ADMIN'
    elif hasattr(request.user, 'role_profile'):
        role = request.user.role_profile.role
    else:
        role = 'EMPLOYEE'

    return {
        'user_role': role,
        'is_admin': role in ['SUPER_ADMIN', 'HR_ADMIN'],
        'is_dept_head': role == 'DEPT_HEAD',
        'is_supervisor': role == 'SUPERVISOR',
        'is_manager_or_above': role in ['SUPER_ADMIN', 'HR_ADMIN', 'DEPT_HEAD'],
        'is_supervisor_or_above': role in ['SUPER_ADMIN', 'HR_ADMIN', 'DEPT_HEAD', 'SUPERVISOR'],
    }
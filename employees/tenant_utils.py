from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import CompanyUnit, Employee

def get_tenant_context(request):
    """
    Returns (user, current_employee, user_unit, is_super)
    """
    user = request.user
    if user.is_superuser:
        return user, None, None, True

    # Retrieve employee profile
    emp = getattr(user, 'employee_profile', None) or getattr(user, 'employee', None)
    if not emp:
        emp = Employee.objects.filter(user=user).select_related('unit').first()

    unit = getattr(emp, 'unit', None) if emp else None
    return user, emp, unit, False


def scope_queryset_to_unit(queryset, request, unit_field='unit'):
    """
    Restricts a QuerySet to the logged-in user's assigned CompanyUnit.
    Super Admins bypass filtering.
    """
    user, emp, unit, is_super = get_tenant_context(request)
    if is_super:
        return queryset

    if not unit:
        return queryset.none()

    return queryset.filter(**{unit_field: unit})


def enforce_unit_integrity(obj, request, unit_field='unit'):
    """
    Ensures that an object being viewed, edited, or saved belongs to the user's unit.
    """
    user, emp, unit, is_super = get_tenant_context(request)
    if is_super:
        return

    obj_unit = getattr(obj, unit_field, None)
    if not obj_unit or not unit or obj_unit.id != unit.id:
        raise PermissionDenied("Access Denied: You cannot view or modify data outside your assigned company unit.")
import calendar
from datetime import date, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Avg, Sum, Count
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from kpi.utils import ensure_monthly_cycle_and_summary

from .forms import FloorProductionKPIForm
from django.http import JsonResponse
from .models import (
    CompanyUnit, Department, Section, SubSection, Designation, 
    Floor, JobGrade, JobLocation, Employee, UserProfile,
    DailyFloorAttendance, MonthlyMigration, FloorDisciplinaryAction
)
from .forms import (
    EmployeeForm, EmployeeEditForm, ResetEmployeePasswordForm,
    DailyFloorAttendanceForm, MonthlyMigrationForm, FloorDisciplinaryActionForm
)
from .models import MonthlyFloorProductionSummary, FloorProductionKPI
from .tenant_utils import get_tenant_context, scope_queryset_to_unit, enforce_unit_integrity

def get_current_employee(user):
    if hasattr(user, 'employee_profile'):
        return user.employee_profile
    if hasattr(user, 'employee'):
        return user.employee
    return Employee.objects.filter(user=user).first()


def get_user_role(user):
    if user.is_superuser:
        return 'SUPER_ADMIN'
    if hasattr(user, 'role_profile'):
        return user.role_profile.role
    return 'EMPLOYEE'


def get_user_unit(user):
    emp = get_current_employee(user)
    if emp:
        return getattr(emp, 'unit', None)
    return None


@login_required
def employee_list(request):
    user = request.user
    role = get_user_role(user)
    current_employee = get_current_employee(user)

    # 1. Base query with company unit joined
    base_qs = Employee.objects.select_related('department', 'designation', 'supervisor', 'user', 'unit')
    
    # 2. Apply Tenant Isolation (Data Wall)
    # Super Admin sees all; all other users are strictly restricted to their own factory unit
    if not user.is_superuser:
        user_unit = getattr(current_employee, 'unit', None) if current_employee else None
        if not user_unit:
            base_qs = base_qs.none()
        else:
            base_qs = base_qs.filter(unit=user_unit)

    # 3. Role-based scoping within the company unit
    if role in ['SUPER_ADMIN', 'HR_ADMIN']:
        employees = base_qs.all()
        departments = Department.objects.filter(is_active=True)
        # Scope departments dropdown to the user's unit for non-superusers
        if not user.is_superuser and current_employee and current_employee.unit:
            departments = departments.filter(unit=current_employee.unit)
    elif role == 'DEPT_HEAD' and current_employee:
        employees = base_qs.filter(department=current_employee.department)
        departments = Department.objects.filter(id=current_employee.department_id)
    elif role == 'SUPERVISOR' and current_employee:
        employees = base_qs.filter(Q(supervisor=current_employee) | Q(id=current_employee.id))
        departments = Department.objects.filter(id=current_employee.department_id)
    elif current_employee:
        employees = base_qs.filter(id=current_employee.id)
        departments = Department.objects.filter(id=current_employee.department_id)
    else:
        employees = base_qs.none()
        departments = Department.objects.none()

    # 4. Search and department filters
    query = request.GET.get('q', '').strip()
    dept_id = request.GET.get('department')

    if query:
        employees = employees.filter(
            Q(employee_code__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(mobile__icontains=query) |
            Q(email__icontains=query)
        )
    if dept_id:
        employees = employees.filter(department_id=dept_id)

    can_add = role in ['SUPER_ADMIN', 'HR_ADMIN']

    return render(request, 'employees/employee_list.html', {
        'employees': employees,
        'departments': departments,
        'query': query,
        'selected_dept': dept_id,
        'can_add_employee': can_add,
        'user_role': role,
    })


@login_required
def employee_detail(request, emp_id):
    user = request.user
    role = get_user_role(user)
    current_employee = get_current_employee(user)

    employee = get_object_or_404(
        Employee.objects.select_related(
            'department', 'section', 'sub_section', 'designation', 
            'floor', 'job_grade', 'job_location', 'supervisor', 'department_head', 'user'
        ), 
        id=emp_id
    )

    if role not in ['SUPER_ADMIN', 'HR_ADMIN']:
        if role == 'DEPT_HEAD' and current_employee:
            if employee.department_id != current_employee.department_id:
                raise PermissionDenied("You can only view profiles within your department.")
        elif role == 'SUPERVISOR' and current_employee:
            if employee.supervisor_id != current_employee.id and employee.id != current_employee.id:
                raise PermissionDenied("You can only view profiles of your direct subordinates.")
        elif current_employee and employee.id != current_employee.id:
            raise PermissionDenied("You can only view your own profile.")

    subordinates = employee.subordinates.filter(is_active=True)
    can_edit = role in ['SUPER_ADMIN', 'HR_ADMIN', 'DEPT_HEAD'] or (current_employee and current_employee.id == employee.id)

    return render(request, 'employees/employee_detail.html', {
        'employee': employee,
        'subordinates': subordinates,
        'can_edit': can_edit,
        'user_role': role,
    })


@login_required
def employee_edit(request, emp_id):
    employee = get_object_or_404(
        Employee.objects.select_related('user', 'department', 'unit', 'designation'), 
        id=emp_id
    )
    
    current_role = 'EMPLOYEE'
    if employee.user and hasattr(employee.user, 'role_profile'):
        current_role = employee.user.role_profile.role

    if request.method == 'POST':
        form = EmployeeEditForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            with transaction.atomic():
                emp = form.save()
                new_role = form.cleaned_data.get('system_role') or request.POST.get('system_role') or current_role or 'EMPLOYEE'
                
                if emp.user:
                    UserProfile.objects.update_or_create(
                        user=emp.user,
                        defaults={'role': new_role}
                    )

            messages.success(request, f"Employee '{emp.full_name}' updated successfully.")
            return redirect('employee_list')
        else:
            for field, err_list in form.errors.items():
                for err in err_list:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {err}")
    else:
        form = EmployeeEditForm(instance=employee, initial={'system_role': current_role})

    return render(request, 'employees/employee_edit.html', {
        'form': form,
        'employee': employee,
        'current_role': current_role,
        'title': f'Edit Employee: {employee.full_name}'
    })


@login_required
def employee_change_password(request, emp_id):
    user = request.user
    role = get_user_role(user)
    current_employee = get_current_employee(user)

    employee = get_object_or_404(Employee, id=emp_id)
    if not employee.user:
        messages.error(request, f"Employee {employee.employee_code} has no associated login user account.")
        return redirect('employee_detail', emp_id=employee.id)

    if role not in ['SUPER_ADMIN', 'HR_ADMIN']:
        if current_employee and current_employee.id != employee.id:
            raise PermissionDenied

    if request.method == 'POST':
        form = ResetEmployeePasswordForm(request.POST)
        if form.is_valid():
            new_pass = form.cleaned_data['new_password']
            employee.user.set_password(new_pass)
            employee.user.save()
            messages.success(request, f"Password for {employee.full_name} updated successfully.")
            return redirect('employee_detail', emp_id=employee.id)
    else:
        form = ResetEmployeePasswordForm()

    return render(request, 'employees/employee_change_password.html', {
        'form': form,
        'employee': employee,
    })


@login_required
def employee_create(request):
    role = get_user_role(request.user)
    if role not in ['SUPER_ADMIN', 'HR_ADMIN']:
        raise PermissionDenied("Only HR and Super Admins can add new employees.")

    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                employee = form.save(commit=False)

                create_user = form.cleaned_data.get('create_user_account')
                username = form.cleaned_data.get('username') or employee.employee_code
                password = form.cleaned_data.get('password')
                role_selected = form.cleaned_data.get('role', 'EMPLOYEE')

                if create_user:
                    if not password:
                        password = employee.employee_code

                    if User.objects.filter(username=username).exists():
                        messages.error(request, f"Username '{username}' already exists.")
                        return render(request, 'employees/employee_form.html', {'form': form, 'title': 'Add New Employee'})

                    user = User.objects.create_user(
                        username=username,
                        password=password,
                        first_name=employee.first_name,
                        last_name=employee.last_name,
                        email=employee.email or ''
                    )
                    
                    employee.user = user
                    employee.save()

                    UserProfile.objects.create(
                        user=user,
                        employee=employee,
                        role=role_selected
                    )
                else:
                    employee.save()

                messages.success(request, f"Employee '{employee.full_name}' ({employee.employee_code}) created successfully.")
                return redirect('employee_list')
    else:
        form = EmployeeForm(initial={'is_active': True, 'create_user_account': True})

    return render(request, 'employees/employee_form.html', {'form': form, 'title': 'Add New Employee'})


@login_required
def org_structure_manage(request):
    role = get_user_role(request.user)
    if role not in ['SUPER_ADMIN', 'HR_ADMIN', 'DEPT_HEAD']:
        raise PermissionDenied("You do not have permission to manage organization structure.")

    active_tab = request.GET.get('tab', 'factories' if role in ['SUPER_ADMIN', 'HR_ADMIN'] else 'departments')
    user_unit = get_user_unit(request.user)

    selected_unit_id = request.GET.get('unit_id')
    
    try:
        if role in ['SUPER_ADMIN', 'HR_ADMIN']:
            units = CompanyUnit.objects.all()
            selected_unit = CompanyUnit.objects.filter(id=selected_unit_id).first() if selected_unit_id else units.first()
        else:
            units = CompanyUnit.objects.filter(id=user_unit.id) if user_unit else CompanyUnit.objects.none()
            selected_unit = user_unit
    except Exception:
        units = []
        selected_unit = None

    if selected_unit and hasattr(Department, 'unit'):
        departments = Department.objects.filter(unit=selected_unit).prefetch_related('sections__sub_sections')
        sections = Section.objects.filter(department__unit=selected_unit).select_related('department')
        sub_sections = SubSection.objects.filter(section__department__unit=selected_unit).select_related('section__department')
    else:
        departments = Department.objects.prefetch_related('sections__sub_sections').all()
        sections = Section.objects.select_related('department').all()
        sub_sections = SubSection.objects.select_related('section__department').all()

    designations = Designation.objects.all()
    floors = Floor.objects.all()
    job_grades = JobGrade.objects.all()
    job_locations = JobLocation.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_unit':
            if role not in ['SUPER_ADMIN', 'HR_ADMIN']:
                raise PermissionDenied("Only Administrators can add factory business units.")
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip().upper()
            address = request.POST.get('address', '').strip()

            if name and code:
                unit, created = CompanyUnit.objects.get_or_create(
                    code=code, 
                    defaults={'name': name, 'address': address or None}
                )
                if created:
                    messages.success(request, f"Factory Unit '{name}' ({code}) registered successfully.")
                else:
                    messages.warning(request, f"Factory Unit with code '{code}' already exists.")
            return redirect(f"{reverse('org_structure')}?tab=factories")

        elif action == 'add_department':
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip().upper()
            description = request.POST.get('description', '').strip()
            unit_id = request.POST.get('unit_id') or (selected_unit.id if selected_unit else None)

            if name and code:
                target_unit = CompanyUnit.objects.filter(id=unit_id).first() if unit_id else None
                dept, created = Department.objects.get_or_create(
                    unit=target_unit,
                    code=code,
                    defaults={'name': name, 'description': description or None}
                )
                if created:
                    unit_label = f" for {target_unit.code}" if target_unit else ""
                    messages.success(request, f"Department '{name}' ({code}) saved{unit_label}.")
                else:
                    unit_label = f" in {target_unit.code}" if target_unit else ""
                    messages.warning(request, f"Department '{code}' already exists{unit_label}.")
                    
            return redirect(f"{reverse('org_structure')}?tab=departments&unit_id={unit_id or ''}")

        elif action == 'add_section':
            dept_id = request.POST.get('department_id')
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip().upper()
            description = request.POST.get('description', '').strip()

            if dept_id and name and code:
                dept = get_object_or_404(Department, id=dept_id)
                sec, created = Section.objects.get_or_create(
                    department=dept, 
                    code=code, 
                    defaults={'name': name, 'description': description or None}
                )
                if created:
                    messages.success(request, f"Section '{name}' ({code}) added under {dept.name} [{dept.unit.code if dept.unit else 'Global'}].")
                else:
                    messages.warning(request, f"Section '{code}' already exists under {dept.name}.")
            return redirect(f"{reverse('org_structure')}?tab=sections")

        elif action == 'add_sub_section':
            sec_id = request.POST.get('section_id')
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip().upper()
            description = request.POST.get('description', '').strip()

            if sec_id and name and code:
                section = get_object_or_404(Section, id=sec_id)
                sub, created = SubSection.objects.get_or_create(
                    section=section, 
                    code=code, 
                    defaults={'name': name, 'description': description or None}
                )
                if created:
                    messages.success(request, f"Sub-Section '{name}' ({code}) added under {section.name}.")
                else:
                    messages.warning(request, f"Sub-Section '{code}' already exists under {section.name}.")
            return redirect(f"{reverse('org_structure')}?tab=sub-sections")

        elif action == 'add_designation':
            title = request.POST.get('title', '').strip()
            code = request.POST.get('code', '').strip().upper()
            description = request.POST.get('description', '').strip()

            if title and code:
                desig, created = Designation.objects.get_or_create(
                    code=code, 
                    defaults={'title': title, 'description': description or None}
                )
                if created:
                    messages.success(request, f"Designation '{title}' ({code}) saved.")
                else:
                    messages.warning(request, f"Designation with code '{code}' already exists.")
            return redirect(f"{reverse('org_structure')}?tab=designations")

        elif action == 'add_job_grade':
            name = request.POST.get('name', '').strip()
            level = request.POST.get('level', 1)
            description = request.POST.get('description', '').strip()
            if name:
                grade, created = JobGrade.objects.get_or_create(
                    name=name, 
                    defaults={'level': level, 'description': description or None}
                )
                if created:
                    messages.success(request, f"Job Grade '{name}' saved.")
                else:
                    messages.warning(request, f"Job Grade '{name}' already exists.")
            return redirect(f"{reverse('org_structure')}?tab=designations")

        elif action == 'add_floor':
            name = request.POST.get('name', '').strip()
            building = request.POST.get('building', '').strip()
            description = request.POST.get('description', '').strip()
            unit_id = request.POST.get('unit_id') or (selected_unit.id if selected_unit else None)

            if name:
                target_unit = CompanyUnit.objects.filter(id=unit_id).first() if unit_id else None
                floor, created = Floor.objects.get_or_create(
                    unit=target_unit,
                    name=name,
                    building=building or '',
                    defaults={'description': description or None}
                )
                if created:
                    messages.success(request, f"Floor '{name}' saved.")
                else:
                    messages.warning(request, f"Floor '{name}' already exists for this unit.")
            return redirect(f"{reverse('org_structure')}?tab=floors-locations")

        elif action == 'add_location':
            name = request.POST.get('name', '').strip()
            address = request.POST.get('address', '').strip()
            description = request.POST.get('description', '').strip()
            unit_id = request.POST.get('unit_id') or (selected_unit.id if selected_unit else None)

            if name:
                target_unit = CompanyUnit.objects.filter(id=unit_id).first() if unit_id else None
                JobLocation.objects.create(
                    unit=target_unit,
                    name=name, 
                    address=address or None, 
                    description=description or None
                )
                messages.success(request, f"Job Location '{name}' saved.")
            return redirect(f"{reverse('org_structure')}?tab=floors-locations")

    context = {
        'units': units,
        'selected_unit': selected_unit,
        'departments': departments,
        'sections': sections,
        'sub_sections': sub_sections,
        'designations': designations,
        'floors': floors,
        'job_grades': job_grades,
        'job_locations': job_locations,
        'active_tab': active_tab,
        'user_role': role,
        'is_admin': role in ['SUPER_ADMIN', 'HR_ADMIN'],
    }
    return render(request, 'employees/org_structure.html', context)


# ==========================================
# 1. DAILY FLOOR ATTENDANCE & ABSENTEEISM
# ==========================================
@login_required
def floor_attendance_manage(request):
    user = request.user
    role = get_user_role(user)
    current_employee = get_current_employee(user)
    is_super = user.is_superuser
    is_admin = role in ['SUPER_ADMIN', 'HR_ADMIN']
    is_supervisor = role in ['DEPT_HEAD', 'MANAGER', 'SUPERVISOR']

    has_perm = is_super or is_admin or is_supervisor or (
        current_employee and getattr(current_employee, 'can_manage_attendance', False)
    )
    if not has_perm:
        messages.error(request, "Access denied: You do not have permission to manage Floor Attendance.")
        return redirect('dashboard')

    # 1. Identify Logged-in User's Assigned Factory Unit
    user_unit = getattr(current_employee, 'unit', None) if current_employee else None

    # Block non-superusers who do not have an assigned company unit
    if not is_super and not user_unit:
        messages.error(request, "Access restricted: Your profile is not assigned to any Company Unit.")
        return redirect('dashboard')

    # 2. Scope Unit & Floor dropdowns
    if is_super:
        units = CompanyUnit.objects.filter(is_active=True)
        all_floors = Floor.objects.select_related('unit').order_by('name')
    else:
        units = CompanyUnit.objects.filter(id=user_unit.id)
        all_floors = Floor.objects.filter(unit=user_unit).order_by('name')

    # 3. Handle Form Submission
    if request.method == 'POST':
        form = DailyFloorAttendanceForm(request.POST)
        
        # Lock form choices to the user's unit
        if not is_super:
            form.fields['unit'].queryset = units
            form.fields['floor'].queryset = all_floors

        if form.is_valid():
            record = form.save(commit=False)
            
            # Enforce Data Wall: prevent selecting/tampering with other factory units
            if not is_super:
                record.unit = user_unit
                if record.floor.unit_id != user_unit.id:
                    messages.error(request, "Invalid floor selected for your company.")
                    return redirect('floor_attendance_manage')

            record.recorded_by = current_employee
            record.save()

            ensure_monthly_cycle_and_summary(
                entry_date=record.date, 
                floor=record.floor, 
                employee=record.employee
            )
            messages.success(request, f"Attendance log for {record.floor.name} ({record.date}) saved successfully.")
            return redirect('floor_attendance_manage')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        initial_data = {'date': timezone.now().date()}
        if not is_super and user_unit:
            initial_data['unit'] = user_unit
        form = DailyFloorAttendanceForm(initial=initial_data)

        if not is_super:
            form.fields['unit'].queryset = units
            form.fields['floor'].queryset = all_floors

    # 4. Scope Table Records (Data Wall)
    attendance_records = DailyFloorAttendance.objects.select_related('floor', 'unit', 'recorded_by').order_by('-date', 'floor__name')

    if not is_super:
        # Strictly show only this employee's company unit
        attendance_records = attendance_records.filter(unit=user_unit)

    # 5. Apply User Filter Bar
    filter_date = request.GET.get('filter_date', '').strip()
    filter_floor = request.GET.get('filter_floor', '').strip()

    if filter_date:
        try:
            attendance_records = attendance_records.filter(date=date.fromisoformat(filter_date))
        except ValueError:
            pass

    if filter_floor:
        attendance_records = attendance_records.filter(floor_id=filter_floor)

    return render(request, 'employees/floor_attendance_manage.html', {
        'form': form,
        'attendance_records': attendance_records,
        'units': units,
        'all_floors': all_floors,
        'filter_date': filter_date,
        'filter_floor': filter_floor,
        'is_super': is_super,
        'title': 'Daily Floor Attendance & Absenteeism'
    })


# ==========================================
# 2. MONTHLY MIGRATION & TURNOVER
# ==========================================
@login_required
def monthly_migration_manage(request):
    user = request.user
    role = get_user_role(user)
    current_employee = get_current_employee(user)
    is_super = user.is_superuser
    is_admin = role in ['SUPER_ADMIN', 'HR_ADMIN']
    is_supervisor = role in ['DEPT_HEAD', 'MANAGER', 'SUPERVISOR']

    has_perm = is_super or is_admin or is_supervisor or (
        current_employee and getattr(current_employee, 'can_manage_migration', False)
    )
    if not has_perm:
        messages.error(request, "Access denied: You do not have permission to manage Monthly Migrations.")
        return redirect('dashboard')

    # Identify user's company unit
    user_unit = getattr(current_employee, 'unit', None) if current_employee else None
    if not is_super and not user_unit:
        messages.error(request, "Access restricted: Your profile is not assigned to any Company Unit.")
        return redirect('dashboard')

    # 1. Scope Dropdowns
    if is_super:
        units = CompanyUnit.objects.filter(is_active=True)
        all_floors = Floor.objects.select_related('unit').order_by('name')
    else:
        units = CompanyUnit.objects.filter(id=user_unit.id)
        all_floors = Floor.objects.filter(unit=user_unit).order_by('name')

    # 2. Form Handling
    if request.method == 'POST':
        form = MonthlyMigrationForm(request.POST)
        if not is_super:
            form.fields['unit'].queryset = units
            form.fields['floor'].queryset = all_floors

        if form.is_valid():
            record = form.save(commit=False)
            if not is_super:
                record.unit = user_unit
                if record.floor.unit_id != user_unit.id:
                    messages.error(request, "Invalid floor selected for your company.")
                    return redirect('monthly_migration_manage')

            record.recorded_by = current_employee
            record.save()
            messages.success(request, f"Migration log for {record.floor.name} saved successfully.")
            return redirect('monthly_migration_manage')
        else:
            messages.error(request, "Please correct the form errors.")
    else:
        initial_data = {}
        if not is_super and user_unit:
            initial_data['unit'] = user_unit
        form = MonthlyMigrationForm(initial=initial_data)
        if not is_super:
            form.fields['unit'].queryset = units
            form.fields['floor'].queryset = all_floors

    # 3. Scope QuerySet (Data Wall)
    migrations = MonthlyMigration.objects.select_related('floor', 'unit', 'recorded_by').order_by('-month', 'floor__name')
    if not is_super:
        migrations = migrations.filter(unit=user_unit)

    # 4. Filters
    filter_month = request.GET.get('filter_month', '').strip()
    filter_floor = request.GET.get('filter_floor', '').strip()

    if filter_month:
        try:
            migrations = migrations.filter(month=date.fromisoformat(filter_month))
        except ValueError:
            pass

    if filter_floor:
        migrations = migrations.filter(floor_id=filter_floor)

    # Match whatever your actual template filename is:
    return render(request, 'employees/monthly_migration.html', {
        'form': form,
        'migrations': migrations,
        'units': units,
        'all_floors': all_floors,
        'filter_month': filter_month,
        'filter_floor': filter_floor,
        'is_super': is_super,
        'title': 'Monthly Floor Turnover & Migration'
    })


# ==========================================
# 3. FLOOR DISCIPLINARY ACTIONS
# ==========================================
@login_required
def floor_disciplinary_manage(request):
    user = request.user
    role = get_user_role(user)
    current_employee = get_current_employee(user)
    is_super = user.is_superuser
    is_admin = role in ['SUPER_ADMIN', 'HR_ADMIN']
    is_supervisor = role in ['DEPT_HEAD', 'MANAGER', 'SUPERVISOR']

    has_perm = is_super or is_admin or is_supervisor or (
        current_employee and getattr(current_employee, 'can_manage_disciplinary', False)
    )
    if not has_perm:
        messages.error(request, "Access denied: You do not have permission to manage Disciplinary Actions.")
        return redirect('dashboard')

    # Identify user's company unit
    user_unit = getattr(current_employee, 'unit', None) if current_employee else None
    if not is_super and not user_unit:
        messages.error(request, "Access restricted: Your profile is not assigned to any Company Unit.")
        return redirect('dashboard')

    # 1. Scope Dropdowns
    if is_super:
        units = CompanyUnit.objects.filter(is_active=True)
        all_floors = Floor.objects.select_related('unit').order_by('name')
        employees_qs = Employee.objects.filter(is_active=True).order_by('first_name')
    else:
        units = CompanyUnit.objects.filter(id=user_unit.id)
        all_floors = Floor.objects.filter(unit=user_unit).order_by('name')
        employees_qs = Employee.objects.filter(unit=user_unit, is_active=True).order_by('first_name')

    # 2. Form Handling
    if request.method == 'POST':
        form = FloorDisciplinaryActionForm(request.POST)
        if not is_super:
            form.fields['unit'].queryset = units
            form.fields['floor'].queryset = all_floors
            if 'employee' in form.fields:
                form.fields['employee'].queryset = employees_qs

        if form.is_valid():
            record = form.save(commit=False)
            if not is_super:
                record.unit = user_unit
                if record.floor.unit_id != user_unit.id:
                    messages.error(request, "Invalid floor selected for your company.")
                    return redirect('floor_disciplinary_manage')

            record.recorded_by = current_employee
            record.save()
            messages.success(request, f"Disciplinary action recorded for {record.floor.name}.")
            return redirect('floor_disciplinary_manage')
        else:
            messages.error(request, "Please correct the form errors.")
    else:
        initial_data = {'date': timezone.now().date()}
        if not is_super and user_unit:
            initial_data['unit'] = user_unit
        form = FloorDisciplinaryActionForm(initial=initial_data)
        if not is_super:
            form.fields['unit'].queryset = units
            form.fields['floor'].queryset = all_floors
            if 'employee' in form.fields:
                form.fields['employee'].queryset = employees_qs

    # 3. Scope QuerySet (Data Wall)
    actions = FloorDisciplinaryAction.objects.select_related('floor', 'unit', 'recorded_by').order_by('-date', 'floor__name')
    if not is_super:
        actions = actions.filter(unit=user_unit)

    # 4. Filters
    filter_date = request.GET.get('filter_date', '').strip()
    filter_floor = request.GET.get('filter_floor', '').strip()

    if filter_date:
        try:
            actions = actions.filter(date=date.fromisoformat(filter_date))
        except ValueError:
            pass

    if filter_floor:
        actions = actions.filter(floor_id=filter_floor)

    # Match whatever your actual template filename is:
    return render(request, 'employees/floor_disciplinary_manage.html', {
        'form': form,
        'actions': actions,
        'units': units,
        'all_floors': all_floors,
        'filter_date': filter_date,
        'filter_floor': filter_floor,
        'is_super': is_super,
        'title': 'Floor Disciplinary Actions'
    })


# ==========================================
# 4. FLOOR ANALYTICS SUMMARY
# ==========================================
@login_required
def floor_analytics_summary(request):
    role = get_user_role(request.user)
    current_employee = get_current_employee(request.user)
    is_admin = role in ['SUPER_ADMIN', 'HR_ADMIN']
    is_supervisor = role in ['DEPT_HEAD', 'MANAGER', 'SUPERVISOR']

    has_perm = is_admin or is_supervisor or (
        current_employee and (
            current_employee.can_view_floor_analytics or 
            current_employee.can_manage_attendance or 
            current_employee.can_manage_migration
        )
    )
    if not has_perm:
        messages.error(request, "Access denied: You do not have permission to view Floor Analytics.")
        return redirect('dashboard')

    today = timezone.now().date()
    default_start = today.replace(day=1)
    
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    
    try:
        start_date = date.fromisoformat(start_date_str) if start_date_str else default_start
    except ValueError:
        start_date = default_start

    try:
        end_date = date.fromisoformat(end_date_str) if end_date_str else today
    except ValueError:
        end_date = today

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    units = CompanyUnit.objects.filter(is_active=True)
    all_floors = Floor.objects.select_related('unit').all().order_by('name')

    selected_unit = request.GET.get('unit', '').strip()
    selected_floor = request.GET.get('floor', '').strip()

    floors = all_floors
    if selected_unit:
        floors = floors.filter(unit_id=selected_unit)
    if selected_floor:
        floors = floors.filter(id=selected_floor)

    analytics_data = []

    tot_avg_manpower = Decimal('0.0')
    tot_avg_present = Decimal('0.0')
    tot_avg_absent = Decimal('0.0')
    tot_joined = 0
    tot_resigned = 0
    tot_separated = 0
    tot_left = 0

    is_single_day = (start_date == end_date)

    for fl in floors:
        att_logs = DailyFloorAttendance.objects.filter(floor=fl, date__range=(start_date, end_date))
        tot_days = att_logs.count()
        avg_manpower = att_logs.aggregate(avg=Avg('total_manpower'))['avg'] or 0
        avg_present = att_logs.aggregate(avg=Avg('present_count'))['avg'] or 0
        avg_absent = att_logs.aggregate(avg=Avg('absent_count'))['avg'] or 0
        avg_late = att_logs.aggregate(avg=Avg('late_count'))['avg'] or 0

        if avg_manpower > 0:
            avg_absent_rate = round((Decimal(str(avg_absent)) / Decimal(str(avg_manpower))) * 100, 2)
        else:
            avg_absent_rate = Decimal('0.00')

        total_fl_joined = 0
        total_fl_resigned = 0
        total_fl_separated = 0
        total_fl_left = 0

        if not is_single_day:
            curr_year = start_date.year
            curr_month = start_date.month
            end_year = end_date.year
            end_month = end_date.month

            while (curr_year, curr_month) <= (end_year, end_month):
                m_first = date(curr_year, curr_month, 1)
                days_in_month = calendar.monthrange(curr_year, curr_month)[1]
                m_last = date(curr_year, curr_month, days_in_month)

                overlap_start = max(start_date, m_first)
                overlap_end = min(end_date, m_last)
                overlap_days = max(0, (overlap_end - overlap_start).days + 1)

                mig = MonthlyMigration.objects.filter(floor=fl, month=m_first).first()
                if mig and days_in_month > 0:
                    factor = Decimal(str(overlap_days)) / Decimal(str(days_in_month))
                    raw_joined = max(0, int(mig.new_joined or 0))
                    raw_resigned = max(0, int(mig.resigned_count or 0))
                    raw_separated = max(0, int(mig.separated_count or 0))
                    raw_total_left = max(raw_resigned + raw_separated, max(0, int(getattr(mig, 'total_left', 0) or 0)))

                    total_fl_joined += int(round(Decimal(str(raw_joined)) * factor))
                    total_fl_resigned += int(round(Decimal(str(raw_resigned)) * factor))
                    total_fl_separated += int(round(Decimal(str(raw_separated)) * factor))
                    total_fl_left += int(round(Decimal(str(raw_total_left)) * factor))

                if curr_month == 12:
                    curr_year += 1
                    curr_month = 1
                else:
                    curr_month += 1

        if avg_manpower > 0 and total_fl_left > 0:
            avg_turnover_rate = round((Decimal(str(total_fl_left)) / Decimal(str(avg_manpower))) * 100, 2)
        else:
            avg_turnover_rate = Decimal('0.00')

        tot_avg_manpower += Decimal(str(avg_manpower))
        tot_avg_present += Decimal(str(avg_present))
        tot_avg_absent += Decimal(str(avg_absent))
        tot_joined += total_fl_joined
        tot_resigned += total_fl_resigned
        tot_separated += total_fl_separated
        tot_left += total_fl_left

        analytics_data.append({
            'floor': fl,
            'unit': fl.unit,
            'days_recorded': tot_days,
            'avg_manpower': round(avg_manpower, 1),
            'avg_present': round(avg_present, 1),
            'avg_absent': round(avg_absent, 1),
            'avg_late': round(avg_late, 1),
            'avg_absent_rate': avg_absent_rate,
            'total_joined': total_fl_joined,
            'total_resigned': total_fl_resigned,
            'total_separated': total_fl_separated,
            'total_left': total_fl_left,
            'avg_turnover_rate': max(Decimal('0.00'), avg_turnover_rate),
        })

    overall_absent_rate = round((tot_avg_absent / tot_avg_manpower * 100), 2) if tot_avg_manpower > 0 else Decimal('0.00')
    overall_turnover_rate = round((Decimal(str(tot_left)) / tot_avg_manpower * 100), 2) if tot_avg_manpower > 0 and tot_left > 0 else Decimal('0.00')

    summary_totals = {
        'avg_manpower': round(tot_avg_manpower, 1),
        'avg_present': round(tot_avg_present, 1),
        'avg_absent': round(tot_avg_absent, 1),
        'overall_absent_rate': overall_absent_rate,
        'total_joined': tot_joined,
        'total_resigned': tot_resigned,
        'total_separated': tot_separated,
        'total_left': tot_left,
        'overall_turnover_rate': max(Decimal('0.00'), overall_turnover_rate),
    }

    return render(request, 'employees/floor_analytics_summary.html', {
        'analytics_data': analytics_data,
        'summary_totals': summary_totals,
        'units': units,
        'all_floors': all_floors,
        'selected_unit': selected_unit,
        'selected_floor': selected_floor,
        'start_date': start_date,
        'end_date': end_date,
        'is_admin': is_admin,
        'title': 'Floor Attendance & Turnover Analytics'
    })


# ==========================================
# 5. FLOOR DISCIPLINARY ANALYTICS
# ==========================================
@login_required
def floor_disciplinary_analytics(request):
    role = get_user_role(request.user)
    current_employee = get_current_employee(request.user)
    is_admin = role in ['SUPER_ADMIN', 'HR_ADMIN']
    is_supervisor = role in ['DEPT_HEAD', 'MANAGER', 'SUPERVISOR']

    has_perm = is_admin or is_supervisor or (
        current_employee and (
            current_employee.can_view_disciplinary_analytics or 
            current_employee.can_manage_disciplinary
        )
    )
    if not has_perm:
        messages.error(request, "Access denied: You do not have permission to view Disciplinary Analytics.")
        return redirect('dashboard')

    today = timezone.now().date()
    default_start = today.replace(day=1)
    
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    
    try:
        start_date = date.fromisoformat(start_date_str) if start_date_str else default_start
    except ValueError:
        start_date = default_start

    try:
        end_date = date.fromisoformat(end_date_str) if end_date_str else today
    except ValueError:
        end_date = today

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    units = CompanyUnit.objects.filter(is_active=True)
    all_floors = Floor.objects.select_related('unit').all().order_by('name')

    selected_unit = request.GET.get('unit', '').strip()
    selected_floor = request.GET.get('floor', '').strip()

    floors = all_floors
    if selected_unit:
        floors = floors.filter(unit_id=selected_unit)

    if selected_floor:
        floors = floors.filter(id=selected_floor)

    analytics_data = []

    tot_manpower = Decimal('0.0')
    tot_incidents = 0
    tot_persons = 0
    tot_verbal = 0
    tot_written = 0
    tot_suspension = 0
    tot_fine = 0
    tot_dismissal = 0
    tot_counseling = 0

    for fl in floors:
        att_logs = DailyFloorAttendance.objects.filter(floor=fl, date__range=(start_date, end_date))
        avg_manpower = att_logs.aggregate(avg=Avg('total_manpower'))['avg'] or 0

        disc_logs = FloorDisciplinaryAction.objects.filter(floor=fl, date__range=(start_date, end_date))
        
        incidents_count = disc_logs.count()
        persons_involved = disc_logs.aggregate(s=Sum('person_count'))['s'] or 0
        verbal_count = disc_logs.filter(action_taken='VERBAL_WARNING').aggregate(s=Sum('person_count'))['s'] or 0
        written_count = disc_logs.filter(action_taken='WRITTEN_WARNING').aggregate(s=Sum('person_count'))['s'] or 0
        suspension_count = disc_logs.filter(action_taken='SUSPENSION').aggregate(s=Sum('person_count'))['s'] or 0
        fine_count = disc_logs.filter(action_taken='FINE_DEDUCTION').aggregate(s=Sum('person_count'))['s'] or 0
        dismissal_count = disc_logs.filter(action_taken='DISMISSAL').aggregate(s=Sum('person_count'))['s'] or 0
        counseling_count = disc_logs.filter(action_taken='COUNSELING').aggregate(s=Sum('person_count'))['s'] or 0

        if avg_manpower > 0 and persons_involved > 0:
            incident_rate = round((Decimal(str(persons_involved)) / Decimal(str(avg_manpower))) * 100, 2)
        else:
            incident_rate = Decimal('0.00')

        tot_manpower += Decimal(str(avg_manpower))
        tot_incidents += incidents_count
        tot_persons += persons_involved
        tot_verbal += verbal_count
        tot_written += written_count
        tot_suspension += suspension_count
        tot_fine += fine_count
        tot_dismissal += dismissal_count
        tot_counseling += counseling_count

        analytics_data.append({
            'floor': fl,
            'unit': fl.unit,
            'avg_manpower': round(avg_manpower, 1),
            'incidents_count': incidents_count,
            'persons_involved': persons_involved,
            'verbal_count': verbal_count,
            'written_count': written_count,
            'suspension_count': suspension_count,
            'fine_count': fine_count,
            'dismissal_count': dismissal_count,
            'counseling_count': counseling_count,
            'incident_rate': incident_rate,
        })

    overall_incident_rate = round((Decimal(str(tot_persons)) / tot_manpower * 100), 2) if tot_manpower > 0 and tot_persons > 0 else Decimal('0.00')

    summary_totals = {
        'avg_manpower': round(tot_manpower, 1),
        'tot_incidents': tot_incidents,
        'tot_persons': tot_persons,
        'tot_verbal': tot_verbal,
        'tot_written': tot_written,
        'tot_suspension': tot_suspension,
        'tot_fine': tot_fine,
        'tot_dismissal': tot_dismissal,
        'tot_counseling': tot_counseling,
        'overall_incident_rate': overall_incident_rate,
    }

    return render(request, 'employees/floor_disciplinary_analytics.html', {
        'analytics_data': analytics_data,
        'summary_totals': summary_totals,
        'units': units,
        'all_floors': all_floors,
        'selected_unit': selected_unit,
        'selected_floor': selected_floor,
        'start_date': start_date,
        'end_date': end_date,
        'is_admin': is_admin,
        'title': 'Floor Disciplinary & Incident Analytics'
    })

def sync_monthly_floor_production(floor, entry_date):
    """
    Finds or automatically creates/updates the Monthly record for this floor,
    then recalculates totals and averages from all daily entries in that month.
    """
    from employees.models import MonthlyFloorProductionSummary

    month_start = entry_date.replace(day=1)
    last_day = calendar.monthrange(entry_date.year, entry_date.month)[1]
    month_end = entry_date.replace(day=last_day)

    daily_records = FloorProductionKPI.objects.filter(
        floor=floor,
        date__range=(month_start, month_end)
    )

    if not daily_records.exists():
        return

    agg = daily_records.aggregate(
        days=Count('id'),
        tot_target=Sum('target_quantity'),
        tot_produced=Sum('produced_quantity'),
        avg_eff=Avg('efficiency_rate'),
        avg_dhu=Avg('dhu_rate'),
        pass_qty=Sum('inspection_pass_qty'),
        fail_qty=Sum('inspection_fail_qty'),
        tot_ot=Sum('extra_ot_hours'),
        avg_ship=Avg('timely_shipment_rate'),
        avg_mgmt=Avg('floor_management_score'),
        tot_disc=Sum('disciplinary_count'),
        avg_kpi=Avg('kpi_rank_score')
    )

    latest_emp = daily_records.exclude(employee__isnull=True).order_by('-date').values_list('employee_id', flat=True).first()

    MonthlyFloorProductionSummary.objects.update_or_create(
        floor=floor,
        month=month_start,
        defaults={
            'unit': floor.unit,
            'employee_id': latest_emp,
            'days_recorded': agg['days'] or 0,
            'total_target': agg['tot_target'] or 0,
            'total_produced': agg['tot_produced'] or 0,
            'avg_efficiency': round(Decimal(str(agg['avg_eff'] or 0)), 2),
            'avg_dhu': round(Decimal(str(agg['avg_dhu'] or 0)), 2),
            'total_inspection_pass': agg['pass_qty'] or 0,
            'total_inspection_fail': agg['fail_qty'] or 0,
            'total_extra_ot': round(Decimal(str(agg['tot_ot'] or 0)), 2),
            'avg_timely_shipment': round(Decimal(str(agg['avg_ship'] or 100)), 2),
            'avg_floor_mgmt': round(Decimal(str(agg['avg_mgmt'] or 100)), 2),
            'total_disciplinary': agg['tot_disc'] or 0,
            'avg_kpi_score': round(Decimal(str(agg['avg_kpi'] or 0)), 2),
        }
    )


@login_required
def floor_production_manage(request):
    user, current_employee, user_unit, is_super = get_tenant_context(request)
    role = get_user_role(request.user)
    is_admin = role in ['SUPER_ADMIN', 'HR_ADMIN']
    is_supervisor = role in ['DEPT_HEAD', 'MANAGER', 'SUPERVISOR']

    has_perm = is_super or is_admin or is_supervisor or (
        current_employee and getattr(current_employee, 'can_manage_production', False)
    )
    if not has_perm:
        messages.error(request, "Access denied: Insufficient privileges.")
        return redirect('dashboard')

    # 1. Scope dropdown choices for Unit, Floors, and Employees
    if is_super:
        units = CompanyUnit.objects.filter(is_active=True)
        all_floors = Floor.objects.select_related('unit').order_by('name')
        employees_qs = Employee.objects.filter(is_active=True).order_by('first_name', 'last_name')
    else:
        if not user_unit:
            messages.error(request, "Your account is not assigned to any Company Unit.")
            return redirect('dashboard')
        units = CompanyUnit.objects.filter(id=user_unit.id)
        all_floors = Floor.objects.filter(unit=user_unit).order_by('name')
        employees_qs = Employee.objects.filter(unit=user_unit, is_active=True).order_by('first_name', 'last_name')

    if request.method == 'POST':
        form = FloorProductionKPIForm(request.POST)
        form.fields['unit'].queryset = units
        form.fields['floor'].queryset = all_floors
        form.fields['employee'].queryset = employees_qs

        if form.is_valid():
            cleaned = form.cleaned_data
            target_floor = cleaned['floor']
            target_date = cleaned['date']
            target_unit = cleaned['unit']

            # Tenant integrity check
            if not is_super:
                target_unit = user_unit
                if target_floor.unit_id != user_unit.id:
                    raise PermissionDenied("Selected floor does not belong to your company.")

            # Look up by python date object or create new
            record = FloorProductionKPI.objects.filter(floor=target_floor, date=target_date).first()
            is_new = record is None

            if is_new:
                record = FloorProductionKPI(floor=target_floor, date=target_date)

            record.unit = target_unit
            record.employee = cleaned.get('employee')
            record.target_quantity = cleaned.get('target_quantity', 0)
            record.produced_quantity = cleaned.get('produced_quantity', 0)
            record.efficiency_rate = cleaned.get('efficiency_rate', 0)
            record.dhu_rate = cleaned.get('dhu_rate', 0)
            record.inspection_pass_qty = cleaned.get('inspection_pass_qty', 0)
            record.inspection_fail_qty = cleaned.get('inspection_fail_qty', 0)
            record.extra_ot_hours = cleaned.get('extra_ot_hours', 0)
            record.timely_shipment_rate = cleaned.get('timely_shipment_rate', 100)
            record.excess_shipment_qty = cleaned.get('excess_shipment_qty', 0)
            record.short_shipment_qty = cleaned.get('short_shipment_qty', 0)
            record.delay_shipment_qty = cleaned.get('delay_shipment_qty', 0)
            record.air_shipment_qty = cleaned.get('air_shipment_qty', 0)
            record.floor_management_score = cleaned.get('floor_management_score', 100)
            record.disciplinary_count = cleaned.get('disciplinary_count', 0)
            record.remarks = cleaned.get('remarks', '')
            record.recorded_by = current_employee
            record.save()

            # Auto-sync monthly summary table
            try:
                sync_monthly_floor_production(floor=record.floor, entry_date=record.date)
            except Exception as e:
                print(f"Monthly sync warning: {e}")

            action_text = "created" if is_new else "updated"
            messages.success(request, f"Production record for {record.floor.name} ({record.date}) {action_text} successfully.")
            return redirect('floor_production_manage')
        else:
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields and form.fields[field].label else field.replace('_', ' ').title()
                for error in errors:
                    messages.error(request, f"{field_label}: {error}")
    else:
        initial_data = {'date': timezone.now().date()}
        if not is_super and user_unit:
            initial_data['unit'] = user_unit
        form = FloorProductionKPIForm(initial=initial_data)
        form.fields['unit'].queryset = units
        form.fields['floor'].queryset = all_floors
        form.fields['employee'].queryset = employees_qs

    # 2. Scope Table / Records
    productions = FloorProductionKPI.objects.select_related('unit', 'floor', 'employee', 'recorded_by').order_by('-date', '-kpi_rank_score')
    productions = scope_queryset_to_unit(productions, request, unit_field='unit')

    # Apply user GET filters
    filter_date = request.GET.get('filter_date', '').strip()
    filter_floor = request.GET.get('filter_floor', '').strip()
    filter_unit = request.GET.get('unit', '').strip()

    if is_super and filter_unit:
        productions = productions.filter(unit_id=filter_unit)
    if filter_date:
        try:
            productions = productions.filter(date=date.fromisoformat(filter_date))
        except ValueError:
            pass
    if filter_floor:
        productions = productions.filter(floor_id=filter_floor)

    return render(request, 'employees/floor_production_manage.html', {
        'form': form,
        'productions': productions,
        'units': units,
        'all_floors': all_floors,
        'filter_date': filter_date,
        'filter_floor': filter_floor,
        'filter_unit': filter_unit,
        'is_super': is_super,
        'title': 'Daily Floor Production Entry & KPI Assessment'
    })

@login_required
def get_employees_by_floor(request):
    user, current_employee, user_unit, is_super = get_tenant_context(request)
    floor_id = request.GET.get('floor_id', '').strip()
    unit_id = request.GET.get('unit_id', '').strip()

    employees_qs = Employee.objects.filter(is_active=True).select_related('designation', 'unit')

    # Apply strict tenant isolation
    if not is_super:
        if not user_unit:
            return JsonResponse({'employees': []})
        employees_qs = employees_qs.filter(unit=user_unit)
    elif unit_id:
        employees_qs = employees_qs.filter(unit_id=unit_id)

    if floor_id:
        employees_qs = employees_qs.filter(floor_id=floor_id)

    data = [
        {
            'id': emp.id,
            'name': f"{emp.full_name} ({emp.employee_code}) - {emp.designation.title if emp.designation else 'Staff'}"
        }
        for emp in employees_qs.order_by('first_name', 'last_name')
    ]

    return JsonResponse({'employees': data})

def sync_monthly_floor_production(floor, entry_date):
    """
    Finds or automatically creates the Monthly record for this floor,
    then recalculates totals and averages from all daily entries in that month.
    """
    month_start = entry_date.replace(day=1)
    last_day = calendar.monthrange(entry_date.year, entry_date.month)[1]
    month_end = entry_date.replace(day=last_day)

    # 1. Query all daily entries for this floor in the current month
    daily_records = FloorProductionKPI.objects.filter(
        floor=floor,
        date__range=(month_start, month_end)
    )

    if not daily_records.exists():
        return

    # 2. Compute aggregate values
    agg = daily_records.aggregate(
        days=Count('id'),
        tot_target=Sum('target_quantity'),
        tot_produced=Sum('produced_quantity'),
        avg_eff=Avg('efficiency_rate'),
        avg_dhu=Avg('dhu_rate'),
        pass_qty=Sum('inspection_pass_qty'),
        fail_qty=Sum('inspection_fail_qty'),
        tot_ot=Sum('extra_ot_hours'),
        avg_ship=Avg('timely_shipment_rate'),
        avg_mgmt=Avg('floor_management_score'),
        tot_disc=Sum('disciplinary_count'),
        avg_kpi=Avg('kpi_rank_score')
    )

    # Pick the latest in-charge employee assigned in this month
    latest_emp = daily_records.exclude(employee__isnull=True).order_by('-date').values_list('employee_id', flat=True).first()

    # 3. Auto Create or Update in Database
    MonthlyFloorProductionSummary.objects.update_or_create(
        floor=floor,
        month=month_start,
        defaults={
            'unit': floor.unit,
            'employee_id': latest_emp,
            'days_recorded': agg['days'] or 0,
            'total_target': agg['tot_target'] or 0,
            'total_produced': agg['tot_produced'] or 0,
            'avg_efficiency': round(Decimal(str(agg['avg_eff'] or 0)), 2),
            'avg_dhu': round(Decimal(str(agg['avg_dhu'] or 0)), 2),
            'total_inspection_pass': agg['pass_qty'] or 0,
            'total_inspection_fail': agg['fail_qty'] or 0,
            'total_extra_ot': round(Decimal(str(agg['tot_ot'] or 0)), 2),
            'avg_timely_shipment': round(Decimal(str(agg['avg_ship'] or 100)), 2),
            'avg_floor_mgmt': round(Decimal(str(agg['avg_mgmt'] or 100)), 2),
            'total_disciplinary': agg['tot_disc'] or 0,
            'avg_kpi_score': round(Decimal(str(agg['avg_kpi'] or 0)), 2),
        }
    )

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from django.contrib import admin, messages
from django.contrib.auth.models import User


from .models import (
    Employee, Department, Designation, Floor, 
    CompanyUnit, DailyFloorAttendance, MonthlyMigration,
    UserProfile, Section, SubSection, JobGrade, JobLocation
)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        'employee_code', 'full_name', 'department', 
        'designation', 'floor', 'password_change_link', 'is_active'
    ]
    list_filter = ['department', 'designation', 'floor', 'employment_status', 'is_active']
    search_fields = ['employee_code', 'first_name', 'last_name', 'email', 'mobile']
    readonly_fields = ['password_change_button']
    actions = ['generate_user_accounts', 'reset_passwords_to_default']

    # Bulk Action: Generate accounts for all selected employees
    def generate_user_accounts(self, request, queryset):
        created_count = 0
        for emp in queryset:
            if not emp.user:
                username = emp.employee_code.strip()
                user, _ = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'first_name': emp.first_name,
                        'last_name': emp.last_name,
                        'email': emp.email or f"{username.lower()}@company.com",
                        'is_staff': True,
                        'is_active': emp.is_active,
                    }
                )
                user.set_password(username)  # Default password = Employee Code
                user.save()
                emp.user = user
                emp.save(update_fields=['user'])
                created_count += 1
        self.message_user(request, f"Successfully created login user accounts for {created_count} employee(s). Default password is their Employee Code.", messages.SUCCESS)
    generate_user_accounts.short_description = "🔑 Generate User Accounts & Default Passwords"

    # Bulk Action: Reset password to Employee Code for selected
    def reset_passwords_to_default(self, request, queryset):
        reset_count = 0
        for emp in queryset:
            if emp.user:
                emp.user.set_password(emp.employee_code.strip())
                emp.user.save()
                reset_count += 1
        self.message_user(request, f"Reset passwords to default (Employee Code) for {reset_count} employee(s).", messages.SUCCESS)
    reset_passwords_to_default.short_description = "🔄 Reset Selected Passwords to Employee Code"

    def password_change_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_password_change', args=[obj.user.id])
            return format_html('<a class="btn btn-xs btn-outline-primary" href="{}"><i class="fas fa-key"></i> Reset Password</a>', url)
        return format_html('<span class="badge badge-warning text-dark">No User Account</span>')
    password_change_link.short_description = "Password"

    def password_change_button(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_password_change', args=[obj.user.id])
            return format_html('<a class="btn btn-sm btn-info text-white" href="{}" target="_blank"><i class="fas fa-key me-1"></i> Change Password for <strong>{}</strong></a>', url, obj.user.username)
        return "Save employee to auto-generate linked User account."
    password_change_button.short_description = "Password Action"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'employee', 'role', 'can_override_kpi']
    list_filter = ['role', 'can_override_kpi']
    search_fields = ['user__username', 'employee__first_name', 'employee__last_name']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'unit', 'is_active']
    search_fields = ['name', 'code']


@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ['title', 'code', 'is_active']
    search_fields = ['title', 'code']


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit', 'building']
    search_fields = ['name']


@admin.register(CompanyUnit)
class CompanyUnitAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active']


@admin.register(DailyFloorAttendance)
class DailyFloorAttendanceAdmin(admin.ModelAdmin):
    list_display = ['date', 'floor', 'unit', 'total_manpower', 'present_count', 'absent_count', 'absenteeism_rate', 'recorded_by']
    list_filter = ['floor', 'date']


@admin.register(MonthlyMigration)
class MonthlyMigrationAdmin(admin.ModelAdmin):
    list_display = ['month', 'floor', 'opening_manpower', 'new_joined', 'total_left', 'closing_manpower', 'migration_rate', 'recorded_by']
    list_filter = ['floor', 'month']


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'department', 'is_active']


@admin.register(SubSection)
class SubSectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'section', 'is_active']


@admin.register(JobGrade)
class JobGradeAdmin(admin.ModelAdmin):
    list_display = ['name', 'level']


@admin.register(JobLocation)
class JobLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit']
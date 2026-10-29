from django.contrib import admin
from .models import (
    KPI, KPIAssignment, PerformancePeriod, 
    PerformanceReview, MonthlyKPI, DailyWork, 
    WorkApproval, TaskEvidence, AssignedTask, RatingScale
)


@admin.register(KPI)
class KPIAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'department', 'designation', 'is_active']
    list_filter = ['department', 'designation', 'is_active']
    search_fields = ['name', 'code', 'description']


@admin.register(KPIAssignment)
class KPIAssignmentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'kpi', 'period', 'weight', 'target', 'unit', 'assigned_by']
    list_filter = ['period', 'kpi', 'unit']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_code', 'kpi__name']


@admin.register(AssignedTask)
class AssignedTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'employee', 'kpi', 'target', 'deadline', 'status', 'assigned_by']
    list_filter = ['status', 'deadline']
    search_fields = ['title', 'employee__first_name', 'employee__last_name', 'employee__employee_code']


@admin.register(DailyWork)
class DailyWorkAdmin(admin.ModelAdmin):
    list_display = ['task_title', 'employee', 'kpi', 'work_date', 'target_quantity', 'achievement_quantity', 'status']
    list_filter = ['status', 'work_date']
    search_fields = ['task_title', 'employee__first_name', 'employee__last_name', 'employee__employee_code']


@admin.register(WorkApproval)
class WorkApprovalAdmin(admin.ModelAdmin):
    list_display = ['daily_work', 'approved_by', 'verified_achievement', 'quality_score', 'timeliness_score', 'supervisor_score']
    search_fields = ['daily_work__task_title', 'approved_by__first_name', 'approved_by__last_name']


@admin.register(PerformancePeriod)
class PerformancePeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'period_type', 'start_date', 'end_date', 'status', 'is_locked']
    list_filter = ['period_type', 'status', 'is_locked']


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ['employee', 'period', 'system_generated_score', 'supervisor_evaluation_score', 'final_score', 'rating', 'is_overridden']
    list_filter = ['period', 'rating', 'is_overridden']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_code']


@admin.register(MonthlyKPI)
class MonthlyKPIAdmin(admin.ModelAdmin):
    list_display = ['employee', 'period', 'kpi', 'weight', 'achievement_percentage', 'weighted_score', 'final_kpi_score']
    list_filter = ['period', 'kpi']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_code']


@admin.register(RatingScale)
class RatingScaleAdmin(admin.ModelAdmin):
    list_display = ['grade', 'name', 'min_score', 'max_score']
    ordering = ['-min_score']


@admin.register(TaskEvidence)
class TaskEvidenceAdmin(admin.ModelAdmin):
    list_display = ['daily_work', 'original_filename', 'uploaded_by', 'uploaded_at']
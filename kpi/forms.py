from django import forms
from .models import KPI, KPIAssignment, PerformancePeriod, DailyWork, WorkApproval, AssignedTask
from employees.models import Employee, Department, Designation
from decimal import Decimal


class KPIForm(forms.ModelForm):
    class Meta:
        model = KPI
        fields = ['code', 'name', 'description', 'department', 'designation', 'default_weight', 'measurement_type', 'default_target', 'unit', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. PAY-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Payroll Processing Accuracy'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Describe measurement indicator...'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'designation': forms.Select(attrs={'class': 'form-select'}),
            'default_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'measurement_type': forms.Select(attrs={'class': 'form-select'}),
            'default_target': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. %, Count, Days'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class KPIAssignmentForm(forms.ModelForm):
    class Meta:
        model = KPIAssignment
        fields = ['employee', 'kpi', 'period', 'weight', 'target', 'unit', 'effective_date']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'kpi': forms.Select(attrs={'class': 'form-select'}),
            'period': forms.Select(attrs={'class': 'form-select'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'target': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'effective_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }


class PerformancePeriodForm(forms.ModelForm):
    class Meta:
        model = PerformancePeriod
        fields = ['name', 'period_type', 'start_date', 'end_date', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Q3 2026 / August 2026'}),
            'period_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class DailyWorkForm(forms.ModelForm):
    evidence_file = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    class Meta:
        model = DailyWork
        fields = [
            'work_date', 'kpi', 'task_category', 'task_title', 
            'task_description', 'target_quantity', 'achievement_quantity', 
            'unit', 'priority', 'start_time', 'end_time', 'remarks'
        ]
        widgets = {
            'work_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'kpi': forms.Select(attrs={'class': 'form-select'}),
            'task_category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'task_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Absent Report & Daily Attendance Checking'}),
            'task_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Provide details of tasks performed...'}),
            'target_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'achievement_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Count, %, Days'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 1, 'placeholder': 'Optional remarks'}),
        }

    def __init__(self, *args, **kwargs):
        employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        if employee:
            assigned_kpis = KPIAssignment.objects.filter(employee=employee).values_list('kpi_id', flat=True)
            if assigned_kpis.exists():
                self.fields['kpi'].queryset = KPI.objects.filter(id__in=assigned_kpis, is_active=True)
            else:
                self.fields['kpi'].queryset = KPI.objects.filter(is_active=True)


class SupervisorApprovalForm(forms.ModelForm):
    approval_status = forms.ChoiceField(
        choices=[
            ('Approved', 'Approve Work'),
            ('Partially Approved', 'Partially Approve'),
            ('Returned', 'Return Work for Correction'),
            ('Rejected', 'Reject Work'),
        ],
        widget=forms.Select(attrs={'class': 'form-select fw-bold'})
    )

    class Meta:
        model = WorkApproval
        fields = ['verified_achievement', 'quality_score', 'timeliness_score', 'supervisor_score', 'approval_remarks']
        widgets = {
            'verified_achievement': forms.NumberInput(attrs={'class': 'form-control fw-bold'}),
            'quality_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'timeliness_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'supervisor_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'approval_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class AssignedTaskForm(forms.ModelForm):
    start_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        input_formats=['%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%d/%m/%Y']
    )
    deadline = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        input_formats=['%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%d/%m/%Y']
    )

    class Meta:
        model = AssignedTask
        fields = [
            'title', 'employee', 'kpi', 'start_date', 'deadline',
            'priority', 'target', 'unit', 'description'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Cutting Manpower Report'}),
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'kpi': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'target': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Count'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Task instructions...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'kpi' in self.fields:
            self.fields['kpi'].required = False
            self.fields['kpi'].empty_label = "-- Related KPI (Optional) --"
        if 'employee' in self.fields:
            self.fields['employee'].empty_label = "-- Select Employee --"
            self.fields['employee'].queryset = Employee.objects.filter(is_active=True).select_related('designation', 'department')
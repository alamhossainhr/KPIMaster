from django import forms
from django.contrib.auth.models import User
from .models import Employee, FloorProductionKPI, UserProfile
from .models import FloorDisciplinaryAction
from .models import (
    CompanyUnit, Department, Section, SubSection, 
    Designation, Floor, JobGrade, JobLocation, Employee
)
from .models import DailyFloorAttendance, MonthlyMigration
from .models import FloorProductionKPI

class DailyFloorAttendanceForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

    class Meta:
        model = DailyFloorAttendance
        fields = ['unit', 'floor', 'date', 'total_manpower', 'present_count', 'absent_count', 'late_count', 'leave_count', 'remarks']
        widgets = {
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'floor': forms.Select(attrs={'class': 'form-select'}),
            'total_manpower': forms.NumberInput(attrs={'class': 'form-control'}),
            'present_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'absent_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'late_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'leave_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class MonthlyMigrationForm(forms.ModelForm):
    month = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

    class Meta:
        model = MonthlyMigration
        fields = ['unit', 'floor', 'month', 'opening_manpower', 'new_joined', 'resigned_count', 'separated_count', 'remarks']
        widgets = {
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'floor': forms.Select(attrs={'class': 'form-select'}),
            'opening_manpower': forms.NumberInput(attrs={'class': 'form-control'}),
            'new_joined': forms.NumberInput(attrs={'class': 'form-control'}),
            'resigned_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'separated_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class EmployeeForm(forms.ModelForm):
    # Optional login account toggle fields
    create_login = forms.BooleanField(required=False, initial=True, label="Enable Login Account for this Employee")
    username = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. AAL00786'}))
    password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter account password'}))
    system_role = forms.ChoiceField(
        choices=[
            ('EMPLOYEE', 'Employee'),
            ('SUPERVISOR', 'Supervisor'),
            ('DEPT_HEAD', 'Department Head'),
            ('HR_ADMIN', 'HR Admin'),
            ('SUPER_ADMIN', 'Super Admin'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Employee
        fields = [
            'employee_code', 'first_name', 'last_name', 'email', 'mobile',
            'unit', 'department', 'section', 'sub_section', 'designation',
            'floor', 'line_unit', 'job_grade', 'job_location',
            'supervisor', 'department_head', 'joining_date', 'employment_status',
            'employee_category', 'is_active', 'photo', 'can_manage_attendance',
            'can_manage_migration',
            'can_manage_disciplinary',
            'can_manage_attendance',
            'can_manage_migration',
            'can_manage_disciplinary',
            'can_view_floor_analytics',
            'can_view_disciplinary_analytics',
        ]
        widgets = {
            'employee_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. EMP-1001'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@company.com'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '017XXXXXXXX'}),
            'unit': forms.Select(attrs={'class': 'form-select', 'id': 'id_unit'}),
            'department': forms.Select(attrs={'class': 'form-select', 'id': 'id_department'}),
            'section': forms.Select(attrs={'class': 'form-select', 'id': 'id_section'}),
            'sub_section': forms.Select(attrs={'class': 'form-select', 'id': 'id_sub_section'}),
            'designation': forms.Select(attrs={'class': 'form-select'}),
            'floor': forms.Select(attrs={'class': 'form-select'}),
            'line_unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Line-05'}),
            'job_grade': forms.Select(attrs={'class': 'form-select'}),
            'job_location': forms.Select(attrs={'class': 'form-select'}),
            'supervisor': forms.Select(attrs={'class': 'form-select'}),
            'department_head': forms.Select(attrs={'class': 'form-select'}),
            'joining_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'employment_status': forms.Select(attrs={'class': 'form-select'}),
            'employee_category': forms.Select(attrs={'class': 'form-select'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'can_manage_attendance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_manage_migration': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_manage_disciplinary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_manage_attendance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_manage_migration': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_manage_disciplinary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_view_floor_analytics': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_view_disciplinary_analytics': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unit'].queryset = CompanyUnit.objects.filter(is_active=True)
        self.fields['unit'].empty_label = "--------- Select Factory / Unit ---------"
        self.fields['unit'].required = True


class EmployeeEditForm(forms.ModelForm):
    system_role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        required=False,
        label="System Access Role",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Employee
        fields = [
            'first_name', 'last_name', 'email', 'mobile',
            'unit', 'department', 'section', 'sub_section', 'designation',
            'floor', 'line_unit', 'job_grade', 'job_location',
            'supervisor', 'department_head', 'joining_date', 'employment_status',
            'employee_category', 'is_active', 'photo'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'unit': forms.Select(attrs={'class': 'form-select', 'id': 'id_unit'}),
            'department': forms.Select(attrs={'class': 'form-select', 'id': 'id_department'}),
            'section': forms.Select(attrs={'class': 'form-select', 'id': 'id_section'}),
            'sub_section': forms.Select(attrs={'class': 'form-select', 'id': 'id_sub_section'}),
            'designation': forms.Select(attrs={'class': 'form-select'}),
            'floor': forms.Select(attrs={'class': 'form-select'}),
            'line_unit': forms.TextInput(attrs={'class': 'form-control'}),
            'job_grade': forms.Select(attrs={'class': 'form-select'}),
            'job_location': forms.Select(attrs={'class': 'form-select'}),
            'supervisor': forms.Select(attrs={'class': 'form-select'}),
            'department_head': forms.Select(attrs={'class': 'form-select'}),
            'joining_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'employment_status': forms.Select(attrs={'class': 'form-select'}),
            'employee_category': forms.Select(attrs={'class': 'form-select'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'unit' in self.fields:
            self.fields['unit'].queryset = CompanyUnit.objects.filter(is_active=True)
            self.fields['unit'].empty_label = "--------- Select Factory / Unit ---------"


class ResetEmployeePasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'}),
        min_length=6,
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        min_length=6,
        label="Confirm Password"
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("new_password")
        p2 = cleaned_data.get("confirm_password")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class FloorDisciplinaryActionForm(forms.ModelForm):
    class Meta:
        model = FloorDisciplinaryAction
        fields = [
            'unit', 'floor', 'date', 'incident_type', 
            'action_taken', 'person_count', 'employee_id_card', 'reason'
        ]
        widgets = {
            'unit': forms.Select(attrs={'class': 'form-select form-select-sm', 'required': 'required'}),
            'floor': forms.Select(attrs={'class': 'form-select form-select-sm', 'required': 'required'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm', 'required': 'required'}),
            'incident_type': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'e.g. Safety Violation / SOP Breach', 'required': 'required'}),
            'action_taken': forms.Select(attrs={'class': 'form-select form-select-sm', 'required': 'required'}),
            'person_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1', 'value': '1'}),
            'employee_id_card': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Optional ID / Card No.'}),
            'reason': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3, 'placeholder': 'Enter summary of incident & root cause...', 'required': 'required'}),
        }
 


class FloorProductionKPIForm(forms.ModelForm):
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True).order_by('first_name', 'last_name'),
        required=False,
        empty_label="-- Select Employee / In-Charge --",
        widget=forms.Select(attrs={'class': 'form-select form-select-sm', 'id': 'id_employee'})
    )

    ten_days_above_efficiency = forms.DecimalField(
        required=False,
        label="10 Days Above Eff. %",
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm bg-light',
            'step': '0.01',
            'placeholder': '10-D Avg %',
            'id': 'id_ten_days_above_efficiency'
        })
    )
    target_dhu = forms.DecimalField(
        required=False,
        label="Target DHU %",
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm bg-light',
            'step': '0.01',
            'placeholder': 'Target DHU %',
            'id': 'id_target_dhu'
        })
    )

    class Meta:
        model = FloorProductionKPI
        fields = [
            'unit', 'floor', 'employee', 'date',
            'target_quantity', 'produced_quantity', 'efficiency_rate', 'dhu_rate',
            'inspection_pass_qty', 'inspection_fail_qty', 'extra_ot_hours',
            'timely_shipment_rate', 'excess_shipment_qty', 'short_shipment_qty',
            'delay_shipment_qty', 'air_shipment_qty', 'floor_management_score',
            'disciplinary_count', 'remarks'
        ]
        widgets = {
            'unit': forms.Select(attrs={'class': 'form-select form-select-sm', 'id': 'id_unit', 'required': 'required'}),
            'floor': forms.Select(attrs={'class': 'form-select form-select-sm', 'id': 'id_floor', 'required': 'required'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm', 'required': 'required'}),
            'target_quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'produced_quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'efficiency_rate': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0'}),
            'dhu_rate': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0'}),
            'inspection_pass_qty': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'inspection_fail_qty': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'extra_ot_hours': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.1', 'min': '0'}),
            'timely_shipment_rate': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0', 'max': '100'}),
            'excess_shipment_qty': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'short_shipment_qty': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'delay_shipment_qty': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'air_shipment_qty': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'floor_management_score': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.1', 'min': '0', 'max': '100'}),
            'disciplinary_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'remarks': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Remarks / notes...'}),
        }

    def validate_unique(self):
        """
        Bypass ModelForm's unique check so the view can update existing 
        floor/date entries seamlessly instead of throwing validation errors.
        """
        pass
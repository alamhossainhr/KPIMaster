from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone

from django.db.models.signals import post_save
from django.dispatch import receiver

class CompanyUnit(models.Model):
    """
    Factory / Group Business Unit Entity
    """
    name = models.CharField(max_length=150, unique=True, help_text="e.g. Unit 1 - Apparel Division")
    code = models.CharField(max_length=30, unique=True, help_text="e.g. U1, U2, GZ-01")
    address = models.TextField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=30, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Department(models.Model):
    """
    Department belongs to a specific Factory Unit.
    Different units can have the same department code/name (e.g. HRP in both Unit 1 and Unit 2).
    """
    unit = models.ForeignKey(CompanyUnit, on_delete=models.CASCADE, related_name='departments', null=True, blank=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ('unit', 'code')

    def __str__(self):
        prefix = f"[{self.unit.code}] " if self.unit else ""
        return f"{prefix}{self.name} ({self.code})"


class Section(models.Model):
    """
    Section belongs to a Department.
    Scoped unique per department.
    """
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        unique_together = ('department', 'code')

    def __str__(self):
        return f"{self.department.code} - {self.name} ({self.code})"


class SubSection(models.Model):
    """
    SubSection belongs to a Section.
    Scoped unique per section.
    """
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='sub_sections')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        unique_together = ('section', 'code')

    def __str__(self):
        return f"{self.section.name} - {self.name} ({self.code})"


class Designation(models.Model):
    """
    Company-wide job designations (can be shared across all factories).
    """
    title = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return f"{self.title} ({self.code})"


class Floor(models.Model):
    """
    Floor / Line locations can be factory unit-specific.
    """
    unit = models.ForeignKey(CompanyUnit, on_delete=models.CASCADE, related_name='floors', null=True, blank=True)
    name = models.CharField(max_length=50)
    building = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']
        unique_together = ('unit', 'name', 'building')

    def __str__(self):
        prefix = f"[{self.unit.code}] " if self.unit else ""
        return f"{prefix}{self.name} - {self.building or 'Main'}"


class JobGrade(models.Model):
    """
    Standard job grades across the group.
    """
    name = models.CharField(max_length=50, unique=True)
    level = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['level', 'name']

    def __str__(self):
        return f"{self.name} (Level {self.level})"


class JobLocation(models.Model):
    """
    Physical factory addresses and locations.
    """
    unit = models.ForeignKey(CompanyUnit, on_delete=models.CASCADE, related_name='locations', null=True, blank=True)
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Employee(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Probationary', 'Probationary'),
        ('Suspended', 'Suspended'),
        ('Terminated', 'Terminated'),
        ('Resigned', 'Resigned'),
    ]
    
    CATEGORY_CHOICES = [
        ('Management', 'Management'),
        ('Staff', 'Staff'),
        ('Worker', 'Worker'),
        ('Contractual', 'Contractual'),
    ]

     # --- ADD THESE TWO FIELDS ---
    unit = models.ForeignKey(CompanyUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    line_unit = models.CharField(max_length=50, blank=True, null=True)

    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_profile')
    employee_code = models.CharField(max_length=30, unique=True, db_index=True)
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    email = models.EmailField(blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='employees')
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True)
    sub_section = models.ForeignKey(SubSection, on_delete=models.SET_NULL, null=True, blank=True)
    designation = models.ForeignKey(Designation, on_delete=models.PROTECT, related_name='employees')
    
    floor = models.ForeignKey(Floor, on_delete=models.SET_NULL, null=True, blank=True)
    line = models.CharField(max_length=50, blank=True, null=True)
    job_grade = models.ForeignKey(JobGrade, on_delete=models.SET_NULL, null=True, blank=True)
    job_location = models.ForeignKey(JobLocation, on_delete=models.SET_NULL, null=True, blank=True)
    
    supervisor = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')
    department_head = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dept_members')
    
    joining_date = models.DateField()
    employment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    employee_category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Staff')
    photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['employee_code']

    def __str__(self):
        return f"{self.employee_code} - {self.first_name} {self.last_name} ({self.designation.title})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    # Granular Operational Permissions
    can_manage_attendance = models.BooleanField(
        default=False, 
        verbose_name="Can Manage Floor Attendance",
        help_text="Allow recording and modifying daily floor attendance/absenteeism."
    )
    can_manage_migration = models.BooleanField(
        default=False, 
        verbose_name="Can Manage Migration",
        help_text="Allow recording and modifying monthly employee turnover & migration."
    )
    can_manage_disciplinary = models.BooleanField(
        default=False, 
        verbose_name="Can Manage Disciplinary Actions",
        help_text="Allow logging and viewing floor-wise disciplinary incidents."
    )

    # Dedicated Analytics / View Report Permissions
    can_view_floor_analytics = models.BooleanField(
        default=False, 
        verbose_name="Can View Floor Analytics",
        help_text="Allow viewing Floor Attendance & Migration summary reports."
    )
    can_view_disciplinary_analytics = models.BooleanField(
        default=False, 
        verbose_name="Can View Disciplinary Analytics",
        help_text="Allow viewing Floor Disciplinary incident analytics & charts."
    )

    floor = models.ForeignKey(
        'Floor', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_employees',
        help_text="Assigned manufacturing floor/line"
    )

    can_manage_production = models.BooleanField(
        default=False, 
        verbose_name="Can Manage Floor Production",
        help_text="Allow recording and updating floor-wise daily production & KPI rank data."
    )

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('SUPER_ADMIN', 'Super Admin'),
        ('HR_ADMIN', 'HR Admin'),
        ('DEPT_HEAD', 'Department Head'),
        ('SUPERVISOR', 'Supervisor'),
        ('EMPLOYEE', 'Employee'),
        ('MANAGEMENT_VIEWER', 'Management Viewer'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='role_profile')
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, null=True, blank=True, related_name='user_account')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='EMPLOYEE')
    can_override_kpi = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class DailyFloorAttendance(models.Model):
    unit = models.ForeignKey('CompanyUnit', on_delete=models.CASCADE, related_name='daily_attendances')
    floor = models.ForeignKey('Floor', on_delete=models.CASCADE, related_name='floor_attendances')
    date = models.DateField(default=timezone.now)
    total_manpower = models.PositiveIntegerField(default=0, help_text="Total registered operators/staff on floor")
    present_count = models.PositiveIntegerField(default=0)
    absent_count = models.PositiveIntegerField(default=0)
    late_count = models.PositiveIntegerField(default=0)
    leave_count = models.PositiveIntegerField(default=0)
    absenteeism_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Calculated Absenteeism %")
    recorded_by = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('floor', 'date')
        ordering = ['-date', 'floor']

    def save(self, *args, **kwargs):
        # Auto-compute Absenteeism %: (absent_count / total_manpower) * 100
        if self.total_manpower > 0:
            self.absenteeism_rate = round((Decimal(self.absent_count) / Decimal(self.total_manpower)) * 100, 2)
        super().save(*args, **kwargs)


class MonthlyMigration(models.Model):
    unit = models.ForeignKey('CompanyUnit', on_delete=models.CASCADE, related_name='unit_migrations')
    floor = models.ForeignKey('Floor', on_delete=models.CASCADE, related_name='floor_migrations')
    month = models.DateField(help_text="First day of the month (e.g. 2026-08-01)")
    opening_manpower = models.PositiveIntegerField(default=0, help_text="Total active workforce at start of month")
    new_joined = models.PositiveIntegerField(default=0, help_text="Total recruited / transferred in")
    resigned_count = models.PositiveIntegerField(default=0, help_text="Voluntary resignations")
    separated_count = models.PositiveIntegerField(default=0, help_text="Terminations / Left / Dismissed")
    total_left = models.PositiveIntegerField(default=0, help_text="Resigned + Separated")
    closing_manpower = models.PositiveIntegerField(default=0, help_text="Total workforce at end of month")
    migration_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Calculated Turnover / Migration %")
    recorded_by = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('floor', 'month')
        ordering = ['-month', 'floor']

    def save(self, *args, **kwargs):
        self.total_left = self.resigned_count + self.separated_count
        self.closing_manpower = max(0, (self.opening_manpower + self.new_joined) - self.total_left)
        
        # Turnover formula: (Total Left / Average Manpower) * 100
        avg_manpower = (Decimal(self.opening_manpower) + Decimal(self.closing_manpower)) / Decimal('2.0')
        if avg_manpower > Decimal('0.0'):
            self.migration_rate = round((Decimal(self.total_left) / avg_manpower) * Decimal('100.0'), 2)
        else:
            self.migration_rate = Decimal('0.00')
            
        super().save(*args, **kwargs)

@receiver(post_save, sender=Employee)
def auto_create_employee_user_account(sender, instance, created, **kwargs):
    """
    Automatically creates and links an auth.User account when an Employee is created,
    or links one if it's missing. Default password: employee_code (e.g., AAL00283)
    """
    if not instance.user:
        # Generate username using employee code
        username = instance.employee_code.strip()
        user, user_created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': instance.first_name,
                'last_name': instance.last_name,
                'email': instance.email or f"{username.lower()}@company.com",
                'is_staff': True,  # Allows portal access
                'is_active': instance.is_active,
            }
        )
        if user_created:
            # Set default password as their Employee Code
            user.set_password(username)
            user.save()
        
        # Link user back to employee
        Employee.objects.filter(pk=instance.pk).update(user=user)

class FloorDisciplinaryAction(models.Model):
    ACTION_CHOICES = [
        ('VERBAL_WARNING', 'Verbal Warning'),
        ('WRITTEN_WARNING', 'Written Warning / Show Cause'),
        ('SUSPENSION', 'Suspension'),
        ('FINE_DEDUCTION', 'Fine / Salary Deduction'),
        ('DISMISSAL', 'Termination / Dismissal'),
        ('COUNSELING', 'Counseling / Retraining'),
        ('OTHER', 'Other Action'),
    ]

    unit = models.ForeignKey(CompanyUnit, on_delete=models.CASCADE, related_name='floor_disciplinary_actions')
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='disciplinary_actions')
    date = models.DateField(default=timezone.now)
    
    incident_type = models.CharField(max_length=150, help_text="e.g., Unauthorized Absence, Insubordination, Safety Violation, SOP Breach")
    action_taken = models.CharField(max_length=30, choices=ACTION_CHOICES, default='WRITTEN_WARNING')
    
    person_count = models.PositiveIntegerField(default=1, help_text="Number of persons involved")
    employee_id_card = models.CharField(max_length=100, blank=True, help_text="Employee Card/PIN (Optional)")
    
    reason = models.TextField(help_text="Detailed description of incident and action rationale")
    recorded_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_disciplinary_actions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'floor__name']
        verbose_name = "Floor Disciplinary Action"
        verbose_name_plural = "Floor Disciplinary Actions"

    def __str__(self):
        return f"{self.floor.name} - {self.get_action_taken_display()} ({self.date.strftime('%d-%b-%Y')})"


class FloorProductionKPI(models.Model):
    unit = models.ForeignKey(CompanyUnit, on_delete=models.CASCADE, related_name='unit_productions')
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='floor_productions')
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='floor_kpi_records',
        help_text="Floor In-Charge / Supervisor"
    )
    date = models.DateField(default=timezone.now)

    # 1. Target, Production Output & Efficiency
    target_quantity = models.PositiveIntegerField(default=0, help_text="Planned Target (Pcs)")
    produced_quantity = models.PositiveIntegerField(default=0, help_text="Actual Output (Pcs)")
    achievement_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    efficiency_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Line/Floor Efficiency %")

    # 2. Quality & Inspection Indicators
    dhu_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="DHU %")
    inspection_pass_qty = models.PositiveIntegerField(default=0, help_text="Inspected Pieces Passed")
    inspection_fail_qty = models.PositiveIntegerField(default=0, help_text="Inspected Pieces Failed/Rejected")

    # 3. Extra OT (Hours)
    extra_ot_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Extra Overtime Hours")

    # 4-8. Shipment Indicators
    timely_shipment_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.00, help_text="On-time Shipment %")
    excess_shipment_qty = models.PositiveIntegerField(default=0, help_text="Excess Shipment (Pcs)")
    short_shipment_qty = models.PositiveIntegerField(default=0, help_text="Short Shipment (Pcs)")
    delay_shipment_qty = models.PositiveIntegerField(default=0, help_text="Delayed Shipment (Pcs)")
    air_shipment_qty = models.PositiveIntegerField(default=0, help_text="Air Shipment (Pcs/Penalty)")

    # 9. Floor Management (5S / Housekeeping / Line balancing score 0-100)
    floor_management_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.00, help_text="Score (0-100)")

    # 10. Disciplinary Action (Count)
    disciplinary_count = models.PositiveIntegerField(default=0, help_text="Disciplinary incidents logged")

    # Composite Assessment Score (0 - 100)
    kpi_rank_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    recorded_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('floor', 'date')
        ordering = ['-date', '-kpi_rank_score']
        verbose_name = "Floor Production KPI"
        verbose_name_plural = "Floor Production KPIs"

    def save(self, *args, **kwargs):
        # 1. Target Achievement
        if self.target_quantity > 0:
            self.achievement_rate = round((Decimal(self.produced_quantity) / Decimal(self.target_quantity)) * 100, 2)
        else:
            self.achievement_rate = Decimal('0.00')

        # 2. Weighted Multi-Indicator Assessment Formula (0 - 100)
        # Production & Efficiency Score (25 pts max)
        p_score = min(Decimal('15.0'), (self.achievement_rate * Decimal('0.15')))
        eff_score = min(Decimal('10.0'), (Decimal(self.efficiency_rate) * Decimal('0.10')))

        # Quality, DHU & Inspection Pass Rate (25 pts max)
        tot_inspected = self.inspection_pass_qty + self.inspection_fail_qty
        if tot_inspected > 0:
            pass_ratio = Decimal(self.inspection_pass_qty) / Decimal(tot_inspected)
            insp_score = pass_ratio * Decimal('10.0')
        else:
            insp_score = Decimal('10.0') if self.dhu_rate <= Decimal('3.0') else Decimal('5.0')
            
        dhu_score = max(Decimal('0.0'), Decimal('15.0') - (Decimal(self.dhu_rate) * Decimal('1.5')))
        q_score = dhu_score + insp_score

        # Timely Shipment (15 pts max)
        s_timely = (Decimal(self.timely_shipment_rate) / Decimal('100.0')) * Decimal('15.0')

        # Floor Management (15 pts max)
        fm_score = (Decimal(self.floor_management_score) / Decimal('100.0')) * Decimal('15.0')

        # Overtime & Resource Control (10 pts max)
        ot_penalty = min(Decimal('10.0'), Decimal(self.extra_ot_hours) * Decimal('1.5'))
        ot_score = max(Decimal('0.0'), Decimal('10.0') - ot_penalty)

        # Non-compliance & Shipment Issue Deductions (10 pts max)
        penalties = (Decimal(self.delay_shipment_qty) * Decimal('0.5')) + \
                    (Decimal(self.air_shipment_qty) * Decimal('2.0')) + \
                    (Decimal(self.short_shipment_qty) * Decimal('0.2')) + \
                    (Decimal(self.excess_shipment_qty) * Decimal('0.1')) + \
                    (Decimal(self.disciplinary_count) * Decimal('2.5'))
        compliance_score = max(Decimal('0.0'), Decimal('10.0') - penalties)

        self.kpi_rank_score = round(p_score + eff_score + q_score + s_timely + fm_score + ot_score + compliance_score, 2)
        super().save(*args, **kwargs)

# In employees/models.py
class MonthlyFloorProductionSummary(models.Model):
    unit = models.ForeignKey(CompanyUnit, on_delete=models.CASCADE)
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    month = models.DateField(help_text="First day of the month (YYYY-MM-01)")

    # Aggregated Metrics
    days_recorded = models.PositiveIntegerField(default=0)
    total_target = models.PositiveIntegerField(default=0)
    total_produced = models.PositiveIntegerField(default=0)
    avg_efficiency = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    avg_dhu = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total_inspection_pass = models.PositiveIntegerField(default=0)
    total_inspection_fail = models.PositiveIntegerField(default=0)
    total_extra_ot = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    avg_timely_shipment = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    avg_floor_mgmt = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    total_disciplinary = models.PositiveIntegerField(default=0)
    avg_kpi_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('floor', 'month')
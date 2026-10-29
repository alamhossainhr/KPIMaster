from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from employees.models import Employee, Department, Designation
from decimal import Decimal
from employees.models import CompanyUnit

class KPI(models.Model):
    unit = models.ForeignKey(CompanyUnit, on_delete=models.CASCADE, related_name='kpis', null=True, blank=True)
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    department = models.ForeignKey('employees.Department', on_delete=models.SET_NULL, null=True, blank=True)
    designation = models.ForeignKey('employees.Designation', on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    measurement_type = models.CharField(max_length=50, default='Quantity')
    default_weight = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    default_target = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    unit_of_measure = models.CharField(max_length=30, default='Count', db_column='unit')
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"[{self.code}] {self.name}"

class PerformancePeriod(models.Model):
    PERIOD_TYPE_CHOICES = [
        ('Weekly', 'Weekly (7 Days)'),
        ('Monthly', 'Monthly (1 Month)'),
        ('Quarterly', 'Quarterly (3 Months)'),
        ('HalfYearly', 'Half-Yearly (6 Months)'),
        ('NineMonths', '9-Monthly (3 Quarters)'),
        ('Annual', 'Yearly / Annual (12 Months)'),
    ]

    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Open', 'Open'),
        ('Review', 'Review'),
        ('Closed', 'Closed'),
    ]

    name = models.CharField(max_length=100, unique=True)
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPE_CHOICES, default='Monthly')
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    is_locked = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name} [{self.get_period_type_display()}] ({self.status})"


class RatingScale(models.Model):
    name = models.CharField(max_length=50)
    min_score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=10)
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-min_score']

    def __str__(self):
        return f"{self.grade} - {self.name} ({self.min_score}% - {self.max_score}%)"


class KPI(models.Model):
    MEASUREMENT_TYPES = [
        ('Percentage', 'Percentage (%)'),
        ('Quantity', 'Quantity / Count'),
        ('Accuracy', 'Accuracy Rate (%)'),
        ('Time', 'Time / Turnaround Hours'),
        ('Completion', 'Completion Status (0-100%)'),
        ('Rating', 'Score Rating (1-10)'),
        ('Boolean', 'Yes/No (Boolean Check)'),
    ]

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='kpi_templates')
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, blank=True, related_name='kpi_templates')
    
    default_weight = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('20.00'), help_text="Default Weight %")
    measurement_type = models.CharField(max_length=30, choices=MEASUREMENT_TYPES, default='Quantity')
    default_target = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('100.00'))
    unit = models.CharField(max_length=30, default='Count')
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('100.00'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"[{self.code}] {self.name} ({self.default_weight}%)"


class KPIAssignment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='kpi_assignments')
    kpi = models.ForeignKey(KPI, on_delete=models.CASCADE, related_name='assigned_instances')
    period = models.ForeignKey(PerformancePeriod, on_delete=models.CASCADE, related_name='employee_assignments')
    weight = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    target = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=30, default='Count')
    effective_date = models.DateField()
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('employee', 'kpi', 'period')
        ordering = ['employee', '-weight']

    def __str__(self):
        return f"{self.employee.employee_code} - {self.kpi.name} ({self.weight}%)"


class AssignedTask(models.Model):
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Submitted', 'Submitted'),
        ('Completed', 'Completed'),
        ('Overdue', 'Overdue'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='assigned_tasks')
    kpi = models.ForeignKey(KPI, on_delete=models.SET_NULL, null=True, blank=True)
    assigned_date = models.DateField(null=True, blank=True)
    start_date = models.DateField()
    deadline = models.DateField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    target = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    unit = models.CharField(max_length=30, default='Count')
    points = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.00'))
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='given_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"{self.title} -> {self.employee.employee_code}"


class DailyWork(models.Model):
    CATEGORY_CHOICES = [
        ('KPI Task', 'KPI Direct Task'),
        ('Routine Task', 'Routine Operations Task'),
        ('Assigned Task', 'Supervisor Assigned Task'),
        ('Special Project', 'Special Project Task'),
    ]

    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('Submitted', 'Submitted'),
        ('Approved', 'Approved'),
        ('Partially Approved', 'Partially Approved'),
        ('Returned', 'Returned'),
        ('Rejected', 'Rejected'),
    ]

    work_date = models.DateField(db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='daily_works')
    kpi = models.ForeignKey(KPI, on_delete=models.PROTECT, related_name='daily_entries')
    assigned_task = models.ForeignKey('AssignedTask', on_delete=models.SET_NULL, null=True, blank=True)
    task_category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='KPI Task')
    
    task_title = models.CharField(max_length=200)
    task_description = models.TextField(blank=True, null=True)
    target_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    achievement_quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Employee claimed achievement")
    unit = models.CharField(max_length=30, default='Count')
    
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('100.00'))
    remarks = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Submitted', db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-work_date', '-id']

    def __str__(self):
        return f"{self.work_date} | {self.employee.employee_code} | {self.task_title}"


class TaskEvidence(models.Model):
    daily_work = models.ForeignKey(DailyWork, on_delete=models.CASCADE, related_name='evidences')
    file = models.FileField(upload_to='evidences/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.original_filename


class WorkApproval(models.Model):
    daily_work = models.OneToOneField(DailyWork, on_delete=models.CASCADE, related_name='approval')
    verified_achievement = models.DecimalField(max_digits=10, decimal_places=2, help_text="Supervisor Verified Quantity")
    
    quality_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('100.00'), validators=[MinValueValidator(0), MaxValueValidator(100)])
    timeliness_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('100.00'), validators=[MinValueValidator(0), MaxValueValidator(100)])
    supervisor_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('100.00'), validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    quantity_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    calculated_daily_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    approval_remarks = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(
        'employees.Employee', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_works'
    )
    approval_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        target = self.daily_work.target_quantity or Decimal('1.0')
        raw_qty_score = (Decimal(str(self.verified_achievement)) / Decimal(str(target))) * Decimal('100.0')
        self.quantity_score = min(Decimal('100.0'), max(Decimal('0.0'), raw_qty_score))

        self.calculated_daily_score = (
            (self.quantity_score * Decimal('0.40')) +
            (Decimal(str(self.quality_score)) * Decimal('0.30')) +
            (Decimal(str(self.timeliness_score)) * Decimal('0.20')) +
            (Decimal(str(self.supervisor_score)) * Decimal('0.10'))
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Approval for Task #{self.daily_work.id} - Score: {self.calculated_daily_score}"


class MonthlyKPI(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='monthly_kpis')
    period = models.ForeignKey(PerformancePeriod, on_delete=models.CASCADE)
    kpi = models.ForeignKey(KPI, on_delete=models.CASCADE)
    
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    total_target = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_verified_achievement = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    achievement_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    average_quality_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    average_timeliness_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    average_supervisor_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    weighted_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    final_kpi_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        unique_together = ('employee', 'period', 'kpi')

    def __str__(self):
        return f"{self.employee.employee_code} - {self.kpi.code} ({self.period.name}): {self.weighted_score}%"


class PerformanceReview(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='reviews')
    period = models.ForeignKey(PerformancePeriod, on_delete=models.CASCADE)
    
    system_generated_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    supervisor_evaluation_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    final_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    rating = models.ForeignKey(RatingScale, on_delete=models.SET_NULL, null=True, blank=True)
    
    is_overridden = models.BooleanField(default=False)
    original_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    override_reason = models.TextField(blank=True, null=True)
    overridden_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='kpi_overrides')
    
    supervisor_comments = models.TextField(blank=True, null=True)
    employee_comments = models.TextField(blank=True, null=True)
    hr_comments = models.TextField(blank=True, null=True)
    
    is_finalized = models.BooleanField(default=False)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('employee', 'period')

    def __str__(self):
        return f"Review: {self.employee.employee_code} - {self.period.name} [{self.final_score}%]"
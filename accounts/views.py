from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from kpi.models import AssignedTask, DailyWork, PerformanceReview
from employees.models import Employee

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        login_identifier = request.POST.get('username', '').strip()
        password_input = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')

        # Check if the identifier is an employee code
        resolved_username = login_identifier
        emp = Employee.objects.filter(employee_code__iexact=login_identifier).select_related('user').first()
        if emp and emp.user:
            resolved_username = emp.user.username

        user = authenticate(request, username=resolved_username, password=password_input)
        if user is not None:
            login(request, user)
            if not remember_me:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(1209600)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username/employee code or password.")

    return render(request, 'accounts/login.html')

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')

@login_required
def dashboard_view(request):
    today = timezone.now().date()
    employee = getattr(request.user, 'employee_profile', None)
    recent_tasks = AssignedTask.objects.filter(employee=employee).order_by('-assigned_date')[:5]
    if employee:
        today_works = DailyWork.objects.filter(employee=employee, work_date=today)
        recent_works = DailyWork.objects.filter(employee=employee).order_by('-work_date')[:5]
        pending_count = DailyWork.objects.filter(employee=employee, status='Submitted').count()
        completed_count = DailyWork.objects.filter(employee=employee, status__in=['Approved', 'Partially Approved']).count()
        latest_review = PerformanceReview.objects.filter(employee=employee).order_by('-period__start_date').first()
    else:
        today_works = DailyWork.objects.filter(work_date=today)
        recent_works = DailyWork.objects.all().order_by('-work_date')[:5]
        pending_count = DailyWork.objects.filter(status='Submitted').count()
        completed_count = DailyWork.objects.filter(status='Approved').count()
        latest_review = PerformanceReview.objects.all().order_by('-period__start_date').first()

    context = {
        'page_title': 'Executive Dashboard',
        'today_task_count': today_works.count(),
        'pending_count': pending_count,
        'completed_count': completed_count,
        'latest_score': latest_review.final_score if latest_review else "0.00",
        'latest_grade': latest_review.rating.name if latest_review and latest_review.rating else "Not Graded",
        'recent_works': recent_works,
    }
    return render(request, 'dashboard/index.html', context)

@login_required
def user_manual_view(request):
    """
    In-App Interactive User Manual and Best Practices Guide
    accessible to all authenticated organization staff.
    """
    return render(request, 'manual/user_manual.html', {
        'page_title': 'User Manual & Best Practices Guide'
    })
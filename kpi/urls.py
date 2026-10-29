from django.urls import path
from . import views

urlpatterns = [
    path('configuration/', views.kpi_configuration, name='kpi_list'),
    path('work/', views.daily_work_list, name='daily_work_list'),
    path('work/new/', views.daily_work_create, name='daily_work_create'),
    path('tasks/', views.my_tasks, name='my_tasks'),
    path('tasks/assign/', views.assign_task_view, name='assign_task'),
    path('work/<int:work_id>/edit/', views.daily_work_edit, name='daily_work_edit'),  # <-- ADD THIS ROUTE
    path('approvals/', views.approval_inbox, name='approval_inbox'),
    path('approvals/<int:work_id>/', views.approval_process, name='approval_process'),
    path('monthly-kpi/', views.monthly_kpi_summary, name='monthly_kpi_summary'),
    #path('performance-reviews/', views.consolidated_performance_report, name='performance_reviews'),
    path('performance-reviews/<int:review_id>/edit/', views.edit_performance_review, name='edit_performance_review'),
    path('reports/', views.consolidated_performance_report, name='reports_dashboard'),
    path('reports/export-excel/', views.export_consolidated_kpi_excel, name='export_kpi_excel'),
    path('reports/preview/', views.consolidated_report_preview, name='report_preview_pdf'),
    path('reports/employee-card/<int:review_id>/', views.single_employee_kpi_card_preview, name='employee_card_pdf'),
    path('team-work/', views.team_work_list, name='team_work_list'),
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('performance-reviews/', views.performance_reviews, name='performance_reviews'),
  
]
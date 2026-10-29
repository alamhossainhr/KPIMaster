from django.urls import path
from . import views

urlpatterns = [
    path('', views.employee_list, name='employee_list'),
    path('new/', views.employee_create, name='employee_create'),
    path('structure/', views.org_structure_manage, name='org_structure'),
    path('<int:emp_id>/', views.employee_detail, name='employee_detail'),
    path('<int:emp_id>/edit/', views.employee_edit, name='employee_edit'),
    path('<int:emp_id>/change-password/', views.employee_change_password, name='employee_change_password'),
    path('migrations/', views.monthly_migration_manage, name='monthly_migration_manage'),
    path('analytics/floors/', views.floor_analytics_summary, name='floor_analytics_summary'),
    path('disciplinary/floor/', views.floor_disciplinary_manage, name='floor_disciplinary_manage'),
    path('analytics/disciplinary/', views.floor_disciplinary_analytics, name='floor_disciplinary_analytics'),
    path('production/floor/', views.floor_production_manage, name='floor_production_manage'),
    path('ajax/employees-by-floor/', views.get_employees_by_floor, name='ajax_employees_by_floor'),
    path('attendance/floor/', views.floor_attendance_manage, name='floor_attendance_manage'),
]
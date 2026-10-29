"""
Django settings for DailyWorkKPI project.
Configured for Microsoft SQL Server, Windows Server / IIS, and Bangladesh (Asia/Dhaka).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'default-insecure-key-change-in-production')

DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,192.168.102.88').split(',')]
CSRF_TRUSTED_ORIGINS = [
    'http://192.168.102.88:8100',
    'http://127.0.0.1:8100',
    'http://localhost:8100',
    'http://127.0.0.1:8900',
    'http://localhost:8900',
]

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'accounts',
    'employees',
    'kpi',
]

JAZZMIN_SETTINGS = {
    "site_title": "KPIMaster Admin",
    "site_header": "KPIMaster Portal",
    "site_brand": "KPIMaster HR",
    "welcome_sign": "Welcome to KPIMaster Administration",
    "copyright": "KPIMaster Ltd",
    "search_model": ["employees.Employee", "auth.User"],
    "user_avatar": None,
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "KPIMaster App", "url": "/"},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user-shield",
        "auth.Group": "fas fa-users",
        "employees.Employee": "fas fa-id-badge",
        "employees.Department": "fas fa-building",
        "employees.Designation": "fas fa-user-tie",
        "employees.Floor": "fas fa-layer-group",
        "employees.CompanyUnit": "fas fa-industry",
        "employees.DailyFloorAttendance": "fas fa-user-check",
        "employees.MonthlyMigration": "fas fa-people-arrows",
        "employees.UserProfile": "fas fa-user-tag",
        "employees.Section": "fas fa-network-wired",
        "employees.SubSection": "fas fa-project-diagram",
        "employees.JobGrade": "fas fa-layer-group",
        "employees.JobLocation": "fas fa-map-marker-alt",
        
        # KPI & Task Section Icons
        "kpi.KPI": "fas fa-bullseye",
        "kpi.KPIAssignment": "fas fa-tasks",
        "kpi.AssignedTask": "fas fa-clipboard-list",
        "kpi.DailyWork": "fas fa-business-time",
        "kpi.WorkApproval": "fas fa-clipboard-check",
        "kpi.PerformancePeriod": "fas fa-calendar-alt",
        "kpi.PerformanceReview": "fas fa-star-half-alt",
        "kpi.MonthlyKPI": "fas fa-chart-pie",
        "kpi.RatingScale": "fas fa-medal",
        "kpi.TaskEvidence": "fas fa-paperclip",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "theme": "flatly",
    "dark_mode_theme": "darkly",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-primary",
    "navbar": "navbar-dark navbar-primary",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "flatly",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'DailyWorkKPI.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'kpi.context_processors.pending_notifications',
                'accounts.context_processors.user_role_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'DailyWorkKPI.wsgi.application'
ASGI_APPLICATION = 'DailyWorkKPI.asgi.application'

# Database Configuration - Microsoft SQL Server via mssql-django
DB_NAME = os.getenv('DB_NAME', 'KPIMasterDB')
DB_USER = os.getenv('DB_USER', 'sa')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '1433')
DB_DRIVER = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')

DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'OPTIONS': {
            'driver': DB_DRIVER,
            'extra_params': 'TrustServerCertificate=yes;',
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 4,
        },
    },
]

LANGUAGE_CODE = os.getenv('LANGUAGE_CODE', 'en-us')
TIME_ZONE = os.getenv('TIME_ZONE', 'Asia/Dhaka')
USE_I18N = True
USE_L10N = True
USE_TZ = True

DATE_FORMAT = 'd-M-Y'
DATETIME_FORMAT = 'd-M-Y H:i'
SHORT_DATE_FORMAT = 'd-M-Y'

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
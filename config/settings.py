from pathlib import Path
import os
import sys
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
from dotenv import load_dotenv
load_dotenv(BASE_DIR / '.env')

# ── SECRET KEY ────────────────────────────────────────────────────────────────
# Crash loudly if not set — never run with a default secret key
_secret = os.getenv("DJANGO_SECRET_KEY")
if not _secret:
    sys.exit("ERROR: DJANGO_SECRET_KEY is not set. Refusing to start.")
SECRET_KEY = _secret

# ── DEBUG ─────────────────────────────────────────────────────────────────────
# Default is FALSE — must explicitly set DEBUG=True in .env for local dev
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# ── ALLOWED HOSTS ─────────────────────────────────────────────────────────────
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

# ── INSTALLED APPS ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_celery_beat",
    "django_celery_results",
    "accounts.apps.AccountsConfig",
    "dashboard.apps.DashboardConfig",
    "company.apps.CompanyConfig",
    "assessment.apps.AssessmentConfig",
    "notifications.apps.NotificationsConfig",
    "api.apps.ApiConfig",
]

# ── MIDDLEWARE ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

# ── TEMPLATES ─────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "notifications.context_processors.unread_notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ── DATABASE ──────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "sa"),
        "USER": os.getenv("DB_USER", "skillmatch_user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "skillmatch_pass"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# ── PASSWORD VALIDATORS ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── INTERNATIONALISATION ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

# ── STATIC & MEDIA ────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ── AUTH ──────────────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:overview"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

# ── DJANGO REST FRAMEWORK ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "api.throttling.BurstUserThrottle",
        "api.throttling.SustainedUserThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "burst":      "60/min",
        "sustained":  "1000/day",
        "login_anon": "10/min",
        "login_user": "20/min",
    },
}

# ── JWT ───────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS":  True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ── CELERY ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

CELERY_BEAT_SCHEDULE = {
    "scan-interview-reminders-every-15min": {
        "task":     "notifications.scan_and_send_interview_reminders",
        "schedule": 15 * 60,
    },
}

# ── AI / GEMINI ───────────────────────────────────────────────────────────────
GOOGLE_API_KEY    = os.getenv("GOOGLE_API_KEY", "")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", GOOGLE_API_KEY)
GOOGLE_GENAI_MODEL = os.getenv("GOOGLE_GENAI_MODEL", "gemini-2.0-flash")

# ── ASSESSMENT ────────────────────────────────────────────────────────────────
ASSESSMENT_QUESTIONS_PER_ATTEMPT = int(os.getenv("ASSESSMENT_QUESTIONS_PER_ATTEMPT", "30"))
ASSESSMENT_COOLDOWN_DAYS         = int(os.getenv("ASSESSMENT_COOLDOWN_DAYS", "7"))
ASSESSMENT_TECHNICAL_WEIGHT      = float(os.getenv("ASSESSMENT_TECHNICAL_WEIGHT", "0.80"))
ASSESSMENT_SOFT_WEIGHT           = float(os.getenv("ASSESSMENT_SOFT_WEIGHT", "0.20"))
ASSESSMENT_MATCH_BUFFER          = int(os.getenv("ASSESSMENT_MATCH_BUFFER", "2"))

# ── FILE UPLOADS ──────────────────────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ── MESSAGES ──────────────────────────────────────────────────────────────────
# FallbackStorage uses server-side session first (more secure than cookie-only)
MESSAGE_STORAGE = "django.contrib.messages.storage.fallback.FallbackStorage"

# ── SITE / EMAIL ──────────────────────────────────────────────────────────────
SITE_URL          = os.getenv("SITE_URL", "http://127.0.0.1:8000")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@skillmatch.local")
EMAIL_BACKEND     = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST        = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT        = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER   = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS     = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_USE_SSL     = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"

# ── GOOGLE OAUTH ──────────────────────────────────────────────────────────────
GOOGLE_OAUTH_CLIENT_ID     = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REDIRECT_URI  = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", f"{SITE_URL}/company/google/callback/")
GOOGLE_CALENDAR_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/userinfo.email",
]

# Only allow insecure transport in local dev — never in production
if os.getenv("OAUTHLIB_INSECURE_TRANSPORT") == "1":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# ── PRODUCTION SECURITY HEADERS ───────────────────────────────────────────────
# These only activate when DEBUG=False
if not DEBUG:
    SECURE_SSL_REDIRECT            = True
    SECURE_HSTS_SECONDS            = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD            = True
    SESSION_COOKIE_SECURE          = True
    CSRF_COOKIE_SECURE             = True
    SESSION_COOKIE_HTTPONLY        = True
    CSRF_COOKIE_HTTPONLY           = True
    SECURE_CONTENT_TYPE_NOSNIFF    = True
    SECURE_REFERRER_POLICY         = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS                = "DENY"
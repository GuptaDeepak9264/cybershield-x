"""
CyberShield X - Django settings.

Django here owns authentication, roles, session management, and the
server-rendered dashboard shell. FastAPI and Flask (added in later
milestones) talk to the SAME MySQL database, so schema changes made
here must stay migration-tracked and never be hand-edited on the DB.
"""

from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Core / security
# ---------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Local apps
    "apps.accounts",
    "apps.security",
    "apps.notifications",
]

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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
#
# DB_ENGINE defaults to "mysql" for production/staging parity with FastAPI
# and Flask, which read the same schema. "sqlite3" is only used to run the
# test suite / local `manage.py check` on machines without a MySQL server
# (e.g. CI runners, this sandbox). Never point DB_ENGINE=sqlite3 at a real
# deployment - it exists purely to keep the test loop fast.
# ---------------------------------------------------------------------------
DB_ENGINE = config("DB_ENGINE", default="mysql")

if DB_ENGINE == "sqlite3":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": config("DB_HOST", default="127.0.0.1"),
            "PORT": config("DB_PORT", default="3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:role_redirect"
LOGOUT_REDIRECT_URL = "accounts:login"

# ---------------------------------------------------------------------------
# JWT (for FastAPI / Flask - stateless services that can't share Django's
# session cookie). Kept as its own secret rather than reusing SECRET_KEY:
# SECRET_KEY protects session/CSRF signing for the browser app; JWT_SECRET
# protects API tokens handed to a different trust boundary (any service
# with the shared MySQL credentials can validate them). Rotating one
# should never force rotating the other.
# ---------------------------------------------------------------------------
JWT_SECRET = config("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = config("JWT_EXPIRATION_MINUTES", default=60, cast=int)

# ---------------------------------------------------------------------------
# Downstream services (Milestone 5 integration). Django acts as the
# browser-facing gateway: it mints a short-lived JWT for the logged-in
# user and calls these over plain HTTP, rather than exposing FastAPI/Flask
# directly to the browser. See apps/integrations/clients.py.
# ---------------------------------------------------------------------------
FASTAPI_BASE_URL = config("FASTAPI_BASE_URL", default="http://127.0.0.1:8001")
FLASK_BASE_URL = config("FLASK_BASE_URL", default="http://127.0.0.1:8002")
INTEGRATION_TIMEOUT_SECONDS = config("INTEGRATION_TIMEOUT_SECONDS", default=10, cast=int)

# ---------------------------------------------------------------------------
# Session / CSRF hardening
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_HTTPONLY = False  # JS front end (later milestones) needs to read this for API calls
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=not DEBUG, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=not DEBUG, cast=bool)
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = config("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise: Django serves its own compressed, cache-busted static files
# in production, no separate static host needed. This is what replaces
# "Frontend: Vercel" from the original plan - there's no standalone
# frontend build to deploy there (the UI is server-rendered Django
# templates), so a static-file host is the wrong tool; WhiteNoise serving
# from the same process Django already runs is simpler and correct here.
# See DEPLOYMENT.md for the full reasoning.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # ManifestStaticFilesStorage requires collectstatic to have already
        # run (it resolves {% static %} tags via a generated manifest
        # file) - fine for production after the Render build step, but it
        # breaks `manage.py test` and local `runserver` with a fresh
        # checkout. WhiteNoise's own docs recommend exactly this DEBUG
        # branch for that reason.
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

# ---------------------------------------------------------------------------
# Media (scan uploads, generated reports)
#
# Local disk (default, DEV_MEDIA below) works for local dev and for the
# single-host setup used in Milestones 1-5, where django-service and
# flask-service happen to share a filesystem. That assumption does NOT
# hold once each service is its own Render container with its own
# ephemeral disk - so production (USE_S3=True) switches to S3-compatible
# object storage instead. flask-service's pdf_report.py has the matching
# upload-instead-of-write-local-disk branch; both point at the same
# bucket so Django's FileField and Flask's writer agree on where files live.
# ---------------------------------------------------------------------------
USE_S3 = config("USE_S3", default=False, cast=bool)

if USE_S3:
    STORAGES["default"] = {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"}
    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="us-east-1")
    # Set this for S3-compatible non-AWS providers (Cloudflare R2,
    # Backblaze B2, DigitalOcean Spaces); leave unset for real AWS S3.
    AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL", default=None)
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = config("AWS_QUERYSTRING_AUTH", default=True, cast=bool)
    AWS_S3_FILE_OVERWRITE = False
    MEDIA_URL = config("MEDIA_URL_OVERRIDE", default=f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/")
else:
    MEDIA_URL = "media/"
    MEDIA_ROOT = BASE_DIR / "media"

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB before spooling to disk

# ---------------------------------------------------------------------------
# Production hardening, active whenever DEBUG=False. Every value below is
# still env-overridable so local/staging setups aren't forced into it.
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=not DEBUG, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0 if DEBUG else 60 * 60 * 24 * 7, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # Render terminates TLS at its edge proxy

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

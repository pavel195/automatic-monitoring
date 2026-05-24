import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "corsheaders",
    "django_prometheus",
    "tickets",
    "ingestion",
    "routing",
    "analytics",
    "companies",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "monolith.urls"

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

WSGI_APPLICATION = "monolith.wsgi.application"
ASGI_APPLICATION = "monolith.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "transport"),
        "USER": os.getenv("POSTGRES_USER", "transport"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "transport"),
        "HOST": os.getenv("POSTGRES_HOST", "postgres"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

CORS_ALLOW_ALL_ORIGINS = True

SPECTACULAR_SETTINGS = {
    "TITLE": "Transport Feedback API",
    "DESCRIPTION": "MVP платформы мониторинга обращений пассажиров.",
    "VERSION": "0.1.0",
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CHANNEL_POLL_INTERVAL_SECONDS = env_float("CHANNEL_POLL_INTERVAL_SECONDS", 1.0)
TELEGRAM_POLL_INTERVAL_SECONDS = env_float(
    "TELEGRAM_POLL_INTERVAL_SECONDS", CHANNEL_POLL_INTERVAL_SECONDS
)
VK_POLL_INTERVAL_SECONDS = env_float("VK_POLL_INTERVAL_SECONDS", CHANNEL_POLL_INTERVAL_SECONDS)
POLL_LOCK_TTL_SECONDS = env_int("POLL_LOCK_TTL_SECONDS", 30)
TELEGRAM_LONG_POLL_TIMEOUT = env_int("TELEGRAM_LONG_POLL_TIMEOUT", 0)
VK_LONG_POLL_WAIT_SECONDS = env_int("VK_LONG_POLL_WAIT_SECONDS", 1)
CELERY_BEAT_SCHEDULE = {
    "sla_watchdog": {
        "task": "routing.tasks.sla_watchdog",
        "schedule": 60.0,
    },
    "poll_telegram": {
        "task": "ingestion.tasks.poll_telegram",
        "schedule": TELEGRAM_POLL_INTERVAL_SECONDS,
    },
    "poll_vk": {
        "task": "ingestion.tasks.poll_vk",
        "schedule": VK_POLL_INTERVAL_SECONDS,
    },
}

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_MONITOR_CHAT_ID = os.getenv("TELEGRAM_MONITOR_CHAT_ID", "")

ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://elasticsearch:9200")

# Ollama LLM
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "30"))
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"

PROMETHEUS_EXPORT_MIGRATIONS = False

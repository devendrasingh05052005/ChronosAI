import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Zero-Dependency Local .env Parser ---
env_file = BASE_DIR / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

SECRET_KEY = os.environ.get('SECRET_KEY', 'chronosai-secret-key-change-in-production-xj7k2m9p4q')

DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'scheduler_api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'scheduler_api' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
# SISTec operations align to India Standard Time for lecture reminders
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Reminder deduplication cache (Redis DB 1; LocMem fallback for local demo) ─
REDIS_CACHE_URL = os.environ.get('REDIS_CACHE_URL', 'redis://127.0.0.1:6379/1')
CHRONOSAI_REMINDER_DEDUP_TTL = int(os.environ.get('CHRONOSAI_REMINDER_DEDUP_TTL', '7200'))
# Set to false for local dev without Redis (uses LocMem only; single-process)
CHRONOSAI_DEDUP_REDIS_ENABLED = (
    os.environ.get('CHRONOSAI_DEDUP_REDIS_ENABLED', 'true').lower() == 'true'
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'chronosai-default',
    },
    'reminder_dedup': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_CACHE_URL,
        'OPTIONS': {
            'socket_connect_timeout': 0.5,
            'socket_timeout': 0.5,
        },
    },
    'reminder_dedup_fallback': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'chronosai-reminder-dedup-fallback',
    },
}

# ── Logging (views, tasks, scheduling validators) ─────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} — {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'chronosai': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'chronosai.tasks': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'chronosai.scheduling': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ── Celery / Redis (flip CELERY_TASK_ALWAYS_EAGER to False for distributed mode)
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Local demo: synchronous inline execution (no Redis worker required)
CELERY_TASK_ALWAYS_EAGER = os.environ.get('CELERY_TASK_ALWAYS_EAGER', 'true').lower() == 'true'
CELERY_TASK_EAGER_PROPAGATES = True

# Periodic lecture reminders — requires: celery -A core beat -l info
CELERY_BEAT_SCHEDULE = {
    'check-lectures-every-minute': {
        'task': 'scheduler_api.tasks.check_and_send_daily_lecture_reminders',
        'schedule': 60.0,
        'options': {'expires': 55},
    },
}

# Groq API Key — set via environment variable in production
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

# Gemini API Key for zero-cost high-volume timetable OCR structurization
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

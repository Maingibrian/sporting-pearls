"""
Sporting Pearls backend settings — environment driven (reads .env from the
project root; real environment variables always win over .env values).
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env():
    env_path = BASE_DIR / '.env'
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, val = line.split('=', 1)
        os.environ.setdefault(key.strip(), val.strip())


_load_env()


def env(key, default=''):
    return os.environ.get(key, default)


def env_bool(key, default='0'):
    return env(key, default).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(key, default=''):
    return [x.strip() for x in env(key, default).split(',') if x.strip()]


SECRET_KEY = env('DJANGO_SECRET_KEY', 'django-insecure-change-me-in-production')

DEBUG = env_bool('DEBUG', '0')

# Comma-separated host list. "*" keeps deploys on Railway/Render preview
# domains painless; tighten it once the final domain is known.
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', '*') or ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'submissions',
    'parents',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Phase 2 — CSP/Permissions-Policy/COOP on every response, and a
    # per-IP throttle on the Django admin login form.
    'submissions.middleware.SecurityHeadersMiddleware',
    'submissions.middleware.AdminLoginThrottle',
]

ROOT_URLCONF = 'sporting_pearls_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sporting_pearls_backend.wsgi.application'

# SQLite by default. Point DB_PATH at a mounted volume (Railway/Render) to
# keep submissions across deploys, e.g. DB_PATH=/data/db.sqlite3
DB_PATH = env('DB_PATH', str(BASE_DIR / 'db.sqlite3'))

# ── Phase 5: optional PostgreSQL (R14/R20/R28) ───────────────────────
# SQLite stays the default (single-host kit, zero extra moving parts).
# When the academy outgrows it — concurrent writers, shared login-throttle
# counters across gunicorn workers — set DB_ENGINE=postgres plus the
# DB_* values below. Requires the psycopg driver:
#   uv pip install psycopg[binary]   (or: pip install psycopg[binary])
# The SP_ENV=production fail-closed guard is unaffected by this choice.
if env('DB_ENGINE', '').strip().lower() in ('postgres', 'postgresql'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME', 'sporting_pearls'),
            'USER': env('DB_USER', 'sporting'),
            'PASSWORD': env('DB_PASSWORD', ''),
            'HOST': env('DB_HOST', '127.0.0.1'),
            'PORT': env('DB_PORT', '5432'),
            'CONN_MAX_AGE': int(env('DB_CONN_MAX_AGE', '60')),
        },
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': DB_PATH,
        },
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]

# ── Phase 2: sessions, auth, response headers ────────────────────────
# Sessions die after 12h of age (tunable). Login CSRF + cookies stay
# SameSite=Lax; cookies are HttpOnly; secure flags below as before.
SESSION_COOKIE_AGE = int(env('SESSION_COOKIE_AGE', '43200'))
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
# One-use password-reset links (portal + parents) expire after 1 hour
# by default (Django's default is three days — far too long).
PASSWORD_RESET_TIMEOUT = int(env('PASSWORD_RESET_TIMEOUT', '3600'))

# Response hardening (SecurityMiddleware / XFrameOptions middleware)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'
# HSTS: 0 (off) by default so plain-HTTP LAN installs keep working.
# The nginx --with-tls front already sends HSTS for the whole origin
# (static site included) — set SECURE_HSTS_SECONDS in .env only for
# direct-HTTPS hosts without the nginx front (e.g. Railway/Render).
SECURE_HSTS_SECONDS = int(env('SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('HSTS_INCLUDE_SUBDOMAINS', '0')

# Logging: security events land on stderr/journald (gunicorn captures
# them). Only usernames-as-pks, audiences and IPs are logged — never
# credentials, reset tokens or report content.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'sp': {'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'sp'},
    },
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'WARNING',
                           'propagate': False},
        'sporting.auth': {'handlers': ['console'], 'level': 'INFO',
                          'propagate': False},
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}

LANGUAGE_CODE = 'en'
TIME_ZONE = env('TIME_ZONE', 'Africa/Nairobi')
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Uploaded player photos. On Railway point MEDIA_ROOT at the mounted
# volume so photos survive deploys, e.g. MEDIA_ROOT=/data/media
MEDIA_URL = 'media/'
MEDIA_ROOT = env('MEDIA_ROOT', str(BASE_DIR / 'media'))
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    # Non-manifest storage: admin pages never 500 if collectstatic was
    # missed; WhiteNoise still compresses and cache-headers everything.
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── CORS: the static site calls this API from the browser ──────────────
# Default: allow all (simplest for the first deploy).
# For production set CORS_ALLOW_ALL=0 and CORS_ALLOWED_ORIGINS=https://your-site.com
CORS_ALLOW_ALL_ORIGINS = env_bool('CORS_ALLOW_ALL', '1')
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS')

# ── Email (Resend) ─────────────────────────────────────────────────────
RESEND_API_KEY = env('RESEND_API_KEY')
EMAIL_TO = env('EMAIL_TO', 'info@sportingpearlsacademy.org')                 # inbox that receives submissions
EMAIL_FROM = env('EMAIL_FROM', 'info@sportingpearlsacademy.org')  # sender on the verified domain
AUTO_REPLY = env_bool('AUTO_REPLY', '1')              # branded confirmation to the visitor
BRAND_NAME = env('BRAND_NAME', 'Sporting Pearls Football Academy')
# Demo/QC mode: set to an inbox address and every outbound portal email is
# redirected there (subject prefixed [QC→original]). Leave unset in production.
SP_MAIL_REDIRECT = env('SP_MAIL_REDIRECT', '')

# ── Safeguarding (Phase 1) ─────────────────────────────────────────────
# The Designated Safeguarding Officer's inbox. New form-10 reports send a
# MINIMAL notification here ("a report is waiting in the DSO desk" + link —
# never the narrative, child name or reporter identity). Leave unset and no
# notification is sent at all; reports are then only visible inside the
# access-controlled /portal/dso/ desk. NEVER set this to a shared/general
# academy inbox.
DSO_EMAIL = env('DSO_EMAIL', '')

# ── Website origin ─────────────────────────────────────────────────────
# Where the static website lives (for "read the user guide" links on the
# portal sign-in pages). Written by install.sh; empty hides the links.
SITE_URL = env('SITE_URL', '').rstrip('/')

# ── Anti-spam ──────────────────────────────────────────────────────────
# Per-IP per-form submissions per minute (honeypot handled in the view).
RATE_LIMIT_PER_MINUTE = int(env('RATE_LIMIT_PER_MINUTE', '8'))

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'sp-default',
    }
}

# ── Phase 5 (R28): shared cache for multi-worker deployments ─────────
# LocMemCache is per-process: login-throttle counters reset on restart
# and stay per-worker. With PostgreSQL available, set SP_CACHE=db to
# move them into the database (shared by every gunicorn worker).
# One-time setup after switching:  python manage.py createcachetable
if env('SP_CACHE', '').strip().lower() == 'db':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'sp_cache',
        }
    }

# Behind an nginx / Railway / Render proxy set TRUST_PROXY_HEADER=1 in
# .env so HTTPS is detected from X-Forwarded-Proto. Default OFF: with
# the header trusted unconditionally, a direct-exposure deployment
# would let clients spoof "I am HTTPS" and poison redirect/cookie
# decisions. install.sh --with-nginx writes it automatically.
def _proxy_ssl_header(raw):
    """'1'/'true'/'on' -> trust X-Forwarded-Proto; anything else -> None."""
    return ('HTTP_X_FORWARDED_PROTO', 'https') \
        if str(raw or '').strip().lower() in ('1', 'true', 'yes', 'on') else None


SECURE_PROXY_SSL_HEADER = _proxy_ssl_header(env('TRUST_PROXY_HEADER', '0'))
# TLS hardening: install.sh --with-tls flips these in .env once certificates
# are actually issued. Defaults keep plain-HTTP LAN installs working.
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', '0')
# Secure cookies by default; set SESSION_COOKIE_SECURE=0 / CSRF_COOKIE_SECURE=0
# in .env for plain-HTTP installs (e.g. LAN kit deployments without TLS).
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', '1')
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', '1')
# Comma-separated origins allowed for CSRF when the site is served from a
# different origin than the API, e.g. http://localhost:8020,http://192.168.1.5:8020
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')

CSRF_FAILURE_VIEW = 'parents.views.csrf_failure'

# ── Operating mode: fail closed in production ──────────────────────────
# SP_ENV=production activates hard startup checks. Every entrypoint that
# imports this module — gunicorn workers, every manage.py command — refuses
# to boot when the configuration is insecure. Development (the default)
# stays permissive so LAN/kit installs keep working out of the box.
#
# Guarded conditions (see PRODUCTION-READINESS.md §6):
#   * DEBUG=1
#   * ALLOWED_HOSTS empty or containing "*"
#   * CORS_ALLOW_ALL=1 (wildcard CORS)
#   * DJANGO_SECRET_KEY missing / known placeholder / shorter than 50 chars
#   * SESSION_COOKIE_SECURE=0 or CSRF_COOKIE_SECURE=0
INSECURE_SECRET_KEYS = {
    'django-insecure-change-me-in-production',
    'change-me', 'changeme', 'secret', 'secret-key', 'insecure-key',
    'please-change-me', 'replace-me', 'sp-secret-key', 'sporting-pearls-secret',
}

SP_ENV = env('SP_ENV', 'development').strip().lower()


def _production_problems():
    """List every reason the current configuration is unsafe for production."""
    problems = []
    if DEBUG:
        problems.append('DEBUG=1 (debug pages and stack traces would be exposed)')
    if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
        problems.append('ALLOWED_HOSTS is empty or contains "*" (wildcard host)')
    if CORS_ALLOW_ALL_ORIGINS:
        problems.append('CORS_ALLOW_ALL=1 (wildcard CORS — any website could call the API)')
    _key = env('DJANGO_SECRET_KEY', '')
    if not _key:
        problems.append('DJANGO_SECRET_KEY is not set')
    elif _key.strip().lower() in INSECURE_SECRET_KEYS or len(_key) < 50:
        problems.append('DJANGO_SECRET_KEY is a known placeholder or shorter than 50 chars')
    if not SESSION_COOKIE_SECURE:
        problems.append('SESSION_COOKIE_SECURE=0 (session cookie would travel over plain HTTP)')
    if not CSRF_COOKIE_SECURE:
        problems.append('CSRF_COOKIE_SECURE=0 (CSRF cookie would travel over plain HTTP)')
    return problems


if SP_ENV == 'production':
    _problems = _production_problems()
    if _problems:
        raise ImproperlyConfigured(
            'Sporting Pearls refuses to start: SP_ENV=production with an insecure '
            'configuration. Fix backend/.env (or the real environment variables) '
            'and try again:\n  - ' + '\n  - '.join(_problems) + '\n\n'
            'Template: backend/.env.production.example — details: PRODUCTION-READINESS.md §6.'
        )
    print('[settings] SP_ENV=production — hard security checks passed.')

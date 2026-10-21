"""
Django settings for Weather-Aware Truck Routing.
All secrets and service URLs come from environment variables.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-dev-key")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")
# Always allow Vercel / local hosts (merge with env so misconfigured env can't break deploy)
_ALLOWED_DEFAULTS = {
    "localhost",
    "127.0.0.1",
    ".vercel.app",
    ".onrender.com",
}
_ALLOWED_FROM_ENV = {
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
    if h.strip()
}
ALLOWED_HOSTS = sorted(_ALLOWED_DEFAULTS | _ALLOWED_FROM_ENV)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "routes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,"
        "https://truck-weather-route.vercel.app,"
        "https://frontend-nine-chi-u07luqtijn.vercel.app",
    ).split(",")
    if o.strip()
]

# Always allow Vercel preview / production aliases (*.vercel.app)
# so domain renames / redirects don't break CORS again.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://[\w.-]+\.vercel\.app$",
]
if os.getenv("CORS_ALLOW_VERCEL_PREVIEWS", "True").lower() not in (
    "1",
    "true",
    "yes",
):
    CORS_ALLOWED_ORIGIN_REGEXES = []

CORS_ALLOW_CREDENTIALS = False
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
CORS_PREFLIGHT_MAX_AGE = 86400

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
}

# --- Third-party service config (env-driven) ---
ORS_API_KEY = os.getenv("ORS_API_KEY", "").strip()
ORS_BASE_URL = os.getenv("ORS_BASE_URL", "https://api.openrouteservice.org").rstrip("/")
OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org").rstrip("/")
NOMINATIM_BASE_URL = os.getenv(
    "NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org"
).rstrip("/")
GEOCODER_USER_AGENT = os.getenv(
    "GEOCODER_USER_AGENT", "WeatherTruckRouting/1.0"
)
OPEN_METEO_BASE_URL = os.getenv(
    "OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast"
).rstrip("/")
DEFAULT_SAMPLE_INTERVAL_MILES = float(
    os.getenv("DEFAULT_SAMPLE_INTERVAL_MILES", "25")
)

"""
Django settings for mtg_championship_site project.

Generated by 'django-admin startproject' using Django 4.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from dataclasses import dataclass
from pathlib import Path
import os
import datetime
from datetime import date
import logging
from prometheus_client import Info
from django.contrib.messages import constants as messages

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
try:
    SECRET_KEY = os.environ["SECRET_KEY"]
except KeyError:
    logging.warning("Using insecure dev key.")
    SECRET_KEY = "django-insecure-8g+wfs#fbtjgv98n!449i9ml%kgi!6(9&_)6%!0#p=4ne#i&qq"

# SECURITY WARNING: don't run with debug turned on in production!
if "RUN_IN_PROD" in os.environ:
    DEBUG = False
    ALLOWED_HOSTS = ["0.0.0.0", "leoninleague.ch", "unityleague.ch"]
    CSRF_TRUSTED_ORIGINS = ["https://leoninleague.ch", "https://unityleague.ch"]
    PROMETHEUS_METRICS_EXPORT_PORT_RANGE = range(8001, 8004)
    PROMETHEUS_METRICS_EXPORT_ADDRESS = ""  # all addresses
else:
    DEBUG = True
    ALLOWED_HOSTS = []


DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": "mtg_championship_site.settings.should_show_toolbar",
    "DEBUG_TOOLBAR_USERS": set(["antoinealb", "jari"]),
}


def should_show_toolbar(request):
    """Whether or not to show Django's debug toolbar.

    Here we check if the users are in an allowlist of users."""
    if DEBUG:
        return True

    return request.user.username in DEBUG_TOOLBAR_CONFIG["DEBUG_TOOLBAR_USERS"]


# Application definition

INSTALLED_APPS = [
    "championship",
    "invoicing",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "crispy_forms",
    "crispy_bootstrap5",
    "django_prometheus",
    "django_bleach",
    "debug_toolbar",
    "rest_framework",
    "sass_processor",
    "auditlog",
    "cid.apps.CidAppConfig",
    "hijack",
    "hijack.contrib.admin",
    "django_tex",
    "tinymce",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "hijack.middleware.HijackUserMiddleware",
]

ROOT_URLCONF = "mtg_championship_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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
    {
        "NAME": "tex",
        "BACKEND": "django_tex.engine.TeXEngine",
        "APP_DIRS": True,
    },
]

WSGI_APPLICATION = "mtg_championship_site.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

db_path = os.getenv("DB_PATH")
if not db_path:
    db_path = BASE_DIR / "db.sqlite3"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": db_path,
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

TIME_ZONE = "Europe/Zurich"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "sass_processor.finders.CssFinder",
]

SASS_PROCESSOR_ENABLED = True
SASS_PRECISION = 8


STATIC_ROOT = BASE_DIR / "static_root"

WHITENOISE_ROOT = STATIC_ROOT / "root"

# Required as we lazily generate CSS files from Sass
WHITENOISE_AUTOREFRESH = True

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Override the name of some alert messages to match what they are named in
# Boostrap.
MESSAGE_TAGS = {
    messages.ERROR: "danger",
}

# List of IPs that Django Debug Toolbar will show the debug information to.
if DEBUG:
    INTERNAL_IPS = ["127.0.0.1"]

# Export release version as a metric. The commit_sha.txt file is populated by
# the CI build.
build_info = Info("app_version", "Stores information about the version of the software")
try:
    with open(BASE_DIR / "commit_sha.txt") as f:
        commit_hash = f.read().strip()
except FileNotFoundError:
    commit_hash = "<unknown>"

build_info.info({"commit_sha": commit_hash})

# Maximum age for an event to enter result in (effetively disables backfill).
EVENT_MAX_AGE_FOR_RESULT_ENTRY = datetime.timedelta(days=31)

# Forces Django to create a correlation Id for requests rather than expect it
# from the load balancer.
CID_GENERATE = True

# Include the correlation ID in the audit log. Useful to identify operations
# that all stem from the same place, such as one "merge players" operation.
import cid.locals

AUDITLOG_CID_GETTER = cid.locals.get_cid

BLEACH_ALLOWED_TAGS = [
    "a",
    "b",
    "blockquote",
    "em",
    "i",
    "li",
    "ol",
    "p",
    "strong",
    "ul",
]


@dataclass
class Season:
    name: str
    start_date: datetime.date
    end_date: datetime.date


SEASON = {
    1: Season(
        start_date=date(2023, 1, 1), end_date=date(2023, 10, 31), name="2023 Season"
    ),
    2: Season(
        start_date=date(2023, 11, 1), end_date=date(2024, 10, 31), name="2024 Season"
    ),
}

DEFAULT_SEASON_ID = 1

INFO_TEXT_DEFAULT_SEASON_ID = 1

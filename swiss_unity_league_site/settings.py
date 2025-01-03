# Copyright 2024 Leonin League
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Django settings for the Swiss Unity League project.

Generated by 'django-admin startproject' using Django 4.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

import datetime
import logging
import os
import platform
import sys
from pathlib import Path

from django.contrib.messages import constants as messages

import cid.locals
from prometheus_client import Gauge

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
else:
    DEBUG = True

try:
    ALLOWED_HOSTS = os.environ["ALLOWED_HOSTS"].split(";")
except KeyError:
    ALLOWED_HOSTS = []

try:
    CSRF_TRUSTED_ORIGINS = os.environ["CSRF_TRUSTED_ORIGINS"].split(";")
except KeyError:
    CSRF_TRUSTED_ORIGINS = []

SITE_ID = int(os.environ.get("SITE_ID", 1))

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": "swiss_unity_league_site.settings.should_show_toolbar",
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
    # keep-sorted start
    "api",
    "articles",
    "auditlog",
    "championship",
    "cid.apps.CidAppConfig",
    "crispy_bootstrap5",
    "crispy_forms",
    "debug_toolbar",
    "decklists",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.gis",
    "django.contrib.humanize",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "django_bleach",
    "django_countries",
    "django_prometheus",
    "django_tex",
    "file_storage_db",
    "geo",
    "hijack",
    "hijack.contrib.admin",
    "info",
    "invoicing",
    "legal",
    "multisite",
    "oracle",
    "rest_framework",
    "rest_framework.authtoken",
    "robotstxt",
    "sass_processor",
    "tinymce",
    "waffle",
    # keep-sorted end
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
    "waffle.middleware.WaffleMiddleware",
    "geo.middleware.GeoIpMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "hijack.middleware.HijackUserMiddleware",
]

ROOT_URLCONF = "swiss_unity_league_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                # keep-sorted start
                "articles.context_processors.articles",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
                "swiss_unity_league_site.context_processors.current_site",
                "swiss_unity_league_site.context_processors.debug",
                # keep-sorted end
            ],
        },
    },
    {
        "NAME": "tex",
        "BACKEND": "django_tex.engine.TeXEngine",
        "APP_DIRS": True,
    },
]

WSGI_APPLICATION = "swiss_unity_league_site.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

db_path = os.getenv("DB_PATH")
if not db_path:
    db_path = os.path.join(BASE_DIR, "db.sqlite3")

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.spatialite",
        "NAME": db_path,
        "TEST": {
            "DEPENDENCIES": [],
        },
    },
    "oracle": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "oracle.sqlite3"),
        "TEST": {
            "DEPENDENCIES": [],
        },
    },
}
DATABASE_ROUTERS = ["oracle.db_routers.OracleRouter"]


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
build_info = Gauge(
    "app_version",
    "Stores information about the version of the software",
    ["commit", "debug_mode"],
)
try:
    with open(BASE_DIR / "commit_sha.txt") as f:
        commit_hash = f.read().strip()
except FileNotFoundError:
    commit_hash = "<unknown>"

build_info.labels(commit=commit_hash, debug_mode=int(DEBUG)).set(1)


# Maximum age for an event to enter result in (effetively disables backfill).
EVENT_MAX_AGE_FOR_RESULT_ENTRY = datetime.timedelta(days=31)

# Forces Django to create a correlation Id for requests rather than expect it
# from the load balancer.
CID_GENERATE = True

# Include the correlation ID in the audit log. Useful to identify operations
# that all stem from the same place, such as one "merge players" operation.
AUDITLOG_CID_GETTER = cid.locals.get_cid

BLEACH_ALLOWED_TAGS = [
    "a",
    "b",
    "em",
    "i",
    "li",
    "ol",
    "p",
    "strong",
    "ul",
    "br",
]

BLEACH_ALLOWED_TAGS_ARTICLE = BLEACH_ALLOWED_TAGS + ["h2", "h3", "h4"]


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

if cache_location := os.getenv("CACHE_LOCATION"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": cache_location,
        }
    }

# Minimum interval between two organizer registration attempts from a single IP.
REGISTRATION_ATTEMPTS_MIN_INTERVAL = datetime.timedelta(hours=8).total_seconds()

# Serves static files from DB at this URl
MEDIA_URL = "media/"
STORAGES = {
    "default": {
        "BACKEND": "file_storage_db.storage.DatabaseFileStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Settings for API views
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ]
}

if sendgrid_api_key := os.getenv("SENDGRID_API_KEY"):
    # Email settings, see https://docs.sendgrid.com/for-developers/sending-email/django
    EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"
    SENDGRID_API_KEY = sendgrid_api_key
    SENDGRID_TRACK_EMAIL_OPENS = False
    SENDGRID_TRACK_CLICKS_HTML = False
    SENDGRID_TRACK_CLICKS_PLAIN = False
else:
    # During development log emails to the console
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Those people will receive emails when an exception arise
ADMINS = [("Antoine", "antoinea101@gmail.com")]
SERVER_EMAIL = "django@unityleague.ch"
DEFAULT_FROM_EMAIL = "noreply@unityleague.ch"

DEFAULT_COUNTRY = "CH"

if "test" in sys.argv or "pytest" in sys.modules:
    # Set some options for faster unit testing in Django See:
    # https://docs.djangoproject.com/en/5.0/topics/testing/overview/
    # https://medium.com/@thehackadda/tips-for-speeding-up-your-django-tests-35bab8250760

    # Use a fake geocoding API that always return the same place.
    GEO_GEOCODER = {
        "BACKEND": "geo.tests.utils.FakeGeocoder",
    }

    # Use a fast, insecure password hasher
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]

    # Those middleware are not needed in tests but slow down everything
    middleware_to_remove = [
        "django_prometheus.middleware.PrometheusBeforeMiddleware",
        "django.middleware.security.SecurityMiddleware",
        "whitenoise.middleware.WhiteNoiseMiddleware",
        "auditlog.middleware.AuditlogMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        "django_prometheus.middleware.PrometheusAfterMiddleware",
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        "hijack.middleware.HijackUserMiddleware",
    ]
    for middleware in middleware_to_remove:
        MIDDLEWARE.remove(middleware)

    # Remove useless slow apps
    apps_to_remove = [
        "django_prometheus",
        "debug_toolbar",
        "cid.apps.CidAppConfig",
        "hijack",
        "hijack.contrib.admin",
        "auditlog",
    ]

    for app in apps_to_remove:
        INSTALLED_APPS.remove(app)

    # Finally, disable logging in unit testing
    logging.disable(logging.CRITICAL)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {message}",
            "style": "{",
        }
    },
    "handlers": {
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
    },
    "loggers": {
        # Instead of sending an email on Disallowed Host, simply log it as it is
        # quite noisy.
        "django.security.DisallowedHost": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# The age of session cookies, in seconds.
SESSION_COOKIE_AGE = datetime.timedelta(days=30).total_seconds()

GEOIP_PATH = BASE_DIR
GEOIP_CITY = "ipdb_city.mmdb"

if key := os.environ.get("GOOGLE_GEOCODING_API_KEY"):
    GEO_GEOCODER = {
        "BACKEND": "geopy.geocoders.GoogleV3",
        "KWARGS": {
            "api_key": key,
        },
    }


# https://docs.djangoproject.com/en/5.1/ref/contrib/gis/install/spatialite/
if platform.system() == "Darwin":
    SPATIALITE_LIBRARY_PATH = "/opt/homebrew/lib/mod_spatialite.dylib"


# Settings related to Waffle, a feature flag library for Django
# See https://waffle.readthedocs.io/en/stable/starting/configuring.html
WAFFLE_CREATE_MISSING_FLAGS = True
WAFFLE_CREATE_MISSING_SAMPLES = True

"""Django settings for tests."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-test-key-only-for-testing"
DEBUG = True
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tests.urls"

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
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ROOT_URLCONF = "tests.urls"
INSTALLED_APPS += [
    "django_boosted",
    "dynamic_template",
    "tests.app",
]

# Rich text in admin (same pattern as django-pymissive tests): TinyMCE via django-richtextfield.
try:
    import djrichtextfield  # noqa: F401

    INSTALLED_APPS += ["djrichtextfield"]

    _TINYMCE_API_KEY = os.environ.get("TINYMCE_API_KEY", "no-api-key")
    DJRICHTEXTFIELD_CONFIG = {
        "js": [f"//cdn.tiny.cloud/1/{_TINYMCE_API_KEY}/tinymce/5/tinymce.min.js"],
        "init_template": "djrichtextfield/init/tinymce.js",
        "settings": {
            "menubar": False,
            "plugins": "link image",
            "toolbar": "bold italic | link image | removeformat",
            "width": 700,
        },
    }
    DYNAMIC_TEMPLATE_RICHTEXT_WIDGET = "djrichtextfield.widgets.RichTextWidget"
except ImportError:
    pass
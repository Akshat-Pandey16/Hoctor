from __future__ import annotations

from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="dev-secret-key-do-not-use-in-prod")

try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE.insert(
        MIDDLEWARE.index("django.middleware.common.CommonMiddleware") + 1,
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    )
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

LOGGING["loggers"]["hoctor"]["level"] = "DEBUG"

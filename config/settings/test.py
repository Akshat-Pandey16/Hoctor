from __future__ import annotations

import tempfile
from pathlib import Path

from .base import *

DEBUG = False
SECRET_KEY = "test-secret-key"
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

HOCTOR["MODEL_DIR"] = Path(tempfile.mkdtemp(prefix="hoctor-models-"))
HOCTOR["SCANNER_BACKEND"] = "mock"
HOCTOR["PREDICTION_MIN_SAMPLES"] = 2
HOCTOR["AP_MIN_OBSERVATIONS"] = 1
HOCTOR["KNN_NEIGHBORS"] = 3

LOGGING["root"]["level"] = "ERROR"

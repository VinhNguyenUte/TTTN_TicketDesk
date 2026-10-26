from .base import *  # noqa: F403

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-ddngjz*1#wg&a5$il3zwd5$8lrghtdu9dhi_=y!)30ms_f4(at"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

# Email backend cho môi trường dev (in ra terminal)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

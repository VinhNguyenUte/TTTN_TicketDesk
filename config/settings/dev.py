import os

from .base import *  # noqa: F403

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-ticketdesk-secret-key-123456",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Database
POSTGRES_DB = os.getenv("POSTGRES_DB", "ticketdesk")
POSTGRES_USER = os.getenv("POSTGRES_USER", "ticketdesk_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "ticketdesk_pass")
POSTGRES_HOST = os.getenv(
    "POSTGRES_HOST", "localhost"
)  # Mặc định localhost cho máy thật, trong Docker ghi đè thành 'db'
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": POSTGRES_DB,
        "USER": POSTGRES_USER,
        "PASSWORD": POSTGRES_PASSWORD,
        "HOST": POSTGRES_HOST,
        "PORT": POSTGRES_PORT,
    }
}

# Email backend cho môi trường dev (in ra terminal)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Cấu hình django-debug-toolbar cho môi trường dev (chỉ kích hoạt khi đã cài đặt)
try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS = list(INSTALLED_APPS) + ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + list(  # noqa: F405
        MIDDLEWARE  # noqa: F405
    )

    INTERNAL_IPS = [
        "127.0.0.1",
        "localhost",
    ]

    # Cho phép debug toolbar hiển thị trong môi trường Docker
    if os.path.exists("/.dockerenv"):
        try:
            import socket

            hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
            INTERNAL_IPS += [ip[: ip.rfind(".")] + ".1" for ip in ips]
        except Exception:
            pass
except ImportError:
    pass

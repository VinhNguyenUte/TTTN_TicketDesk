import os

from .base import *  # noqa: F403

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Lấy SECRET_KEY từ biến môi trường của hệ thống server
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

# domain hoặc IP  của server production
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")

# Database cho production
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "myproject"),
        "USER": os.environ.get("DB_USER", "myprojectuser"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "mypassword"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# Cấu hình bảo mật bổ sung cho Production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
# HTTPS
# CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_SECURE = True
# SECURE_SSL_REDIRECT = True

"""
Settings for running tests.

This file is used by Django test runner (manage.py test).
It inherits from base settings and overrides specific values for testing.
"""

from config.settings import *

# Use in-memory SQLite for faster tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable API key check in tests
API_KEY = "test-api-key"

# Use dummy cache for tests (faster than Redis)
# Note: django-ratelimit needs a shared cache, but we disable it in tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Disable rate limiting in tests (required since DummyCache doesn't work with ratelimit)
RATELIMIT_ENABLE = False

# Silence django-ratelimit warnings for tests since we disable rate limiting
SILENCED_SYSTEM_CHECKS = ["django_ratelimit.E003", "django_ratelimit.W001"]

# Use eager Celery execution for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable migrations for faster tests (optional)
# Uncomment if you want to use --keepdb flag
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
# MIGRATION_MODULES = DisableMigrations()

# Test runner configuration
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# Logging - less verbose during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

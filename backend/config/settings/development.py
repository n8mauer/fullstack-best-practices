"""
Development settings - includes debug tools and relaxed security.
"""

from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# Debug toolbar
INSTALLED_APPS += ['debug_toolbar']

MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

INTERNAL_IPS = ['127.0.0.1']

# Development cache (can be disabled for testing)
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
#     }
# }

# Email backend - console for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS - allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True

# Security settings - relaxed for development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# DRF - add browsable API in development
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
]

# Celery - eager mode for development (synchronous)
# Uncomment to run tasks synchronously without Celery worker
# CELERY_TASK_ALWAYS_EAGER = True
# CELERY_TASK_EAGER_PROPAGATES = True

# More verbose logging for development
LOGGING['loggers']['django']['level'] = 'DEBUG'
LOGGING['loggers']['apps']['level'] = 'DEBUG'

print(f"🚀 Running in DEVELOPMENT mode")
print(f"📍 Database: {DATABASES['default']['NAME']}@{DATABASES['default']['HOST']}")
print(f"💾 Cache: {CACHES['default']['LOCATION']}")

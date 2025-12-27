"""
Production settings - security hardened and optimized.
"""

from .base import *
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

DEBUG = False

# SECURITY WARNING: Update this with your production domain
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Session security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 1209600  # 2 weeks

# CSRF security
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.sendgrid.net')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@example.com')

# Celery with AmazonMQ (RabbitMQ)
CELERY_BROKER_URL = config(
    'CELERY_BROKER_URL',
    default='amqps://username:password@b-xxxxx.mq.us-east-1.amazonaws.com:5671'
)

# AmazonMQ SSL configuration
CELERY_BROKER_USE_SSL = {
    'ssl_cert_reqs': 'CERT_REQUIRED',
}

# Celery optimization for production
CELERY_BROKER_POOL_LIMIT = 10
CELERY_BROKER_CONNECTION_TIMEOUT = 30
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10

# Task configuration
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Result backend with Redis
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://redis:6379/1')
CELERY_RESULT_EXPIRES = 3600  # 1 hour

# Database optimization
DATABASES['default']['CONN_MAX_AGE'] = 600
DATABASES['default']['OPTIONS'] = {
    'connect_timeout': 10,
    'options': '-c statement_timeout=30000',  # 30 seconds
}

# Optional: Read replicas
# DATABASES['replica'] = {
#     'ENGINE': 'django.db.backends.postgresql',
#     'NAME': config('DB_NAME'),
#     'USER': config('DB_REPLICA_USER'),
#     'PASSWORD': config('DB_REPLICA_PASSWORD'),
#     'HOST': config('DB_REPLICA_HOST'),
#     'PORT': config('DB_PORT', default='5432'),
# }

# Database router for read replicas
# DATABASE_ROUTERS = ['config.db_router.ReplicaRouter']

# Sentry error tracking
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,  # 10% of transactions
        send_default_pii=False,
        environment=config('ENVIRONMENT', default='production'),
    )

# Logging - structured logging for production
LOGGING['handlers']['console']['formatter'] = 'verbose'
LOGGING['root']['level'] = 'INFO'
LOGGING['loggers']['django']['level'] = 'WARNING'
LOGGING['loggers']['apps']['level'] = 'INFO'

# Cache optimization
CACHES['default']['TIMEOUT'] = 300
CACHES['default']['OPTIONS']['CONNECTION_POOL_KWARGS']['max_connections'] = 50

# Static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Admin security
ADMIN_URL = config('ADMIN_URL', default='admin/')

print(f"🚀 Running in PRODUCTION mode")
print(f"🔒 Security: SSL={SECURE_SSL_REDIRECT}, HSTS={SECURE_HSTS_SECONDS}s")

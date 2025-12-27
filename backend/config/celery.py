"""
Celery configuration for async task processing.

This module demonstrates best practices for Celery setup:
- Auto-discovery of tasks
- Task routing by priority
- Proper configuration for AmazonMQ (RabbitMQ)
- Result backend with Redis
- Error handling and monitoring
"""

import os
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
import logging

logger = logging.getLogger(__name__)

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Create Celery app
app = Celery('myapp')

# Load configuration from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


# Define task queues with different priorities
app.conf.task_routes = {
    # High priority queue for critical tasks
    'apps.orders.tasks.process_order': {
        'queue': 'high_priority',
        'routing_key': 'high.priority',
    },
    'apps.payments.tasks.process_payment': {
        'queue': 'high_priority',
        'routing_key': 'high.priority',
    },

    # Default queue for normal tasks
    'apps.orders.tasks.send_order_confirmation': {
        'queue': 'default',
        'routing_key': 'default',
    },

    # Low priority queue for background tasks
    'apps.notifications.tasks.*': {
        'queue': 'low_priority',
        'routing_key': 'low.priority',
    },

    # Report tasks with priority-based routing
    'apps.reports.tasks.generate_report': {
        'queue': 'reports',  # Dedicated queue for report generation
        'routing_key': 'reports.generate',
    },
    'apps.reports.tasks.cleanup_expired_reports': {
        'queue': 'maintenance',
        'routing_key': 'maintenance.cleanup',
    },
}


# Task execution monitoring
@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """Log when a task starts."""
    logger.info(f'Task {task.name}[{task_id}] starting')


@task_postrun.connect
def task_postrun_handler(task_id, task, retval, *args, **kwargs):
    """Log when a task completes successfully."""
    logger.info(f'Task {task.name}[{task_id}] completed successfully')


@task_failure.connect
def task_failure_handler(task_id, exception, *args, **kwargs):
    """Log when a task fails."""
    logger.error(f'Task {task_id} failed: {exception}', exc_info=True)


# Example task for testing
@app.task(bind=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}')
    return 'Celery is working!'


@app.task
def test_task():
    """Simple test task."""
    logger.info('Test task executed successfully')
    return 'Success'


# Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'cleanup-old-sessions': {
        'task': 'apps.core.tasks.cleanup_sessions',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-expired-reports': {
        'task': 'apps.reports.tasks.cleanup_expired_reports',
        'schedule': 86400.0,  # Every day
        'options': {
            'queue': 'maintenance',
        },
    },
}

app.conf.timezone = 'UTC'


# AmazonMQ (RabbitMQ) specific configuration for production
if os.environ.get('DJANGO_SETTINGS_MODULE') == 'config.settings.production':
    """
    Production configuration with AmazonMQ (RabbitMQ).

    Best practices:
    - Use SSL/TLS for broker connection
    - Configure heartbeat for connection health
    - Set up connection pool limits
    - Enable connection retry with backoff
    """

    app.conf.update(
        # SSL/TLS configuration
        broker_use_ssl={
            'ssl_cert_reqs': 'CERT_REQUIRED',
        },

        # Connection pool configuration
        broker_pool_limit=10,
        broker_connection_timeout=30,
        broker_connection_retry=True,
        broker_connection_max_retries=10,
        broker_connection_retry_on_startup=True,

        # Heartbeat to detect broken connections
        broker_heartbeat=30,

        # Task acknowledgment settings for reliability
        task_acks_late=True,
        task_reject_on_worker_lost=True,

        # Worker optimization
        worker_prefetch_multiplier=4,
        worker_max_tasks_per_child=1000,  # Restart worker after N tasks (memory management)

        # Result backend
        result_backend_transport_options={
            'master_name': 'mymaster',
            'socket_keepalive': True,
            'socket_connect_timeout': 5,
            'retry_on_timeout': True,
        },
    )

"""
Core Celery tasks for system maintenance.

Best practices demonstrated:
- Scheduled periodic tasks
- Proper logging
- Error handling
"""

from celery import shared_task
from django.core.management import call_command
from django.contrib.sessions.models import Session
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_sessions():
    """
    Clean up expired sessions.

    This task should run periodically (e.g., daily) to remove
    expired session data from the database.
    """
    try:
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        count = expired_sessions.count()
        expired_sessions.delete()

        logger.info(f"Cleaned up {count} expired sessions")
        return f"Deleted {count} expired sessions"

    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}", exc_info=True)
        raise


@shared_task
def clear_old_cache_keys():
    """
    Clear old cache keys that are no longer needed.

    This is a placeholder for cache maintenance tasks.
    """
    logger.info("Cache cleanup task executed")
    return "Cache cleanup completed"


@shared_task
def database_backup():
    """
    Trigger database backup.

    This is a placeholder showing how to integrate backup systems.
    """
    logger.info("Database backup task executed")
    # In production, integrate with your backup solution
    # call_command('dbbackup')
    return "Backup initiated"

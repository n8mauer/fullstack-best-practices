"""
Core models providing base classes for all apps.

Best practices demonstrated:
- Abstract base models for common fields
- Soft delete functionality
- Timestamp tracking
"""

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base class that provides self-updating
    'created_at' and 'updated_at' fields.
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class SoftDeleteModel(models.Model):
    """
    Abstract base class that provides soft delete functionality.

    Instead of actually deleting records, we mark them as deleted.
    This is useful for audit trails and data recovery.
    """
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Override delete to mark as deleted instead of removing."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def hard_delete(self):
        """Actually delete the record from database."""
        super().delete()

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class BaseModel(TimeStampedModel, SoftDeleteModel):
    """
    Combination of TimeStamped and SoftDelete models.
    Use this as the base for most models.
    """
    class Meta:
        abstract = True

"""
Report models demonstrating advanced Celery patterns.

Best practices:
- Track task state in database
- Store task results
- Progress tracking
- Priority levels
- Retry tracking
"""

from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models import BaseModel
import uuid

User = get_user_model()


class Report(BaseModel):
    """
    Report generation request.

    Demonstrates:
    - Async task tracking
    - Progress monitoring
    - Priority queues
    - Result storage
    """

    class ReportType(models.TextChoices):
        SALES = 'sales', 'Sales Report'
        INVENTORY = 'inventory', 'Inventory Report'
        CUSTOMERS = 'customers', 'Customer Report'
        ORDERS = 'orders', 'Order Report'
        ANALYTICS = 'analytics', 'Analytics Report'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low Priority'
        NORMAL = 'normal', 'Normal Priority'
        HIGH = 'high', 'High Priority'
        URGENT = 'urgent', 'Urgent Priority'

    # Request details
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Parameters (stored as JSON)
    parameters = models.JSONField(
        default=dict,
        help_text="Report parameters like date range, filters, etc."
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
        db_index=True
    )

    # Task tracking
    celery_task_id = models.CharField(max_length=255, blank=True, db_index=True)
    progress = models.IntegerField(
        default=0,
        help_text="Progress percentage (0-100)"
    )
    progress_message = models.CharField(max_length=255, blank=True)

    # Results
    result_file = models.FileField(
        upload_to='reports/%Y/%m/%d/',
        blank=True,
        null=True
    )
    result_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Report summary data"
    )

    # Error tracking
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Auto-cleanup
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the report file should be deleted"
    )

    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'priority', '-created_at']),
            models.Index(fields=['report_type', '-created_at']),
            models.Index(fields=['-expires_at']),
        ]

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.title}"

    @property
    def is_processing(self):
        """Check if report is currently being processed."""
        return self.status in [self.Status.PENDING, self.Status.PROCESSING]

    @property
    def is_complete(self):
        """Check if report generation is complete."""
        return self.status == self.Status.COMPLETED

    @property
    def has_result(self):
        """Check if report has a result file."""
        return bool(self.result_file)

    @property
    def duration_seconds(self):
        """Calculate report generation duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ReportSchedule(BaseModel):
    """
    Scheduled report generation.

    Demonstrates:
    - Celery beat integration
    - Cron schedules
    - Automated report delivery
    """

    class Frequency(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
        CUSTOM = 'custom', 'Custom Cron'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='report_schedules')
    report_type = models.CharField(max_length=20, choices=Report.ReportType.choices)
    title = models.CharField(max_length=255)
    parameters = models.JSONField(default=dict)

    # Schedule
    frequency = models.CharField(max_length=20, choices=Frequency.choices)
    cron_expression = models.CharField(
        max_length=100,
        blank=True,
        help_text="Cron expression for custom schedules"
    )

    # Email delivery
    send_email = models.BooleanField(default=True)
    email_recipients = models.JSONField(
        default=list,
        help_text="List of email addresses to send report to"
    )

    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'report_schedules'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_frequency_display()})"


class ReportExecution(BaseModel):
    """
    Track individual executions of scheduled reports.

    Audit trail for scheduled report runs.
    """

    schedule = models.ForeignKey(
        ReportSchedule,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    report = models.ForeignKey(
        Report,
        on_delete=models.SET_NULL,
        null=True,
        related_name='schedule_executions'
    )

    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    execution_time_seconds = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'report_executions'
        ordering = ['-created_at']

    def __str__(self):
        return f"Execution of {self.schedule.title} at {self.created_at}"

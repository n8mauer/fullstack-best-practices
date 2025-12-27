"""
Report admin configuration.

Demonstrates:
- Custom admin actions
- Inline displays
- Filtering and search
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Report, ReportSchedule, ReportExecution


class ReportExecutionInline(admin.TabularInline):
    """Inline for report executions."""
    model = ReportExecution
    extra = 0
    readonly_fields = ['report', 'success', 'error_message', 'execution_time_seconds', 'created_at']
    can_delete = False


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Report admin with monitoring features."""

    list_display = [
        'title', 'user', 'report_type', 'status_badge',
        'priority', 'progress_bar', 'created_at', 'duration'
    ]
    list_filter = ['status', 'report_type', 'priority', 'created_at']
    search_fields = ['title', 'user__email', 'celery_task_id']
    readonly_fields = [
        'id', 'celery_task_id', 'progress', 'progress_message',
        'result_data', 'error_message', 'retry_count',
        'started_at', 'completed_at', 'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Report Information', {
            'fields': ('id', 'user', 'report_type', 'title', 'description')
        }),
        ('Parameters', {
            'fields': ('parameters',)
        }),
        ('Status', {
            'fields': ('status', 'priority', 'progress', 'progress_message')
        }),
        ('Task Information', {
            'fields': ('celery_task_id', 'retry_count')
        }),
        ('Results', {
            'fields': ('result_file', 'result_data')
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at', 'expires_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['cancel_reports', 'retry_failed_reports']

    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            Report.Status.PENDING: 'gray',
            Report.Status.PROCESSING: 'blue',
            Report.Status.COMPLETED: 'green',
            Report.Status.FAILED: 'red',
            Report.Status.CANCELLED: 'orange',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def progress_bar(self, obj):
        """Display progress as HTML bar."""
        if obj.status == Report.Status.COMPLETED:
            color = 'green'
        elif obj.status == Report.Status.FAILED:
            color = 'red'
        else:
            color = 'blue'

        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">'
            '{}%'
            '</div></div>',
            obj.progress,
            color,
            obj.progress
        )
    progress_bar.short_description = 'Progress'

    def duration(self, obj):
        """Display generation duration."""
        if obj.duration_seconds:
            return f"{obj.duration_seconds:.1f}s"
        return "-"
    duration.short_description = 'Duration'

    def cancel_reports(self, request, queryset):
        """Admin action to cancel reports."""
        from celery import current_app

        count = 0
        for report in queryset.filter(status__in=[Report.Status.PENDING, Report.Status.PROCESSING]):
            if report.celery_task_id:
                current_app.control.revoke(report.celery_task_id, terminate=True)

            report.status = Report.Status.CANCELLED
            report.save(update_fields=['status'])
            count += 1

        self.message_user(request, f'{count} reports cancelled')
    cancel_reports.short_description = 'Cancel selected reports'

    def retry_failed_reports(self, request, queryset):
        """Admin action to retry failed reports."""
        from .tasks import generate_report

        count = 0
        for report in queryset.filter(status=Report.Status.FAILED):
            report.status = Report.Status.PENDING
            report.error_message = ''
            report.save(update_fields=['status', 'error_message'])

            generate_report.delay(str(report.id))
            count += 1

        self.message_user(request, f'{count} reports queued for retry')
    retry_failed_reports.short_description = 'Retry failed reports'


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    """Report schedule admin."""

    list_display = [
        'title', 'user', 'report_type', 'frequency',
        'is_active', 'last_run', 'next_run'
    ]
    list_filter = ['is_active', 'frequency', 'report_type']
    search_fields = ['title', 'user__email']
    inlines = [ReportExecutionInline]

    fieldsets = (
        ('Schedule Information', {
            'fields': ('user', 'report_type', 'title', 'parameters')
        }),
        ('Schedule Configuration', {
            'fields': ('frequency', 'cron_expression', 'is_active')
        }),
        ('Email Settings', {
            'fields': ('send_email', 'email_recipients')
        }),
        ('Execution History', {
            'fields': ('last_run', 'next_run'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ReportExecution)
class ReportExecutionAdmin(admin.ModelAdmin):
    """Report execution history admin."""

    list_display = ['schedule', 'report', 'success', 'execution_time_seconds', 'created_at']
    list_filter = ['success', 'created_at']
    search_fields = ['schedule__title', 'error_message']
    readonly_fields = ['schedule', 'report', 'success', 'error_message', 'execution_time_seconds', 'created_at']

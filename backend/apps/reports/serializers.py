"""Report serializers."""

from rest_framework import serializers
from .models import Report, ReportSchedule, ReportExecution
from django.utils import timezone


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for Report model."""

    report_type_display = serializers.CharField(
        source='get_report_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display',
        read_only=True
    )

    # Computed fields
    is_processing = serializers.BooleanField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    has_result = serializers.BooleanField(read_only=True)
    duration_seconds = serializers.FloatField(read_only=True)

    # File URL
    result_file_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'user', 'report_type', 'report_type_display',
            'title', 'description', 'parameters',
            'status', 'status_display', 'priority', 'priority_display',
            'celery_task_id', 'progress', 'progress_message',
            'result_file', 'result_file_url', 'result_data',
            'error_message', 'retry_count',
            'started_at', 'completed_at', 'expires_at',
            'is_processing', 'is_complete', 'has_result', 'duration_seconds',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'celery_task_id', 'progress', 'progress_message',
            'result_file', 'result_data', 'error_message', 'retry_count',
            'started_at', 'completed_at', 'created_at', 'updated_at'
        ]

    def get_result_file_url(self, obj):
        """Get absolute URL for result file."""
        if obj.result_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.result_file.url)
        return None


class ReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reports."""

    class Meta:
        model = Report
        fields = [
            'report_type', 'title', 'description',
            'parameters', 'priority'
        ]

    def validate_parameters(self, value):
        """Validate parameters based on report type."""
        report_type = self.initial_data.get('report_type')

        # Required parameters by report type
        required_params = {
            Report.ReportType.SALES: ['start_date', 'end_date'],
            Report.ReportType.ORDERS: ['start_date', 'end_date'],
            Report.ReportType.ANALYTICS: ['start_date', 'end_date'],
        }

        if report_type in required_params:
            for param in required_params[report_type]:
                if param not in value:
                    raise serializers.ValidationError(
                        f"Parameter '{param}' is required for {report_type} reports"
                    )

        return value

    def create(self, validated_data):
        """Create report and trigger generation task."""
        from .tasks import generate_report

        # Set user from request
        validated_data['user'] = self.context['request'].user

        # Create report instance
        report = Report.objects.create(**validated_data)

        # Trigger async generation based on priority
        if report.priority == Report.Priority.URGENT:
            # Use high priority queue
            generate_report.apply_async(
                args=[str(report.id)],
                queue='reports_high_priority'
            )
        else:
            # Use default queue
            generate_report.delay(str(report.id))

        return report


class ReportScheduleSerializer(serializers.ModelSerializer):
    """Serializer for ReportSchedule model."""

    frequency_display = serializers.CharField(
        source='get_frequency_display',
        read_only=True
    )

    class Meta:
        model = ReportSchedule
        fields = [
            'id', 'user', 'report_type', 'title', 'parameters',
            'frequency', 'frequency_display', 'cron_expression',
            'send_email', 'email_recipients',
            'is_active', 'last_run', 'next_run',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'last_run', 'next_run', 'created_at', 'updated_at']

    def validate(self, attrs):
        """Validate schedule configuration."""
        frequency = attrs.get('frequency')
        cron_expression = attrs.get('cron_expression')

        if frequency == ReportSchedule.Frequency.CUSTOM and not cron_expression:
            raise serializers.ValidationError({
                'cron_expression': 'Cron expression is required for custom frequency'
            })

        return attrs


class ReportExecutionSerializer(serializers.ModelSerializer):
    """Serializer for ReportExecution model."""

    schedule_title = serializers.CharField(source='schedule.title', read_only=True)
    report_id = serializers.UUIDField(source='report.id', read_only=True)

    class Meta:
        model = ReportExecution
        fields = [
            'id', 'schedule', 'schedule_title', 'report', 'report_id',
            'success', 'error_message', 'execution_time_seconds',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

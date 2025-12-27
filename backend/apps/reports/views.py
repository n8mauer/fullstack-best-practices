"""
Report views demonstrating advanced API patterns.

Features:
- Report generation endpoints
- Progress tracking
- File downloads
- Task cancellation
- Schedule management
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from celery.result import AsyncResult

from .models import Report, ReportSchedule, ReportExecution
from .serializers import (
    ReportSerializer,
    ReportCreateSerializer,
    ReportScheduleSerializer,
    ReportExecutionSerializer
)


class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for report management.

    Endpoints:
    - GET /api/v1/reports/ - List user's reports
    - POST /api/v1/reports/ - Create new report
    - GET /api/v1/reports/{id}/ - Get report details
    - DELETE /api/v1/reports/{id}/ - Cancel/delete report
    - GET /api/v1/reports/{id}/progress/ - Get generation progress
    - GET /api/v1/reports/{id}/download/ - Download report file
    - POST /api/v1/reports/{id}/cancel/ - Cancel generation
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter reports by user."""
        user = self.request.user

        if user.is_staff:
            return Report.objects.all()

        return Report.objects.filter(user=user, is_deleted=False)

    def get_serializer_class(self):
        """Return appropriate serializer."""
        if self.action == 'create':
            return ReportCreateSerializer
        return ReportSerializer

    def perform_create(self, serializer):
        """Create report and start generation."""
        report = serializer.save()
        return report

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """
        Get report generation progress.

        Returns real-time progress from Celery task.
        """
        report = self.get_object()

        if not report.celery_task_id:
            return Response({
                'status': report.status,
                'progress': report.progress,
                'message': report.progress_message or 'Report not started'
            })

        # Get task result
        task_result = AsyncResult(report.celery_task_id)

        response_data = {
            'status': report.status,
            'progress': report.progress,
            'message': report.progress_message,
            'task_state': task_result.state,
        }

        # Add task-specific info if available
        if task_result.state == 'PROGRESS':
            task_info = task_result.info or {}
            response_data.update({
                'progress': task_info.get('progress', report.progress),
                'message': task_info.get('message', report.progress_message),
            })

        return Response(response_data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download report file.

        Returns the generated CSV/Excel file.
        """
        report = self.get_object()

        if not report.result_file:
            return Response({
                'error': 'Report file not available'
            }, status=status.HTTP_404_NOT_FOUND)

        if report.status != Report.Status.COMPLETED:
            return Response({
                'error': 'Report generation not complete'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            response = FileResponse(
                report.result_file.open('rb'),
                content_type='text/csv'
            )
            response['Content-Disposition'] = f'attachment; filename="{report.result_file.name}"'
            return response
        except FileNotFoundError:
            raise Http404("Report file not found")

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel report generation.

        Revokes the Celery task if still processing.
        """
        report = self.get_object()

        if report.status not in [Report.Status.PENDING, Report.Status.PROCESSING]:
            return Response({
                'error': f'Cannot cancel report with status: {report.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Revoke Celery task
        if report.celery_task_id:
            from celery import current_app
            current_app.control.revoke(report.celery_task_id, terminate=True)

        # Update report status
        report.status = Report.Status.CANCELLED
        report.save(update_fields=['status'])

        return Response({
            'message': 'Report generation cancelled',
            'status': report.status
        })

    @action(detail=False, methods=['get'])
    def types(self, request):
        """
        Get available report types.

        Returns list of report types with metadata.
        """
        report_types = []

        for choice in Report.ReportType.choices:
            report_types.append({
                'value': choice[0],
                'label': choice[1],
                'required_parameters': _get_required_parameters(choice[0])
            })

        return Response(report_types)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get user's recent reports.

        Returns last 10 reports.
        """
        recent_reports = self.get_queryset()[:10]
        serializer = self.get_serializer(recent_reports, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """
        Regenerate report with same parameters.

        Creates a new report instance with same configuration.
        """
        original_report = self.get_object()

        # Create new report
        new_report = Report.objects.create(
            user=original_report.user,
            report_type=original_report.report_type,
            title=f"{original_report.title} (Regenerated)",
            description=original_report.description,
            parameters=original_report.parameters,
            priority=original_report.priority
        )

        # Trigger generation
        from .tasks import generate_report
        generate_report.delay(str(new_report.id))

        serializer = self.get_serializer(new_report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ReportScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for scheduled reports.

    Endpoints:
    - GET /api/v1/report-schedules/ - List schedules
    - POST /api/v1/report-schedules/ - Create schedule
    - PUT /api/v1/report-schedules/{id}/ - Update schedule
    - DELETE /api/v1/report-schedules/{id}/ - Delete schedule
    - POST /api/v1/report-schedules/{id}/run-now/ - Execute immediately
    """

    serializer_class = ReportScheduleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter schedules by user."""
        user = self.request.user

        if user.is_staff:
            return ReportSchedule.objects.all()

        return ReportSchedule.objects.filter(user=user, is_deleted=False)

    def perform_create(self, serializer):
        """Create schedule with user."""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """
        Execute scheduled report immediately.

        Triggers report generation outside of schedule.
        """
        schedule = self.get_object()

        from .tasks import run_scheduled_report
        task = run_scheduled_report.delay(schedule.id)

        return Response({
            'message': 'Report generation started',
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """
        Get execution history for schedule.

        Returns past executions with success/failure info.
        """
        schedule = self.get_object()
        executions = schedule.executions.all()[:20]  # Last 20 executions

        serializer = ReportExecutionSerializer(executions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """
        Toggle schedule active status.

        Enable or disable scheduled report execution.
        """
        schedule = self.get_object()
        schedule.is_active = not schedule.is_active
        schedule.save(update_fields=['is_active'])

        return Response({
            'is_active': schedule.is_active,
            'message': f"Schedule {'activated' if schedule.is_active else 'deactivated'}"
        })


def _get_required_parameters(report_type):
    """Get required parameters for a report type."""
    parameters_map = {
        Report.ReportType.SALES: [
            {'name': 'start_date', 'type': 'date', 'label': 'Start Date'},
            {'name': 'end_date', 'type': 'date', 'label': 'End Date'}
        ],
        Report.ReportType.ORDERS: [
            {'name': 'start_date', 'type': 'date', 'label': 'Start Date'},
            {'name': 'end_date', 'type': 'date', 'label': 'End Date'},
            {'name': 'status', 'type': 'select', 'label': 'Order Status', 'required': False}
        ],
        Report.ReportType.INVENTORY: [],
        Report.ReportType.CUSTOMERS: [],
        Report.ReportType.ANALYTICS: [
            {'name': 'start_date', 'type': 'date', 'label': 'Start Date'},
            {'name': 'end_date', 'type': 'date', 'label': 'End Date'}
        ],
    }

    return parameters_map.get(report_type, [])

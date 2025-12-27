"""
Report generation tasks demonstrating advanced Celery patterns.

Best practices demonstrated:
- Task progress tracking
- Chain and group tasks
- Priority queues with AmazonMQ
- Retry with exponential backoff
- Result backends
- Task routing
- Canvas primitives (chain, group, chord)
"""

from celery import shared_task, chain, group, chord
from celery.exceptions import SoftTimeLimitExceeded
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db import transaction
from datetime import timedelta
import logging
import io
import csv
import json
from decimal import Decimal

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='apps.reports.tasks.generate_report',
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    soft_time_limit=600,  # 10 minutes
    time_limit=660,  # 11 minutes hard limit
    track_started=True,
)
def generate_report(self, report_id):
    """
    Main report generation task.

    Features:
    - Progress tracking
    - Error handling with retries
    - Task state updates
    - Result file generation

    Args:
        report_id: UUID of the Report instance

    Returns:
        dict: Report generation results
    """
    from .models import Report

    try:
        # Get report instance
        report = Report.objects.select_for_update().get(id=report_id)

        # Update status and task ID
        report.status = Report.Status.PROCESSING
        report.celery_task_id = self.request.id
        report.started_at = timezone.now()
        report.save(update_fields=['status', 'celery_task_id', 'started_at'])

        logger.info(f"Starting report generation: {report.title} (ID: {report_id})")

        # Update progress: 10%
        self.update_state(
            state='PROGRESS',
            meta={'progress': 10, 'message': 'Initializing report generation'}
        )
        report.progress = 10
        report.progress_message = 'Initializing report generation'
        report.save(update_fields=['progress', 'progress_message'])

        # Generate report based on type
        report_type = report.report_type
        parameters = report.parameters

        if report_type == Report.ReportType.SALES:
            result = _generate_sales_report(self, report, parameters)
        elif report_type == Report.ReportType.INVENTORY:
            result = _generate_inventory_report(self, report, parameters)
        elif report_type == Report.ReportType.CUSTOMERS:
            result = _generate_customers_report(self, report, parameters)
        elif report_type == Report.ReportType.ORDERS:
            result = _generate_orders_report(self, report, parameters)
        elif report_type == Report.ReportType.ANALYTICS:
            result = _generate_analytics_report(self, report, parameters)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

        # Save results
        report.result_data = result['summary']
        report.progress = 100
        report.progress_message = 'Report completed'
        report.status = Report.Status.COMPLETED
        report.completed_at = timezone.now()
        report.expires_at = timezone.now() + timedelta(days=30)

        # Save CSV file
        if 'csv_content' in result:
            filename = f"{report.report_type}_{report_id}.csv"
            report.result_file.save(
                filename,
                ContentFile(result['csv_content'].encode('utf-8')),
                save=False
            )

        report.save()

        logger.info(f"Report completed: {report.title} (ID: {report_id})")

        # Chain follow-up tasks
        chain(
            post_process_report.s(report_id),
            send_report_notification.s(report_id),
        ).apply_async()

        return {
            'status': 'success',
            'report_id': str(report_id),
            'summary': result['summary']
        }

    except SoftTimeLimitExceeded:
        logger.error(f"Report generation timeout: {report_id}")
        report.status = Report.Status.FAILED
        report.error_message = 'Report generation timed out'
        report.save(update_fields=['status', 'error_message'])
        raise

    except Exception as e:
        logger.error(f"Report generation failed: {report_id} - {str(e)}", exc_info=True)
        report.status = Report.Status.FAILED
        report.error_message = str(e)
        report.retry_count += 1
        report.save(update_fields=['status', 'error_message', 'retry_count'])
        raise


def _generate_sales_report(task, report, parameters):
    """Generate sales report with progress updates."""
    from apps.orders.models import Order
    from django.db.models import Sum, Count, Avg

    # Update progress: 30%
    task.update_state(state='PROGRESS', meta={'progress': 30, 'message': 'Fetching sales data'})
    report.progress = 30
    report.progress_message = 'Fetching sales data'
    report.save(update_fields=['progress', 'progress_message'])

    # Get date range
    start_date = parameters.get('start_date')
    end_date = parameters.get('end_date')

    # Query orders
    orders = Order.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date,
        is_deleted=False
    )

    # Update progress: 50%
    task.update_state(state='PROGRESS', meta={'progress': 50, 'message': 'Calculating metrics'})
    report.progress = 50
    report.progress_message = 'Calculating metrics'
    report.save(update_fields=['progress', 'progress_message'])

    # Calculate metrics
    metrics = orders.aggregate(
        total_orders=Count('id'),
        total_revenue=Sum('total'),
        average_order_value=Avg('total')
    )

    # Update progress: 70%
    task.update_state(state='PROGRESS', meta={'progress': 70, 'message': 'Generating CSV'})
    report.progress = 70
    report.progress_message = 'Generating CSV'
    report.save(update_fields=['progress', 'progress_message'])

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Order Number', 'Date', 'Customer', 'Total', 'Status'])

    for order in orders.select_related('user')[:1000]:  # Limit for performance
        writer.writerow([
            order.order_number,
            order.created_at.strftime('%Y-%m-%d'),
            order.user.email,
            str(order.total),
            order.status
        ])

    # Update progress: 90%
    task.update_state(state='PROGRESS', meta={'progress': 90, 'message': 'Finalizing report'})
    report.progress = 90
    report.progress_message = 'Finalizing report'
    report.save(update_fields=['progress', 'progress_message'])

    return {
        'summary': {
            'total_orders': metrics['total_orders'] or 0,
            'total_revenue': float(metrics['total_revenue'] or 0),
            'average_order_value': float(metrics['average_order_value'] or 0),
            'period': f"{start_date} to {end_date}"
        },
        'csv_content': output.getvalue()
    }


def _generate_inventory_report(task, report, parameters):
    """Generate inventory report."""
    from apps.products.models import Product

    task.update_state(state='PROGRESS', meta={'progress': 30, 'message': 'Fetching inventory data'})
    report.progress = 30
    report.save(update_fields=['progress'])

    products = Product.objects.filter(is_active=True, is_deleted=False)

    task.update_state(state='PROGRESS', meta={'progress': 70, 'message': 'Generating CSV'})
    report.progress = 70
    report.save(update_fields=['progress'])

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['SKU', 'Name', 'Category', 'Stock', 'Price', 'Status'])

    low_stock_count = 0
    out_of_stock_count = 0

    for product in products.select_related('category'):
        status = 'OK'
        if product.stock_quantity == 0:
            status = 'OUT OF STOCK'
            out_of_stock_count += 1
        elif product.is_low_stock:
            status = 'LOW STOCK'
            low_stock_count += 1

        writer.writerow([
            product.sku,
            product.name,
            product.category.name,
            product.stock_quantity,
            str(product.price),
            status
        ])

    return {
        'summary': {
            'total_products': products.count(),
            'low_stock_items': low_stock_count,
            'out_of_stock_items': out_of_stock_count,
        },
        'csv_content': output.getvalue()
    }


def _generate_customers_report(task, report, parameters):
    """Generate customers report."""
    from django.contrib.auth import get_user_model
    from apps.orders.models import Order
    from django.db.models import Count, Sum

    User = get_user_model()

    task.update_state(state='PROGRESS', meta={'progress': 30, 'message': 'Fetching customer data'})

    # Get customers with order stats
    customers = User.objects.annotate(
        order_count=Count('orders'),
        total_spent=Sum('orders__total')
    ).filter(order_count__gt=0)

    task.update_state(state='PROGRESS', meta={'progress': 70, 'message': 'Generating CSV'})

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Email', 'Name', 'Orders', 'Total Spent', 'Joined Date'])

    for customer in customers:
        writer.writerow([
            customer.email,
            customer.full_name,
            customer.order_count,
            str(customer.total_spent or 0),
            customer.date_joined.strftime('%Y-%m-%d')
        ])

    return {
        'summary': {
            'total_customers': customers.count(),
            'customers_with_orders': customers.filter(order_count__gt=0).count(),
        },
        'csv_content': output.getvalue()
    }


def _generate_orders_report(task, report, parameters):
    """Generate detailed orders report."""
    from apps.orders.models import Order
    from django.db.models import Count

    task.update_state(state='PROGRESS', meta={'progress': 30, 'message': 'Fetching order data'})

    # Get date range
    start_date = parameters.get('start_date')
    end_date = parameters.get('end_date')
    status_filter = parameters.get('status')

    orders = Order.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date,
        is_deleted=False
    )

    if status_filter:
        orders = orders.filter(status=status_filter)

    task.update_state(state='PROGRESS', meta={'progress': 70, 'message': 'Generating CSV'})

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Order Number', 'Customer', 'Date', 'Status',
        'Items', 'Subtotal', 'Tax', 'Shipping', 'Total'
    ])

    status_breakdown = orders.values('status').annotate(count=Count('id'))

    for order in orders.select_related('user').prefetch_related('items'):
        writer.writerow([
            order.order_number,
            order.user.email,
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.status,
            order.items.count(),
            str(order.subtotal),
            str(order.tax),
            str(order.shipping),
            str(order.total)
        ])

    return {
        'summary': {
            'total_orders': orders.count(),
            'status_breakdown': {item['status']: item['count'] for item in status_breakdown},
            'period': f"{start_date} to {end_date}"
        },
        'csv_content': output.getvalue()
    }


def _generate_analytics_report(task, report, parameters):
    """Generate analytics report with advanced metrics."""
    from apps.orders.models import Order
    from apps.products.models import Product
    from django.db.models import Sum, Count, Avg
    from django.db.models.functions import TruncDate

    task.update_state(state='PROGRESS', meta={'progress': 20, 'message': 'Collecting analytics'})

    start_date = parameters.get('start_date')
    end_date = parameters.get('end_date')

    # Daily sales
    daily_sales = Order.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        revenue=Sum('total'),
        orders=Count('id')
    ).order_by('date')

    task.update_state(state='PROGRESS', meta={'progress': 50, 'message': 'Analyzing products'})

    # Top products
    from apps.orders.models import OrderItem
    top_products = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        order__created_at__lte=end_date
    ).values('product__name').annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum('total')
    ).order_by('-revenue')[:10]

    task.update_state(state='PROGRESS', meta={'progress': 80, 'message': 'Generating report'})

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Orders', 'Revenue'])

    for day in daily_sales:
        writer.writerow([
            day['date'].strftime('%Y-%m-%d'),
            day['orders'],
            str(day['revenue'] or 0)
        ])

    return {
        'summary': {
            'period': f"{start_date} to {end_date}",
            'total_days': len(daily_sales),
            'top_products': list(top_products),
            'daily_average': float(
                sum(d['revenue'] or 0 for d in daily_sales) / len(daily_sales)
            ) if daily_sales else 0
        },
        'csv_content': output.getvalue()
    }


@shared_task(
    name='apps.reports.tasks.post_process_report',
    bind=True
)
def post_process_report(self, report_id):
    """
    Post-process report after generation.

    Could include:
    - Compression
    - Upload to S3
    - Generate thumbnails
    - Create summary visualizations
    """
    from .models import Report

    try:
        report = Report.objects.get(id=report_id)
        logger.info(f"Post-processing report: {report_id}")

        # Example: Could upload to S3 here
        # s3_client.upload_file(report.result_file.path, bucket, key)

        return {'status': 'success', 'report_id': str(report_id)}

    except Exception as e:
        logger.error(f"Post-processing failed for report {report_id}: {e}")
        raise


@shared_task(
    name='apps.reports.tasks.send_report_notification',
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 5, 'countdown': 30}
)
def send_report_notification(report_id):
    """
    Send notification when report is ready.

    Features:
    - Email notification with retry
    - In-app notification
    - Webhook callback (optional)
    """
    from .models import Report

    try:
        report = Report.objects.select_related('user').get(id=report_id)

        logger.info(f"Sending notification for report: {report_id}")

        # Send email (integrate with your email service)
        email_subject = f"Your {report.get_report_type_display()} is ready"
        email_body = f"""
        Hello {report.user.first_name},

        Your report "{report.title}" has been generated successfully.

        Report Details:
        - Type: {report.get_report_type_display()}
        - Generated: {report.completed_at}
        - Duration: {report.duration_seconds}s

        You can download your report from the Reports section.

        Thanks!
        """

        # Example: send_email(to=report.user.email, subject=email_subject, body=email_body)
        logger.info(f"Email sent to {report.user.email}")

        return {'status': 'success', 'sent_to': report.user.email}

    except Exception as e:
        logger.error(f"Failed to send notification for report {report_id}: {e}")
        raise


@shared_task(
    name='apps.reports.tasks.cleanup_expired_reports'
)
def cleanup_expired_reports():
    """
    Periodic task to clean up expired reports.

    This task should be configured in Celery beat schedule.
    """
    from .models import Report

    now = timezone.now()
    expired_reports = Report.objects.filter(
        expires_at__lt=now,
        is_deleted=False
    )

    count = 0
    for report in expired_reports:
        # Delete file
        if report.result_file:
            report.result_file.delete()

        # Soft delete the report
        report.delete()
        count += 1

    logger.info(f"Cleaned up {count} expired reports")
    return {'deleted_count': count}


@shared_task(
    name='apps.reports.tasks.run_scheduled_report'
)
def run_scheduled_report(schedule_id):
    """
    Execute a scheduled report.

    Called by Celery beat for scheduled reports.
    """
    from .models import ReportSchedule, Report, ReportExecution

    try:
        schedule = ReportSchedule.objects.select_related('user').get(
            id=schedule_id,
            is_active=True
        )

        start_time = timezone.now()

        # Create report instance
        report = Report.objects.create(
            user=schedule.user,
            report_type=schedule.report_type,
            title=f"{schedule.title} - {start_time.strftime('%Y-%m-%d')}",
            parameters=schedule.parameters,
            priority=Report.Priority.NORMAL
        )

        # Trigger generation
        generate_report.delay(str(report.id))

        # Update schedule
        schedule.last_run = start_time
        schedule.save(update_fields=['last_run'])

        # Record execution
        execution = ReportExecution.objects.create(
            schedule=schedule,
            report=report,
            success=True
        )

        logger.info(f"Scheduled report executed: {schedule.title}")

        return {'status': 'success', 'report_id': str(report.id)}

    except Exception as e:
        logger.error(f"Scheduled report execution failed: {schedule_id} - {e}")

        # Record failed execution
        ReportExecution.objects.create(
            schedule_id=schedule_id,
            success=False,
            error_message=str(e)
        )

        raise


# Task routing configuration for AmazonMQ
# Add to config/celery.py:
"""
app.conf.task_routes = {
    'apps.reports.tasks.generate_report': {
        'queue': 'reports_high_priority',  # For urgent reports
        'routing_key': 'reports.high',
    },
    'apps.reports.tasks.cleanup_expired_reports': {
        'queue': 'maintenance',  # Low priority queue
        'routing_key': 'maintenance.cleanup',
    },
}
"""

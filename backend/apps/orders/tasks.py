"""
Order processing tasks demonstrating Celery best practices:
- Idempotent tasks
- Proper error handling
- Retry logic
- Task chaining
- Progress tracking
"""

from celery import shared_task, chain
from celery.exceptions import SoftTimeLimitExceeded
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    soft_time_limit=300,  # 5 minutes
    name='apps.orders.tasks.process_order'
)
def process_order(self, order_id):
    """
    Process an order asynchronously.

    Best practices demonstrated:
    - Idempotent (can run multiple times safely)
    - Atomic transactions
    - Proper error handling
    - Logging
    - Progress tracking

    Args:
        order_id: ID of the order to process
    """
    from .models import Order, OrderStatusHistory

    try:
        logger.info(f"Processing order {order_id}")

        # Get order
        try:
            order = Order.objects.select_for_update().get(id=order_id)
        except Order.DoesNotExist:
            logger.error(f"Order {order_id} not found")
            return {'status': 'error', 'message': 'Order not found'}

        # Check if already processed (idempotency)
        if order.status in [Order.Status.PROCESSING, Order.Status.SHIPPED, Order.Status.DELIVERED]:
            logger.info(f"Order {order_id} already processed (status: {order.status})")
            return {'status': 'skipped', 'message': 'Order already processed'}

        # Update progress
        self.update_state(state='PROCESSING', meta={'step': 'validating'})

        # Validate inventory
        with transaction.atomic():
            for item in order.items.select_related('product'):
                if item.product.stock_quantity < item.quantity:
                    logger.warning(f"Insufficient stock for {item.product.sku}")
                    # In real app, handle this more gracefully
                    raise ValueError(f"Insufficient stock for {item.product.name}")

            # Update inventory
            self.update_state(state='PROCESSING', meta={'step': 'updating_inventory'})
            for item in order.items.select_related('product'):
                product = item.product
                product.stock_quantity -= item.quantity
                product.sales_count += item.quantity
                product.save(update_fields=['stock_quantity', 'sales_count'])

            # Update order status
            self.update_state(state='PROCESSING', meta={'step': 'updating_order'})
            order.status = Order.Status.PROCESSING
            order.save(update_fields=['status'])

            # Add status history
            OrderStatusHistory.objects.create(
                order=order,
                status=Order.Status.PROCESSING,
                notes="Order processing started"
            )

        # Invalidate product caches
        cache.delete('featured_products')

        logger.info(f"Order {order_id} processed successfully")

        # Chain to next tasks
        chain(
            send_order_confirmation.s(order_id),
            notify_warehouse.s(order_id),
        ).apply_async()

        return {
            'status': 'success',
            'order_id': order_id,
            'order_number': order.order_number
        }

    except SoftTimeLimitExceeded:
        logger.error(f"Order {order_id} processing timed out")
        raise
    except Exception as e:
        logger.error(f"Error processing order {order_id}: {e}", exc_info=True)
        # Update order to failed status or handle appropriately
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 5, 'countdown': 10},
    name='apps.orders.tasks.send_order_confirmation'
)
def send_order_confirmation(self, order_id):
    """
    Send order confirmation email.

    Best practice: Separate email sending into its own task
    with higher retry count since email services can be flaky.
    """
    from .models import Order

    try:
        order = Order.objects.get(id=order_id)

        # Simulated email sending
        logger.info(f"Sending confirmation email for order {order.order_number} to {order.email}")

        # In production, integrate with your email service
        # send_email(
        #     to=order.email,
        #     template='order_confirmation',
        #     context={'order': order}
        # )

        # Store in cache that email was sent
        cache.set(f'order_email_sent_{order_id}', True, 86400)  # 24 hours

        return {'status': 'success', 'email': order.email}

    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for email confirmation")
        return {'status': 'error', 'message': 'Order not found'}
    except Exception as e:
        logger.error(f"Error sending confirmation for order {order_id}: {e}")
        raise


@shared_task(
    name='apps.orders.tasks.notify_warehouse'
)
def notify_warehouse(order_id):
    """
    Notify warehouse system about new order.

    Best practice: Separate integration with external systems
    into dedicated tasks.
    """
    from .models import Order

    try:
        order = Order.objects.prefetch_related('items').get(id=order_id)

        # Simulated warehouse notification
        logger.info(f"Notifying warehouse about order {order.order_number}")

        # In production, integrate with your warehouse system
        # warehouse_api.create_shipment(order)

        return {'status': 'success', 'order_number': order.order_number}

    except Exception as e:
        logger.error(f"Error notifying warehouse for order {order_id}: {e}")
        # Don't retry - warehouse notifications can be handled manually if failed
        return {'status': 'error', 'message': str(e)}


@shared_task(
    name='apps.orders.tasks.update_order_status'
)
def update_order_status(order_id, new_status, notes=''):
    """
    Update order status asynchronously.

    Useful for batch status updates or external triggers.
    """
    from .models import Order, OrderStatusHistory

    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)

            old_status = order.status
            order.status = new_status

            # Update timestamps based on status
            if new_status == Order.Status.SHIPPED and not order.shipped_at:
                order.shipped_at = timezone.now()
            elif new_status == Order.Status.DELIVERED and not order.delivered_at:
                order.delivered_at = timezone.now()

            order.save()

            # Add to history
            OrderStatusHistory.objects.create(
                order=order,
                status=new_status,
                notes=notes or f"Status changed from {old_status} to {new_status}"
            )

            logger.info(f"Order {order.order_number} status updated: {old_status} -> {new_status}")

        return {
            'status': 'success',
            'order_id': order_id,
            'old_status': old_status,
            'new_status': new_status
        }

    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return {'status': 'error', 'message': 'Order not found'}
    except Exception as e:
        logger.error(f"Error updating order {order_id} status: {e}")
        raise


@shared_task(
    name='apps.orders.tasks.cancel_pending_orders'
)
def cancel_pending_orders():
    """
    Periodic task to cancel old pending orders.

    Best practice: Use periodic tasks for cleanup operations.
    This would be configured in Celery beat schedule.
    """
    from .models import Order
    from datetime import timedelta

    cutoff_time = timezone.now() - timedelta(hours=24)

    old_pending_orders = Order.objects.filter(
        status=Order.Status.PENDING,
        created_at__lt=cutoff_time
    )

    count = 0
    for order in old_pending_orders:
        order.status = Order.Status.CANCELLED
        order.save(update_fields=['status'])
        count += 1

        OrderStatusHistory.objects.create(
            order=order,
            status=Order.Status.CANCELLED,
            notes="Automatically cancelled due to timeout"
        )

    logger.info(f"Cancelled {count} pending orders older than 24 hours")
    return {'status': 'success', 'cancelled_count': count}

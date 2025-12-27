"""
Order models demonstrating best practices:
- Transaction handling
- State machines
- Audit trails
- Financial calculations
"""

from django.db import models, transaction
from django.contrib.auth import get_user_model
from apps.core.models import BaseModel
from apps.products.models import Product
from decimal import Decimal

User = get_user_model()


class Order(BaseModel):
    """
    Order model with status tracking.

    Best practices:
    - Use choices for status fields
    - Track all status changes
    - Use DecimalField for monetary values
    - Denormalize calculated fields for performance
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        CONFIRMED = 'confirmed', 'Confirmed'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'

    # User
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='orders'
    )

    # Order details
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    # Pricing (denormalized for historical accuracy)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    # Shipping information
    shipping_name = models.CharField(max_length=255)
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)

    # Contact
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    # Notes
    customer_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)

    # Timestamps
    confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['-total']),
        ]

    def __str__(self):
        return f"Order {self.order_number}"

    @transaction.atomic
    def confirm_order(self):
        """
        Confirm order and trigger processing.

        Best practice: Use atomic transactions for operations
        that modify multiple models.
        """
        from django.utils import timezone
        from .tasks import process_order

        if self.status != self.Status.PENDING:
            raise ValueError(f"Cannot confirm order with status {self.status}")

        self.status = self.Status.CONFIRMED
        self.confirmed_at = timezone.now()
        self.save(update_fields=['status', 'confirmed_at'])

        # Create status history
        OrderStatusHistory.objects.create(
            order=self,
            status=self.Status.CONFIRMED,
            notes="Order confirmed"
        )

        # Trigger async processing
        process_order.delay(self.id)

    def calculate_total(self):
        """Calculate order total from items."""
        self.subtotal = sum(
            item.total for item in self.items.all()
        )
        # Simple tax calculation (10%)
        self.tax = self.subtotal * Decimal('0.10')
        # Flat shipping
        self.shipping = Decimal('10.00')
        self.total = self.subtotal + self.tax + self.shipping


class OrderItem(BaseModel):
    """
    Order line items.

    Best practice: Denormalize product data to preserve
    historical information even if product changes.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )

    # Denormalized product data for historical record
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    quantity = models.IntegerField(default=1)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"

    def save(self, *args, **kwargs):
        """Auto-calculate total and denormalize product data."""
        # Denormalize product data
        if not self.product_name:
            self.product_name = self.product.name
        if not self.product_sku:
            self.product_sku = self.product.sku
        if not self.unit_price:
            self.unit_price = self.product.price

        # Calculate total
        self.total = self.unit_price * self.quantity

        super().save(*args, **kwargs)


class OrderStatusHistory(BaseModel):
    """
    Track all status changes for audit trail.

    Best practice: Maintain a complete audit trail of
    important state changes.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    status = models.CharField(
        max_length=20,
        choices=Order.Status.choices
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'order_status_history'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order.order_number} - {self.status}"

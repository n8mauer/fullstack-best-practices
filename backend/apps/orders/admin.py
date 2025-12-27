"""Order admin configuration."""

from django.contrib import admin
from .models import Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    """Inline for order items."""
    model = OrderItem
    extra = 0
    readonly_fields = ['total']


class OrderStatusHistoryInline(admin.TabularInline):
    """Inline for status history."""
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ['status', 'notes', 'created_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Order admin with best practices."""
    list_display = [
        'order_number', 'user', 'status', 'total',
        'created_at', 'confirmed_at'
    ]
    list_filter = ['status', 'created_at', 'confirmed_at']
    search_fields = ['order_number', 'user__email', 'email']
    readonly_fields = [
        'order_number', 'subtotal', 'tax', 'total',
        'created_at', 'confirmed_at', 'shipped_at', 'delivered_at'
    ]
    inlines = [OrderItemInline, OrderStatusHistoryInline]

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'tax', 'shipping', 'total')
        }),
        ('Shipping Information', {
            'fields': (
                'shipping_name', 'shipping_address', 'shipping_city',
                'shipping_postal_code', 'shipping_country'
            )
        }),
        ('Contact', {
            'fields': ('email', 'phone')
        }),
        ('Notes', {
            'fields': ('customer_notes', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'confirmed_at', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_processing', 'mark_as_shipped']

    def mark_as_processing(self, request, queryset):
        """Bulk action to mark orders as processing."""
        updated = queryset.update(status=Order.Status.PROCESSING)
        self.message_user(request, f'{updated} orders marked as processing')

    def mark_as_shipped(self, request, queryset):
        """Bulk action to mark orders as shipped."""
        from django.utils import timezone
        updated = queryset.update(
            status=Order.Status.SHIPPED,
            shipped_at=timezone.now()
        )
        self.message_user(request, f'{updated} orders marked as shipped')

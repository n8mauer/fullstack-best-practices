"""Order serializers."""

from rest_framework import serializers
from .models import Order, OrderItem, OrderStatusHistory
from apps.products.serializers import ProductListSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    """Order item serializer."""
    product_details = ProductListSerializer(source='product', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_details',
            'product_name', 'product_sku',
            'unit_price', 'quantity', 'total'
        ]
        read_only_fields = ['product_name', 'product_sku', 'unit_price', 'total']


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Order status history serializer."""
    class Meta:
        model = OrderStatusHistory
        fields = ['id', 'status', 'notes', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    """Detailed order serializer."""
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'user',
            'subtotal', 'tax', 'shipping', 'total',
            'shipping_name', 'shipping_address', 'shipping_city',
            'shipping_postal_code', 'shipping_country',
            'email', 'phone', 'customer_notes', 'admin_notes',
            'items', 'status_history',
            'created_at', 'confirmed_at', 'shipped_at', 'delivered_at'
        ]
        read_only_fields = [
            'order_number', 'user', 'subtotal', 'tax', 'total',
            'confirmed_at', 'shipped_at', 'delivered_at'
        ]


class OrderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating new orders.

    Best practice: Use a separate serializer for creation
    with nested item creation.
    """
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    shipping_name = serializers.CharField(max_length=255)
    shipping_address = serializers.CharField()
    shipping_city = serializers.CharField(max_length=100)
    shipping_postal_code = serializers.CharField(max_length=20)
    shipping_country = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=20)
    customer_notes = serializers.CharField(required=False, allow_blank=True)

    def validate_items(self, items):
        """Validate order items."""
        from apps.products.models import Product

        if not items:
            raise serializers.ValidationError("Order must have at least one item")

        for item in items:
            if 'product_id' not in item:
                raise serializers.ValidationError("Each item must have a product_id")
            if 'quantity' not in item:
                raise serializers.ValidationError("Each item must have a quantity")

            try:
                quantity = int(item['quantity'])
                if quantity <= 0:
                    raise serializers.ValidationError("Quantity must be positive")
            except (ValueError, TypeError):
                raise serializers.ValidationError("Invalid quantity")

            # Verify product exists and is active
            try:
                product = Product.objects.get(
                    id=item['product_id'],
                    is_active=True,
                    is_deleted=False
                )
                if product.stock_quantity < quantity:
                    raise serializers.ValidationError(
                        f"{product.name} has insufficient stock"
                    )
            except Product.DoesNotExist:
                raise serializers.ValidationError(
                    f"Product {item['product_id']} not found or inactive"
                )

        return items

    def create(self, validated_data):
        """Create order with items."""
        from django.db import transaction
        from apps.products.models import Product
        import uuid

        items_data = validated_data.pop('items')
        user = self.context['request'].user

        with transaction.atomic():
            # Create order
            order = Order.objects.create(
                user=user,
                order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
                email=user.email,
                **validated_data
            )

            # Create order items
            for item_data in items_data:
                product = Product.objects.get(id=item_data['product_id'])
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item_data['quantity']
                )

            # Calculate totals
            order.calculate_total()
            order.save()

        return order

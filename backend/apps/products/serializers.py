"""
Product serializers demonstrating best practices:
- Nested serializers for related data
- Read-only computed fields
- Different serializers for list vs detail views
"""

from rest_framework import serializers
from .models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    """Category serializer."""
    product_count = serializers.IntegerField(
        source='products.count',
        read_only=True
    )

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'product_count']


class ProductImageSerializer(serializers.ModelSerializer):
    """Product image serializer."""
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'order']


class ProductListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for product lists.

    Best practice: Use a simpler serializer for list views
    to reduce payload size and improve performance.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'short_description',
            'price', 'compare_at_price', 'is_on_sale',
            'discount_percentage', 'category_name',
            'is_active', 'is_featured', 'is_in_stock',
            'primary_image',
        ]

    def get_primary_image(self, obj):
        """Get the primary product image."""
        image = obj.images.filter(is_primary=True).first()
        if image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(image.image.url)
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for single product view.

    Best practice: Include all related data in detail view.
    """
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    # Computed fields
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'description', 'short_description',
            'price', 'compare_at_price', 'is_on_sale', 'discount_percentage',
            'stock_quantity', 'is_low_stock', 'is_in_stock',
            'category', 'images', 'is_active', 'is_featured',
            'meta_title', 'meta_description',
            'view_count', 'sales_count',
            'created_at', 'updated_at',
        ]


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating products.

    Best practice: Separate serializer for write operations
    with only writeable fields.
    """
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'description', 'short_description',
            'price', 'compare_at_price', 'stock_quantity',
            'low_stock_threshold', 'category', 'is_active',
            'is_featured', 'meta_title', 'meta_description',
        ]

    def validate_price(self, value):
        """Ensure price is positive."""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value

    def validate_stock_quantity(self, value):
        """Ensure stock quantity is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative")
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        compare_at_price = attrs.get('compare_at_price')
        price = attrs.get('price')

        if compare_at_price and compare_at_price <= price:
            raise serializers.ValidationError({
                'compare_at_price': 'Compare at price must be greater than the regular price'
            })

        return attrs

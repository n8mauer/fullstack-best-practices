"""
Product views demonstrating best practices:
- Query optimization
- Caching strategies
- Filtering and search
- Custom actions
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Product
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for product categories."""
    queryset = Category.objects.filter(is_deleted=False)
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for products with best practices.

    Features:
    - Query optimization
    - Different serializers for different actions
    - Caching
    - Filtering and search
    - Custom actions
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active', 'is_featured']
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['price', 'created_at', 'sales_count', 'view_count']
    lookup_field = 'slug'

    def get_queryset(self):
        """
        Optimize queryset with proper prefetching.

        Best practice: Only select_related and prefetch_related
        what you actually need for the current action.
        """
        queryset = Product.objects.select_related('category').filter(is_deleted=False)

        # For detail view, prefetch images
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('images')

        # Filter out inactive products for non-admin users
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)

        return queryset

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.

        Best practice: Use lightweight serializers for lists,
        detailed ones for individual items.
        """
        if self.action == 'list':
            return ProductListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        """Only admins can create/update/delete products."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def list(self, request, *args, **kwargs):
        """Cached product list."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve product and increment view count.

        Best practice: Use atomic operations for counters
        to avoid race conditions.
        """
        instance = self.get_object()

        # Increment view count (asynchronously would be better)
        Product.objects.filter(pk=instance.pk).update(
            view_count=models.F('view_count') + 1
        )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """
        Get featured products.

        Custom endpoint: /api/v1/products/featured/
        """
        # Try to get from cache first
        cache_key = 'featured_products'
        products = cache.get(cache_key)

        if products is None:
            queryset = self.filter_queryset(
                self.get_queryset().filter(
                    is_featured=True,
                    is_active=True
                )[:10]
            )
            serializer = ProductListSerializer(
                queryset,
                many=True,
                context={'request': request}
            )
            products = serializer.data
            # Cache for 1 hour
            cache.set(cache_key, products, 60 * 60)

        return Response(products)

    @action(detail=False, methods=['get'])
    def on_sale(self, request):
        """
        Get products on sale.

        Custom endpoint: /api/v1/products/on_sale/
        """
        queryset = self.filter_queryset(
            self.get_queryset().filter(
                is_active=True,
                compare_at_price__gt=models.F('price')
            )
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ProductListSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(
            queryset,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def update_stock(self, request, slug=None):
        """
        Update product stock quantity.

        Custom endpoint: /api/v1/products/{slug}/update_stock/
        """
        product = self.get_object()
        quantity = request.data.get('quantity')

        if quantity is None:
            return Response(
                {'error': 'Quantity is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(quantity)
        except ValueError:
            return Response(
                {'error': 'Quantity must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )

        product.stock_quantity = quantity
        product.save(update_fields=['stock_quantity'])

        # Invalidate caches
        cache.delete('featured_products')

        return Response({
            'message': f'Stock updated to {quantity}',
            'stock_quantity': product.stock_quantity,
            'is_in_stock': product.is_in_stock,
            'is_low_stock': product.is_low_stock,
        })


# Import models at the end to avoid circular imports
from django.db import models

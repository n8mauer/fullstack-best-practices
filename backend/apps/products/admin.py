"""Product admin configuration."""

from django.contrib import admin
from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    """Inline for product images."""
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Category admin."""
    list_display = ['name', 'slug', 'parent', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Product admin with best practices."""
    list_display = [
        'name', 'sku', 'category', 'price', 'stock_quantity',
        'is_active', 'is_featured', 'created_at'
    ]
    list_filter = ['is_active', 'is_featured', 'category', 'created_at']
    search_fields = ['name', 'sku', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    readonly_fields = ['view_count', 'sales_count', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'sku', 'category')
        }),
        ('Description', {
            'fields': ('short_description', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'compare_at_price')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'low_stock_threshold')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Metrics', {
            'fields': ('view_count', 'sales_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

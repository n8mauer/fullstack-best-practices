"""
Product models demonstrating best practices:
- Proper indexing for performance
- Decimal fields for money
- Composite indexes
- Slug fields for SEO
"""

from django.db import models
from django.utils.text import slugify
from apps.core.models import BaseModel


class Category(BaseModel):
    """Product category."""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )

    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug from name."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(BaseModel):
    """
    Product model with best practices.

    Important fields:
    - DecimalField for prices (never use FloatField for money!)
    - Indexes on frequently queried fields
    - Composite index for category+active queries
    """
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True)

    # Pricing - Use DecimalField for money, never FloatField
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Original price for showing discounts"
    )

    # Inventory
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)

    # Categorization
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,  # Don't allow deleting categories with products
        related_name='products'
    )

    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    # SEO
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)

    # Metrics
    view_count = models.IntegerField(default=0)
    sales_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
        indexes = [
            # Composite indexes for common query patterns
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['is_featured', 'is_active']),
            models.Index(fields=['-sales_count']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug and meta fields."""
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.meta_title:
            self.meta_title = self.name[:60]
        if not self.meta_description:
            self.meta_description = self.short_description[:160] or self.description[:160]
        super().save(*args, **kwargs)

    @property
    def is_on_sale(self):
        """Check if product is on sale."""
        return self.compare_at_price and self.compare_at_price > self.price

    @property
    def discount_percentage(self):
        """Calculate discount percentage."""
        if not self.is_on_sale:
            return 0
        return int(((self.compare_at_price - self.price) / self.compare_at_price) * 100)

    @property
    def is_low_stock(self):
        """Check if product is low on stock."""
        return 0 < self.stock_quantity <= self.low_stock_threshold

    @property
    def is_in_stock(self):
        """Check if product is in stock."""
        return self.stock_quantity > 0


class ProductImage(BaseModel):
    """Product images."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'product_images'
        ordering = ['order', '-is_primary']

    def __str__(self):
        return f"Image for {self.product.name}"

"""
Tests for products app.

Best practices demonstrated:
- Use pytest fixtures
- Test models, views, and serializers
- Use factory_boy for test data
- Test edge cases
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from decimal import Decimal

from .models import Category, Product

User = get_user_model()


@pytest.fixture
def api_client():
    """API client fixture."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        email='test@example.com',
        username='testuser',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def category(db):
    """Create test category."""
    return Category.objects.create(
        name='Electronics',
        description='Electronic products'
    )


@pytest.fixture
def product(db, category):
    """Create test product."""
    return Product.objects.create(
        name='Test Product',
        sku='TEST-001',
        description='Test description',
        short_description='Short description',
        price=Decimal('99.99'),
        stock_quantity=10,
        category=category,
        is_active=True
    )


@pytest.mark.django_db
class TestProductModel:
    """Test Product model."""

    def test_product_creation(self, product):
        """Test product is created correctly."""
        assert product.name == 'Test Product'
        assert product.sku == 'TEST-001'
        assert product.price == Decimal('99.99')
        assert product.slug == 'test-product'

    def test_product_str(self, product):
        """Test product string representation."""
        assert str(product) == 'Test Product'

    def test_is_on_sale(self, product):
        """Test is_on_sale property."""
        assert not product.is_on_sale

        product.compare_at_price = Decimal('149.99')
        product.save()
        assert product.is_on_sale

    def test_discount_percentage(self, product):
        """Test discount percentage calculation."""
        assert product.discount_percentage == 0

        product.compare_at_price = Decimal('149.99')
        product.save()
        assert product.discount_percentage == 33

    def test_is_in_stock(self, product):
        """Test stock status."""
        assert product.is_in_stock

        product.stock_quantity = 0
        product.save()
        assert not product.is_in_stock

    def test_is_low_stock(self, product):
        """Test low stock detection."""
        assert not product.is_low_stock

        product.stock_quantity = 5
        product.save()
        assert product.is_low_stock


@pytest.mark.django_db
class TestProductAPI:
    """Test Product API endpoints."""

    def test_list_products(self, api_client, product):
        """Test listing products."""
        response = api_client.get('/api/v1/products/')
        assert response.status_code == 200
        assert len(response.data['results']) == 1

    def test_retrieve_product(self, api_client, product):
        """Test retrieving a product."""
        response = api_client.get(f'/api/v1/products/{product.slug}/')
        assert response.status_code == 200
        assert response.data['name'] == 'Test Product'

    def test_filter_by_category(self, api_client, product):
        """Test filtering products by category."""
        response = api_client.get(f'/api/v1/products/?category={product.category.id}')
        assert response.status_code == 200
        assert len(response.data['results']) == 1

    def test_search_products(self, api_client, product):
        """Test searching products."""
        response = api_client.get('/api/v1/products/?search=Test')
        assert response.status_code == 200
        assert len(response.data['results']) == 1

        response = api_client.get('/api/v1/products/?search=Nonexistent')
        assert response.status_code == 200
        assert len(response.data['results']) == 0

    def test_create_product_requires_admin(self, api_client, user, category):
        """Test that creating products requires admin."""
        api_client.force_authenticate(user=user)

        data = {
            'name': 'New Product',
            'sku': 'NEW-001',
            'description': 'Description',
            'short_description': 'Short',
            'price': '49.99',
            'stock_quantity': 5,
            'category': category.id,
        }

        response = api_client.post('/api/v1/products/', data)
        # Regular user should not be able to create
        assert response.status_code == 403


@pytest.mark.django_db
class TestCategoryModel:
    """Test Category model."""

    def test_category_creation(self, category):
        """Test category is created correctly."""
        assert category.name == 'Electronics'
        assert category.slug == 'electronics'

    def test_category_str(self, category):
        """Test category string representation."""
        assert str(category) == 'Electronics'

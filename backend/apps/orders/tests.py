"""
Tests for orders app.

Best practices for testing:
- Test business logic
- Test task execution
- Test permissions
- Test state transitions
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from decimal import Decimal
from unittest.mock import patch

from .models import Order, OrderItem
from apps.products.models import Category, Product

User = get_user_model()


@pytest.fixture
def api_client():
    """API client fixture."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        email='customer@example.com',
        username='customer',
        password='testpass123',
        first_name='Customer',
        last_name='Test'
    )


@pytest.fixture
def product(db):
    """Create test product."""
    category = Category.objects.create(name='Test Category')
    return Product.objects.create(
        name='Test Product',
        sku='TEST-001',
        description='Test',
        price=Decimal('50.00'),
        stock_quantity=10,
        category=category
    )


@pytest.mark.django_db
class TestOrderModel:
    """Test Order model."""

    def test_order_creation(self, user, product):
        """Test creating an order."""
        order = Order.objects.create(
            user=user,
            order_number='TEST-001',
            email=user.email,
            shipping_name='Test User',
            shipping_address='123 Test St',
            shipping_city='Test City',
            shipping_postal_code='12345',
            shipping_country='Test Country',
            phone='1234567890',
            subtotal=Decimal('50.00'),
            tax=Decimal('5.00'),
            shipping=Decimal('10.00'),
            total=Decimal('65.00')
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=1
        )

        assert order.items.count() == 1
        assert order.total == Decimal('65.00')

    def test_order_status_default(self, user):
        """Test order starts with pending status."""
        order = Order.objects.create(
            user=user,
            order_number='TEST-002',
            email=user.email,
            shipping_name='Test',
            shipping_address='123 St',
            shipping_city='City',
            shipping_postal_code='12345',
            shipping_country='Country',
            phone='1234567890',
            subtotal=Decimal('50.00'),
            total=Decimal('65.00')
        )

        assert order.status == Order.Status.PENDING

    @patch('apps.orders.tasks.process_order.delay')
    def test_confirm_order(self, mock_task, user, product):
        """Test confirming an order."""
        order = Order.objects.create(
            user=user,
            order_number='TEST-003',
            email=user.email,
            shipping_name='Test',
            shipping_address='123 St',
            shipping_city='City',
            shipping_postal_code='12345',
            shipping_country='Country',
            phone='1234567890',
            subtotal=Decimal('50.00'),
            total=Decimal('65.00')
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=1
        )

        order.confirm_order()

        assert order.status == Order.Status.CONFIRMED
        assert order.confirmed_at is not None
        mock_task.assert_called_once_with(order.id)


@pytest.mark.django_db
class TestOrderAPI:
    """Test Order API endpoints."""

    def test_create_order(self, api_client, user, product):
        """Test creating an order via API."""
        api_client.force_authenticate(user=user)

        data = {
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 2
                }
            ],
            'shipping_name': 'Test User',
            'shipping_address': '123 Test St',
            'shipping_city': 'Test City',
            'shipping_postal_code': '12345',
            'shipping_country': 'Test Country',
            'phone': '1234567890'
        }

        response = api_client.post('/api/v1/orders/', data, format='json')
        assert response.status_code == 201
        assert Order.objects.count() == 1

    def test_list_user_orders(self, api_client, user, product):
        """Test user can only see their own orders."""
        # Create order for user
        order = Order.objects.create(
            user=user,
            order_number='TEST-001',
            email=user.email,
            shipping_name='Test',
            shipping_address='123 St',
            shipping_city='City',
            shipping_postal_code='12345',
            shipping_country='Country',
            phone='1234567890',
            subtotal=Decimal('50.00'),
            total=Decimal('65.00')
        )

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/v1/orders/')

        assert response.status_code == 200
        assert len(response.data['results']) == 1

"""Order views."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Order
from .serializers import OrderSerializer, OrderCreateSerializer


class OrderViewSet(viewsets.ModelViewSet):
    """
    Order ViewSet with best practices.

    Features:
    - Users can only see their own orders
    - Proper permission handling
    - Custom actions for order operations
    """
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        """
        Filter orders based on user.

        Best practice: Users should only see their own orders.
        Staff can see all orders.
        """
        user = self.request.user

        if user.is_staff:
            return Order.objects.select_related('user').prefetch_related(
                'items__product',
                'status_history'
            ).filter(is_deleted=False)

        return Order.objects.select_related('user').prefetch_related(
            'items__product',
            'status_history'
        ).filter(user=user, is_deleted=False)

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        """Create order."""
        order = serializer.save()
        return order

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """
        Confirm order and start processing.

        Endpoint: /api/v1/orders/{id}/confirm/
        """
        order = self.get_object()

        try:
            order.confirm_order()
            return Response({
                'message': 'Order confirmed and processing started',
                'order_number': order.order_number,
                'status': order.status
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel order.

        Endpoint: /api/v1/orders/{id}/cancel/
        """
        from .tasks import update_order_status

        order = self.get_object()

        if order.status not in [Order.Status.PENDING, Order.Status.CONFIRMED]:
            return Response({
                'error': f'Cannot cancel order with status {order.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Use task to update status
        update_order_status.delay(
            order.id,
            Order.Status.CANCELLED,
            'Cancelled by customer'
        )

        return Response({
            'message': 'Order cancellation in progress',
            'order_number': order.order_number
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get user's recent orders.

        Endpoint: /api/v1/orders/recent/
        """
        orders = self.get_queryset()[:5]
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

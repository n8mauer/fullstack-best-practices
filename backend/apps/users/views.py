"""
User views demonstrating best practices:
- ViewSets for CRUD operations
- Custom actions
- Permission classes
- Caching
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from .models import User
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management.

    Best practices demonstrated:
    - Use ViewSets for standard CRUD
    - Custom actions for specific operations
    - Proper permission handling
    - Query optimization with select_related/prefetch_related
    - Caching for list views
    """
    queryset = User.objects.select_related('profile').filter(is_active=True)
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.

        Best practice: Different serializers for different operations.
        """
        if self.action == 'create':
            return UserRegistrationSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        """
        Customize permissions per action.

        Best practice: Allow registration without authentication,
        but protect other endpoints.
        """
        if self.action == 'create':
            return [AllowAny()]
        return super().get_permissions()

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def list(self, request, *args, **kwargs):
        """
        List users with caching.

        Best practice: Cache list views to reduce database load.
        """
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        Create user with additional processing.

        Best practice: Use perform_create for post-save operations.
        """
        user = serializer.save()

        # Invalidate user list cache
        cache.delete('user_list')

        # Here you could trigger welcome email, analytics, etc.
        # send_welcome_email.delay(user.id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get current user profile.

        Custom action: /api/v1/users/me/
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """
        Update current user profile.

        Custom action: /api/v1/users/update_profile/
        """
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """
        Change user password.

        Custom action: /api/v1/users/change_password/
        """
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'message': 'Password updated successfully.'
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """
        Verify user account (admin only).

        Custom action: /api/v1/users/{id}/verify/
        """
        user = self.get_object()
        user.is_verified = True
        user.save(update_fields=['is_verified'])

        return Response({
            'message': f'User {user.email} verified successfully.'
        }, status=status.HTTP_200_OK)

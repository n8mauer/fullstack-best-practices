"""
URL configuration demonstrating best practices:
- API versioning
- Proper URL namespacing
- Admin URL customization for security
- Health check endpoint
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from apps.core.views import health_check, api_root

# Customize admin URL for security (configure in production settings)
admin_url = getattr(settings, 'ADMIN_URL', 'admin/')

urlpatterns = [
    # Admin
    path(admin_url, admin.site.urls),

    # Health check
    path('health/', health_check, name='health-check'),

    # API root
    path('api/', api_root, name='api-root'),

    # API v1
    path('api/v1/', include([
        # Authentication
        path('auth/', include([
            path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
            path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
            path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
        ])),

        # App endpoints
        path('users/', include('apps.users.urls')),
        path('products/', include('apps.products.urls')),
        path('orders/', include('apps.orders.urls')),
    ])),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        urlpatterns += [
            path('__debug__/', include('debug_toolbar.urls')),
        ]

# Customize admin site
admin.site.site_header = 'MyApp Administration'
admin.site.site_title = 'MyApp Admin'
admin.site.index_title = 'Welcome to MyApp Administration'

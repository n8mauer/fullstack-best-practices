"""
User admin configuration.

Best practices:
- Customize admin interface
- Add search and filters
- Inline related models
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    """Inline profile editor in user admin."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom user admin."""
    inlines = (UserProfileInline,)
    list_display = ['email', 'username', 'first_name', 'last_name', 'is_verified', 'is_active', 'date_joined']
    list_filter = ['is_verified', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-date_joined']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone', 'is_verified')}),
    )

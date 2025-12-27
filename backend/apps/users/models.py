"""
User models demonstrating best practices:
- Custom user model
- Profile information
- Proper field indexing
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.models import TimeStampedModel


class User(AbstractUser):
    """
    Custom user model.

    Best practice: Always use a custom user model from the start,
    even if you don't add extra fields initially. This makes future
    changes much easier.
    """
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)

    # Override username to make email the primary identifier
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email', 'is_active']),
            models.Index(fields=['is_verified']),
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()


class UserProfile(TimeStampedModel):
    """
    Extended user profile information.

    Best practice: Separate frequently-accessed auth data (User model)
    from profile data to optimize queries.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    # Preferences
    newsletter_subscribed = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)

    class Meta:
        db_table = 'user_profiles'

    def __str__(self):
        return f"Profile for {self.user.email}"

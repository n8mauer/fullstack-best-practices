"""
User serializers demonstrating best practices:
- Nested serializers
- Write-only fields for passwords
- Custom validation
- Method fields for computed data
"""

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""

    class Meta:
        model = UserProfile
        fields = [
            'bio', 'avatar', 'date_of_birth', 'address',
            'city', 'country', 'postal_code',
            'newsletter_subscribed', 'email_notifications',
        ]


class UserSerializer(serializers.ModelSerializer):
    """
    User serializer with nested profile.

    Best practices:
    - Nested serializers for related data
    - Read-only fields that shouldn't be updated via API
    - Computed fields with SerializerMethodField
    """
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.CharField(source='full_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'full_name', 'phone', 'is_verified', 'is_active',
            'date_joined', 'profile',
        ]
        read_only_fields = ['id', 'is_verified', 'is_active', 'date_joined']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.

    Best practices:
    - Validate passwords
    - Write-only password field
    - Custom validation
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'email', 'username', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone',
        ]

    def validate(self, attrs):
        """Validate that passwords match."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        return attrs

    def create(self, validated_data):
        """Create user with hashed password."""
        # Remove password_confirm as it's not a model field
        validated_data.pop('password_confirm')

        # Create user with hashed password
        user = User.objects.create_user(**validated_data)

        # Create associated profile
        UserProfile.objects.create(user=user)

        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user information."""

    profile = UserProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'profile']

    def update(self, instance, validated_data):
        """Update user and nested profile."""
        # Extract profile data if present
        profile_data = validated_data.pop('profile', None)

        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update profile if data provided
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change.

    Best practice: Separate serializer for password changes
    with current password validation.
    """
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_old_password(self, value):
        """Validate that old password is correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Incorrect password.')
        return value

    def validate(self, attrs):
        """Validate that new passwords match."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'New passwords do not match.'
            })
        return attrs

    def save(self):
        """Update user password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

from rest_framework import serializers
from .models import Organization, User, APIToken, PasswordResetToken, LoginHistory

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "organization", "role", "phone", "department", "bio",
            "avatar_url", "is_internal", "is_active", "is_staff",
            "last_login", "last_login_ip", "failed_login_count",
            "preferences", "date_joined", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "date_joined", "created_at", "updated_at", "last_login"]

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=4)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "password", "first_name", "last_name",
            "organization", "role", "phone", "department", "bio",
            "is_internal", "is_staff", "is_active",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "email", "phone", "department",
            "bio", "avatar_url", "role", "organization", "is_internal",
            "preferences",
        ]

class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "email",
            "role", "department", "organization", "is_internal",
            "last_login", "last_login_ip",
        ]

class LegacyUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"

class APITokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIToken
        fields = ["id", "name", "token", "is_active", "last_used", "expires_at", "created_at"]
        read_only_fields = ["id", "token", "last_used", "created_at"]

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField(max_length=10)
    new_password = serializers.CharField(min_length=4)

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=4)

class LoginHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginHistory
        fields = "__all__"

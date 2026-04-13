from rest_framework import serializers

from vulnops.access import is_org_admin, is_sys_admin

from .models import Organization, User, APIToken, PasswordResetToken, LoginHistory


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "is_active", "plan", "settings_json", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not is_org_admin(user):
            data.pop("settings_json", None)
        return data


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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            for field in ["email", "last_login_ip", "failed_login_count", "preferences", "is_staff", "is_internal"]:
                data.pop(field, None)
            return data
        if user.id == instance.id or is_org_admin(user):
            return data
        for field in ["last_login_ip", "failed_login_count", "preferences", "is_staff", "is_internal"]:
            data.pop(field, None)
        return data


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "email",
            "role", "department", "organization", "last_login", "is_active",
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=10)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "password", "first_name", "last_name",
            "organization", "role", "phone", "department", "bio",
            "is_internal", "is_staff", "is_active",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        actor = getattr(request, "user", None)

        if not actor or not actor.is_authenticated:
            attrs["role"] = "user"
            attrs["is_internal"] = False
            attrs["is_staff"] = False
            attrs["is_active"] = True
            attrs["organization"] = None
            return attrs

        if is_sys_admin(actor):
            return attrs

        attrs["is_internal"] = False
        attrs["is_staff"] = False
        attrs["is_active"] = attrs.get("is_active", True)
        requested_role = attrs.get("role", "user")
        attrs["role"] = requested_role if requested_role in {"user", "agent"} else "user"
        attrs["organization"] = actor.organization
        return attrs

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
            "preferences", "is_active", "is_staff",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        actor = getattr(request, "user", None)
        target = self.instance
        if not actor or not actor.is_authenticated:
            raise serializers.ValidationError("Authentication required.")

        if actor.id == target.id and not is_org_admin(actor):
            for field in ["role", "organization", "is_internal", "is_active", "is_staff"]:
                attrs.pop(field, None)
            return attrs

        if is_sys_admin(actor):
            return attrs

        if not is_org_admin(actor) or actor.organization_id != target.organization_id:
            raise serializers.ValidationError("You cannot update this user.")

        attrs["organization"] = actor.organization
        attrs["role"] = attrs.get("role", target.role)
        if attrs["role"] not in {"user", "agent", "org_admin", "service_account"}:
            attrs["role"] = target.role
        attrs["is_internal"] = bool(attrs.get("is_internal", target.is_internal))
        attrs["is_staff"] = False
        return attrs


class LegacyUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "organization", "role", "department", "is_active"]


class APITokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIToken
        fields = ["id", "name", "token", "is_active", "last_used", "expires_at", "created_at"]
        read_only_fields = ["id", "token", "last_used", "created_at"]


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField(max_length=128)
    new_password = serializers.CharField(min_length=10)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=10)


class LoginHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginHistory
        fields = ["id", "user", "username_attempted", "ip_address", "user_agent", "success", "created_at"]

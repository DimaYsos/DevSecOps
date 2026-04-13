import hmac
import hashlib

from django.conf import settings
from rest_framework import serializers

from vulnops.security import validate_outbound_url

from .models import WebhookConfig, WebhookDelivery


class WebhookConfigSerializer(serializers.ModelSerializer):
    secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    has_secret = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = WebhookConfig
        fields = [
            "id", "organization", "name", "url", "secret", "has_secret", "events", "is_active",
            "headers", "retry_count", "timeout_seconds", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "organization", "created_by", "has_secret"]

    def get_has_secret(self, obj):
        return bool(obj.secret)

    def validate_url(self, value):
        validate_outbound_url(value)
        return value


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = ["id", "webhook", "event_type", "payload", "status", "response_status", "attempts", "error_message", "delivered_at", "created_at"]
        read_only_fields = ["id", "created_at"]

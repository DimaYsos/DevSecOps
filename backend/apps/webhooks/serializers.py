from rest_framework import serializers
from .models import WebhookConfig, WebhookDelivery

class WebhookConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookConfig
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

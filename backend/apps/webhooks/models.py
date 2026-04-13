import uuid
from django.db import models
from django.conf import settings

class WebhookConfig(models.Model):
    EVENT_CHOICES = [
        ("ticket.created", "Ticket Created"), ("ticket.updated", "Ticket Updated"),
        ("ticket.closed", "Ticket Closed"), ("incident.created", "Incident Created"),
        ("incident.resolved", "Incident Resolved"), ("comment.created", "Comment Created"),
        ("asset.created", "Asset Created"), ("asset.updated", "Asset Updated"),
        ("all", "All Events"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="webhooks")
    name = models.CharField(max_length=200)
    url = models.URLField(max_length=500)
    secret = models.CharField(max_length=200, blank=True, default="")
    events = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    headers = models.JSONField(default=dict, blank=True)
    retry_count = models.IntegerField(default=3)
    timeout_seconds = models.IntegerField(default=10)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "webhook_configs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Webhook:{self.name} -> {self.url}"

class WebhookDelivery(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"), ("success", "Success"),
        ("failed", "Failed"), ("retrying", "Retrying"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook = models.ForeignKey(WebhookConfig, on_delete=models.CASCADE, related_name="deliveries")
    event_type = models.CharField(max_length=50)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, default="")
    response_headers = models.JSONField(default=dict, blank=True)
    attempts = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "webhook_deliveries"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Delivery:{self.event_type} -> {self.webhook.url} ({self.status})"

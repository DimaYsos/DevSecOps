import uuid
from django.db import models
from django.conf import settings

class AuditEvent(models.Model):
    ACTION_CHOICES = [
        ("create", "Create"), ("update", "Update"), ("delete", "Delete"),
        ("login", "Login"), ("logout", "Logout"), ("export", "Export"),
        ("import", "Import"), ("escalate", "Escalate"), ("assign", "Assign"),
        ("webhook", "Webhook"), ("admin", "Admin Action"), ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, default="other")
    resource_type = models.CharField(max_length=50, blank=True, default="")
    resource_id = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.action}] {self.resource_type}:{self.resource_id} by {self.user}"

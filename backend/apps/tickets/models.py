import uuid
from django.db import models
from django.conf import settings

class Ticket(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("waiting_customer", "Waiting on Customer"),
        ("waiting_vendor", "Waiting on Vendor"),
        ("escalated", "Escalated"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
        ("reopened", "Reopened"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="tickets"
    )
    title = models.CharField(max_length=300)
    description = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="open")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    category = models.CharField(max_length=100, blank=True, default="general")
    tags = models.JSONField(default=list, blank=True)

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="reported_tickets"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assigned_tickets"
    )
    sla_due_at = models.DateTimeField(null=True, blank=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    is_internal = models.BooleanField(default=False)
    internal_notes = models.TextField(blank=True, default="")
    status_override = models.CharField(max_length=50, blank=True, default="")
    custom_fields = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tickets"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.id}] {self.title}"

class Incident(models.Model):
    SEVERITY_CHOICES = [
        ("info", "Informational"),
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
        ("emergency", "Emergency"),
    ]
    STATUS_CHOICES = [
        ("detected", "Detected"),
        ("investigating", "Investigating"),
        ("identified", "Identified"),
        ("mitigating", "Mitigating"),
        ("resolved", "Resolved"),
        ("post_mortem", "Post-Mortem"),
        ("closed", "Closed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="incidents"
    )
    title = models.CharField(max_length=300)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="detected")
    affected_services = models.JSONField(default=list, blank=True)

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="reported_incidents"
    )
    commander = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="commanded_incidents"
    )

    related_tickets = models.ManyToManyField(Ticket, blank=True, related_name="incidents")
    timeline = models.JSONField(default=list, blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)

    detected_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "incidents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"INC-{self.id}: {self.title}"

class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="comments",
        null=True, blank=True
    )
    incident = models.ForeignKey(
        Incident, on_delete=models.CASCADE, related_name="comments",
        null=True, blank=True
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="comments"
    )
    content = models.TextField()
    content_html = models.TextField(blank=True, default="")
    is_internal = models.BooleanField(default=False)
    edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comments"
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.ticket or self.incident}"

class Attachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="attachments",
        null=True, blank=True
    )
    incident = models.ForeignKey(
        Incident, on_delete=models.CASCADE, related_name="attachments",
        null=True, blank=True
    )
    comment = models.ForeignKey(
        Comment, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="attachments"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="attachments"
    )
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE,
        related_name="attachments", null=True
    )
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="attachments/%Y/%m/")
    content_type = models.CharField(max_length=100, blank=True, default="")
    file_size = models.BigIntegerField(default=0)
    is_public = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "attachments"
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_filename

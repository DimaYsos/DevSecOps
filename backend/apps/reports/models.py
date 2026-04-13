import uuid
from django.db import models
from django.conf import settings

class ReportJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"), ("running", "Running"),
        ("completed", "Completed"), ("failed", "Failed"),
    ]
    FORMAT_CHOICES = [
        ("csv", "CSV"), ("xlsx", "Excel"), ("pdf", "PDF"), ("json", "JSON"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="report_jobs")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="report_jobs")
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=50, default="tickets")
    output_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default="csv")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    parameters = models.JSONField(default=dict, blank=True)
    output_file = models.FileField(upload_to="reports/%Y/%m/", null=True, blank=True)
    output_filename = models.CharField(max_length=255, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    row_count = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "report_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report:{self.name} ({self.status})"

class ImportJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"), ("processing", "Processing"),
        ("completed", "Completed"), ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="import_jobs")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="import_jobs")
    name = models.CharField(max_length=200)
    import_type = models.CharField(max_length=50, default="assets")
    source_file = models.FileField(upload_to="imports/%Y/%m/")
    source_filename = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    total_rows = models.IntegerField(default=0)
    processed_rows = models.IntegerField(default=0)
    error_rows = models.IntegerField(default=0)
    error_log = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "import_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Import:{self.name} ({self.status})"

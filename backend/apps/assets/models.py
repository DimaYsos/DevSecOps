import uuid
from django.db import models
from django.conf import settings

class Asset(models.Model):
    TYPE_CHOICES = [
        ("server", "Server"), ("laptop", "Laptop"), ("desktop", "Desktop"),
        ("network", "Network Device"), ("software", "Software License"),
        ("mobile", "Mobile Device"), ("printer", "Printer"), ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"), ("inactive", "Inactive"), ("maintenance", "Maintenance"),
        ("retired", "Retired"), ("lost", "Lost"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="assets")
    name = models.CharField(max_length=200)
    asset_tag = models.CharField(max_length=100, unique=True)
    asset_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default="other")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    description = models.TextField(blank=True, default="")
    serial_number = models.CharField(max_length=200, blank=True, default="")
    manufacturer = models.CharField(max_length=200, blank=True, default="")
    model = models.CharField(max_length=200, blank=True, default="")
    location = models.CharField(max_length=200, blank=True, default="")
    department = models.CharField(max_length=100, blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_assets")
    custom_fields = models.JSONField(default=dict, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    warranty_expires = models.DateField(null=True, blank=True)
    enrichment_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assets"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.asset_tag}: {self.name}"

class AssetLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="links")
    ticket = models.ForeignKey("tickets.Ticket", on_delete=models.CASCADE, null=True, blank=True, related_name="asset_links")
    incident = models.ForeignKey("tickets.Incident", on_delete=models.CASCADE, null=True, blank=True, related_name="asset_links")
    link_type = models.CharField(max_length=50, default="affected")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "asset_links"

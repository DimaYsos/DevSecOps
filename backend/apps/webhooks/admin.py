from django.contrib import admin
from .models import WebhookConfig, WebhookDelivery
admin.site.register(WebhookConfig)
admin.site.register(WebhookDelivery)

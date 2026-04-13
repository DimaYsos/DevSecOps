from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"webhook-configs", views.WebhookConfigViewSet, basename="webhook-config")
router.register(r"webhook-deliveries", views.WebhookDeliveryViewSet, basename="webhook-delivery")

urlpatterns = [
    path("", include(router.urls)),
    path("webhooks/fetch-url/", views.fetch_url, name="fetch-url"),
    path("webhooks/incoming/", views.webhook_incoming, name="webhook-incoming"),
]

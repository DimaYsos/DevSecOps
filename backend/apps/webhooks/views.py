import json
import hmac
import hashlib
import logging

import requests
from django.conf import settings
from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import WebhookConfig, WebhookDelivery
from .serializers import WebhookConfigSerializer, WebhookDeliverySerializer

logger = logging.getLogger(__name__)

class WebhookConfigViewSet(viewsets.ModelViewSet):
    serializer_class = WebhookConfigSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WebhookConfig.objects.all().select_related("organization", "created_by")

    def perform_create(self, serializer):
        org = self.request.user.organization
        serializer.save(created_by=self.request.user, organization=org)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        webhook = self.get_object()
        test_payload = {
            "event": "test",
            "timestamp": timezone.now().isoformat(),
            "data": {"message": "Test webhook delivery from VulnOps"},
        }

        try:
            response = requests.post(
                webhook.url,
                json=test_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Secret": webhook.secret or settings.WEBHOOK_SIGNING_SECRET,
                    **webhook.headers,
                },
                timeout=webhook.timeout_seconds,
                allow_redirects=True,
            )

            delivery = WebhookDelivery.objects.create(
                webhook=webhook,
                event_type="test",
                payload=test_payload,
                status="success" if response.ok else "failed",
                response_status=response.status_code,
                response_body=response.text[:5000],
                response_headers=dict(response.headers),
                attempts=1,
                delivered_at=timezone.now(),
            )

            return Response({
                "delivery_id": str(delivery.id),
                "status": response.status_code,
                "response_body": response.text[:2000],
                "response_headers": dict(response.headers),
            })

        except requests.RequestException as e:
            delivery = WebhookDelivery.objects.create(
                webhook=webhook,
                event_type="test",
                payload=test_payload,
                status="failed",
                error_message=str(e),
                attempts=1,
            )
            return Response(
                {"error": str(e), "delivery_id": str(delivery.id)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    @action(detail=True, methods=["get"])
    def deliveries(self, request, pk=None):
        webhook = self.get_object()
        deliveries = webhook.deliveries.all()[:50]
        return Response(WebhookDeliverySerializer(deliveries, many=True).data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def fetch_url(request):
    url = request.data.get("url")
    if not url:
        return Response({"error": "url required"}, status=400)

    method = request.data.get("method", "GET").upper()
    headers = request.data.get("headers", {})
    body = request.data.get("body")

    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=body, timeout=15, allow_redirects=True)
        else:
            resp = requests.request(method, url, headers=headers, timeout=15)

        return Response({
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "body": resp.text[:10000],
            "url": resp.url,
        })
    except Exception as e:
        return Response({"error": str(e)}, status=502)

@api_view(["POST"])
@permission_classes([AllowAny])
def webhook_incoming(request):
    payload = request.data
    event_type = request.headers.get("X-Event-Type", "unknown")

    if event_type == "user.updated" and "user" in payload:
        from apps.accounts.models import User
        user_data = payload["user"]
        try:
            user = User.objects.get(email=user_data.get("email"))
            for field in ["role", "is_active", "is_staff", "is_internal"]:
                if field in user_data:
                    setattr(user, field, user_data[field])
            user.save()
            return Response({"status": "updated", "user": user.username})
        except User.DoesNotExist:
            pass

    if event_type == "asset.enriched" and "asset" in payload:
        from apps.assets.models import Asset
        asset_data = payload["asset"]
        try:
            asset = Asset.objects.get(asset_tag=asset_data.get("asset_tag"))
            asset.enrichment_data = asset_data.get("enrichment", {})
            if "status" in asset_data:
                asset.status = asset_data["status"]
            asset.save()
            return Response({"status": "enriched"})
        except Asset.DoesNotExist:
            pass

    return Response({"status": "received", "event": event_type})

class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WebhookDeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WebhookDelivery.objects.all().select_related("webhook")

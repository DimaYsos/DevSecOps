import hashlib
import hmac
import json
import logging

import requests
from django.conf import settings
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from vulnops.access import is_org_admin, scope_queryset
from vulnops.security import sanitize_outbound_headers, validate_outbound_url

from .models import WebhookConfig, WebhookDelivery
from .serializers import WebhookConfigSerializer, WebhookDeliverySerializer

logger = logging.getLogger(__name__)
ALLOWED_FETCH_METHODS = {"GET", "POST"}


def _signature_for_payload(secret, payload_bytes):
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


class WebhookConfigViewSet(viewsets.ModelViewSet):
    serializer_class = WebhookConfigSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return scope_queryset(WebhookConfig.objects.select_related("organization", "created_by"), self.request.user)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, organization=self.request.user.organization)

    def perform_update(self, serializer):
        serializer.save(organization=self.get_object().organization, created_by=self.get_object().created_by)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        webhook = self.get_object()
        test_payload = {
            "event": "test",
            "timestamp": timezone.now().isoformat(),
            "data": {"message": "Test webhook delivery from VulnOps"},
        }
        payload_bytes = json.dumps(test_payload).encode("utf-8")
        signature = _signature_for_payload(webhook.secret or settings.WEBHOOK_SIGNING_SECRET, payload_bytes)

        try:
            validate_outbound_url(webhook.url)
            response = requests.post(
                webhook.url,
                data=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    **sanitize_outbound_headers(webhook.headers),
                },
                timeout=min(max(webhook.timeout_seconds, 1), 15),
                allow_redirects=False,
            )

            delivery = WebhookDelivery.objects.create(
                webhook=webhook,
                event_type="test",
                payload=test_payload,
                status="success" if response.ok else "failed",
                response_status=response.status_code,
                attempts=1,
                delivered_at=timezone.now(),
            )
            return Response({"delivery_id": str(delivery.id), "status": response.status_code})
        except (requests.RequestException, ValidationError) as e:
            delivery = WebhookDelivery.objects.create(
                webhook=webhook,
                event_type="test",
                payload=test_payload,
                status="failed",
                error_message=str(e),
                attempts=1,
            )
            return Response({"error": "Webhook delivery failed", "delivery_id": str(delivery.id)}, status=status.HTTP_502_BAD_GATEWAY)

    @action(detail=True, methods=["get"])
    def deliveries(self, request, pk=None):
        webhook = self.get_object()
        deliveries = webhook.deliveries.all()[:50]
        return Response(WebhookDeliverySerializer(deliveries, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def fetch_url(request):
    if not is_org_admin(request.user):
        raise PermissionDenied("Administrative access required.")
    url = request.data.get("url")
    if not url:
        return Response({"error": "url required"}, status=400)

    method = request.data.get("method", "GET").upper()
    if method not in ALLOWED_FETCH_METHODS:
        raise ValidationError("Only GET and POST are allowed.")

    headers = sanitize_outbound_headers(request.data.get("headers", {}))
    body = request.data.get("body")
    validate_outbound_url(url)

    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=10, allow_redirects=False)
        else:
            resp = requests.post(url, headers=headers, json=body, timeout=10, allow_redirects=False)
        return Response({"status": resp.status_code, "body_preview": resp.text[:500]})
    except Exception:
        return Response({"error": "Request failed"}, status=502)


@api_view(["POST"])
@permission_classes([AllowAny])
def webhook_incoming(request):
    signature = request.headers.get("X-Webhook-Signature", "")
    payload_bytes = request.body or b""
    expected = _signature_for_payload(settings.WEBHOOK_SIGNING_SECRET, payload_bytes)
    if not signature or not hmac.compare_digest(signature, expected):
        return Response({"error": "Invalid signature"}, status=403)

    payload = request.data or {}
    event_type = request.headers.get("X-Event-Type") or payload.get("event") or "unknown"

    if event_type == "asset.enriched" and isinstance(payload.get("asset"), dict):
        from apps.assets.models import Asset

        asset_data = payload["asset"]
        asset = Asset.objects.filter(asset_tag=asset_data.get("asset_tag")).first()
        if asset:
            asset.enrichment_data = asset_data.get("enrichment", {})
            if asset_data.get("status") in {choice[0] for choice in Asset.STATUS_CHOICES}:
                asset.status = asset_data["status"]
            asset.save(update_fields=["enrichment_data", "status", "updated_at"])
            return Response({"status": "enriched"})

    return Response({"status": "received", "event": event_type})


class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WebhookDeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return scope_queryset(WebhookDelivery.objects.select_related("webhook"), self.request.user, org_lookup="webhook__organization")

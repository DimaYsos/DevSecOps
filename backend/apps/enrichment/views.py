import logging

import requests
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from vulnops.access import is_org_admin, is_sys_admin
from vulnops.security import validate_outbound_url

from apps.accounts.models import User
from apps.assets.models import Asset

logger = logging.getLogger(__name__)
ENRICHMENT_URL = getattr(settings, "ENRICHMENT_API_URL", "http://localhost:9003")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enrich_user(request):
    user_id = request.data.get("user_id")
    if not user_id:
        return Response({"error": "user_id required"}, status=400)

    user = User.objects.filter(id=user_id).first()
    if not user:
        return Response({"error": "User not found"}, status=404)
    if not is_sys_admin(request.user) and user.organization_id != request.user.organization_id:
        raise PermissionDenied("You cannot enrich users outside your organization.")

    try:
        validate_outbound_url(f"{ENRICHMENT_URL}/api/enrich/user")
        resp = requests.get(
            f"{ENRICHMENT_URL}/api/enrich/user",
            params={"email": user.email, "username": user.username},
            headers={"X-API-Key": settings.ENRICHMENT_API_KEY},
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            for field in ["department", "phone", "bio"]:
                if field in data:
                    setattr(user, field, data[field])
            if "preferences" in data and isinstance(data["preferences"], dict):
                user.preferences.update(data["preferences"])
            user.save(update_fields=["department", "phone", "bio", "preferences"])
            return Response({"status": "enriched", "data": {"department": user.department, "phone": user.phone, "bio": user.bio}})
        return Response({"error": "Enrichment API error"}, status=502)
    except requests.RequestException:
        logger.warning("Enrichment service unavailable")
        return Response({"status": "fallback"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enrich_asset(request):
    asset_id = request.data.get("asset_id")
    if not asset_id:
        return Response({"error": "asset_id required"}, status=400)

    asset = Asset.objects.filter(id=asset_id).first()
    if not asset:
        return Response({"error": "Asset not found"}, status=404)
    if not is_sys_admin(request.user) and asset.organization_id != request.user.organization_id:
        raise PermissionDenied("You cannot enrich assets outside your organization.")

    try:
        validate_outbound_url(f"{ENRICHMENT_URL}/api/enrich/asset")
        resp = requests.get(
            f"{ENRICHMENT_URL}/api/enrich/asset",
            params={"serial": asset.serial_number, "tag": asset.asset_tag},
            headers={"X-API-Key": settings.ENRICHMENT_API_KEY},
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            asset.enrichment_data = data if isinstance(data, dict) else {}
            if isinstance(data, dict) and data.get("custom_fields") and isinstance(data["custom_fields"], dict):
                asset.custom_fields.update(data["custom_fields"])
            if isinstance(data, dict) and data.get("status") in {choice[0] for choice in Asset.STATUS_CHOICES}:
                asset.status = data["status"]
            asset.save(update_fields=["enrichment_data", "custom_fields", "status", "updated_at"])
            return Response({"status": "enriched", "data": asset.enrichment_data})
        return Response({"error": "Enrichment API error"}, status=502)
    except requests.RequestException:
        return Response({"error": "Enrichment service unavailable"}, status=502)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def lookup_address(request):
    query = request.data.get("query", "")
    endpoint = f"{ENRICHMENT_URL}/api/lookup/address"
    validate_outbound_url(endpoint)
    try:
        resp = requests.get(endpoint, params={"q": query}, timeout=10, headers={"X-API-Key": settings.ENRICHMENT_API_KEY})
        if resp.ok:
            return Response(resp.json())
        return Response({"error": "Lookup failed"}, status=502)
    except Exception:
        return Response({"error": "Lookup failed"}, status=502)

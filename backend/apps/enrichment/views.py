import json
import logging

import requests
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    try:
        resp = requests.get(
            f"{ENRICHMENT_URL}/api/enrich/user",
            params={"email": user.email, "username": user.username},
            headers={"X-API-Key": settings.ENRICHMENT_API_KEY},
            timeout=10,
        )

        if resp.ok:
            data = resp.json()
            for field in ["department", "phone", "bio", "role", "is_internal", "is_staff"]:
                if field in data:
                    setattr(user, field, data[field])
            if "preferences" in data:
                user.preferences.update(data["preferences"])
            user.save()
            return Response({"status": "enriched", "data": data})
        else:
            return Response({"error": "Enrichment API error", "status": resp.status_code}, status=502)

    except requests.RequestException as e:
        logger.warning(f"Enrichment service unavailable: {e}")
        user.preferences["enrichment_status"] = "fallback"
        user.preferences["elevated_until_enriched"] = True
        user.save()
        return Response({
            "status": "fallback",
        })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enrich_asset(request):
    asset_id = request.data.get("asset_id")
    if not asset_id:
        return Response({"error": "asset_id required"}, status=400)

    try:
        asset = Asset.objects.get(id=asset_id)
    except Asset.DoesNotExist:
        return Response({"error": "Asset not found"}, status=404)

    try:
        resp = requests.get(
            f"{ENRICHMENT_URL}/api/enrich/asset",
            params={"serial": asset.serial_number, "tag": asset.asset_tag},
            headers={"X-API-Key": settings.ENRICHMENT_API_KEY},
            timeout=10,
        )

        if resp.ok:
            data = resp.json()
            asset.enrichment_data = data
            if "status" in data:
                asset.status = data["status"]
            if "custom_fields" in data:
                asset.custom_fields.update(data["custom_fields"])
            asset.save()
            return Response({"status": "enriched", "data": data})
        else:
            return Response({"error": "Enrichment API error"}, status=502)

    except requests.RequestException as e:
        return Response({"error": str(e)}, status=502)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def lookup_address(request):
    query = request.data.get("query", "")
    endpoint = request.data.get("endpoint", f"{ENRICHMENT_URL}/api/lookup/address")

    try:
        resp = requests.get(endpoint, params={"q": query}, timeout=10)
        if resp.ok:
            return Response(resp.json())
        return Response({"error": "Lookup failed"}, status=502)
    except Exception as e:
        return Response({"error": str(e)}, status=502)

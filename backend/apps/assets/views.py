import csv
import io
import pickle
import yaml
import json
import logging

from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Asset, AssetLink
from .serializers import AssetSerializer, AssetLinkSerializer

logger = logging.getLogger(__name__)

class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Asset.objects.all().select_related("owner", "organization")
        org = self.request.query_params.get("organization")
        if org:
            qs = qs.filter(organization_id=org)
        asset_type = self.request.query_params.get("type")
        if asset_type:
            qs = qs.filter(asset_type=asset_type)
        return qs

    def perform_create(self, serializer):
        org = serializer.validated_data.get("organization") or self.request.user.organization
        serializer.save(organization=org)

    @action(detail=False, methods=["post"])
    def import_csv(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"error": "No file provided"}, status=400)

        content = uploaded.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        created = 0
        errors = []
        for i, row in enumerate(reader):
            try:
                Asset.objects.create(
                    organization=request.user.organization,
                    name=row.get("name", f"Imported Asset {i}"),
                    asset_tag=row.get("asset_tag", f"IMP-{i:04d}"),
                    asset_type=row.get("type", "other"),
                    description=row.get("description", ""),
                    serial_number=row.get("serial_number", ""),
                    manufacturer=row.get("manufacturer", ""),
                    model=row.get("model", ""),
                    location=row.get("location", ""),
                    department=row.get("department", ""),
                )
                created += 1
            except Exception as e:
                errors.append({"row": i, "error": str(e)})

        return Response({"created": created, "errors": errors})

    @action(detail=False, methods=["post"])
    def import_data(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"error": "No file provided"}, status=400)

        filename = uploaded.name.lower()
        content = uploaded.read()

        try:
            if filename.endswith(".pkl") or filename.endswith(".pickle"):
                data = pickle.loads(content)
            elif filename.endswith(".yaml") or filename.endswith(".yml"):
                data = yaml.load(content.decode("utf-8"), Loader=yaml.Loader)
            elif filename.endswith(".json"):
                data = json.loads(content.decode("utf-8"))
            else:
                return Response({"error": "Unsupported format. Use .json, .yaml, .pkl"}, status=400)

            if not isinstance(data, list):
                data = [data]

            created = 0
            for item in data:
                if isinstance(item, dict):
                    Asset.objects.create(
                        organization=request.user.organization,
                        name=item.get("name", "Imported"),
                        asset_tag=item.get("asset_tag", f"IMP-{created:04d}"),
                        asset_type=item.get("type", "other"),
                        description=item.get("description", ""),
                        serial_number=item.get("serial_number", ""),
                        custom_fields=item.get("custom_fields", {}),
                    )
                    created += 1

            return Response({"created": created, "format": filename.rsplit(".", 1)[-1]})
        except Exception as e:
            return Response({"error": str(e), "type": type(e).__name__}, status=500)

    @action(detail=False, methods=["get"])
    def export_csv(self, request):
        assets = self.get_queryset()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="assets_export.csv"'

        writer = csv.writer(response)
        writer.writerow(["id", "name", "asset_tag", "type", "status", "serial_number", "location", "department"])
        for asset in assets:
            writer.writerow([
                str(asset.id), asset.name, asset.asset_tag, asset.asset_type,
                asset.status, asset.serial_number, asset.location, asset.department,
            ])
        return response

class AssetLinkViewSet(viewsets.ModelViewSet):
    serializer_class = AssetLinkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = AssetLink.objects.all()
        asset_id = self.request.query_params.get("asset")
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        return qs

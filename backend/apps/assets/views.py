import csv
import io
import json
import logging

import yaml
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from vulnops.access import is_sys_admin, scope_queryset

from .models import Asset, AssetLink
from .serializers import AssetSerializer, AssetLinkSerializer

logger = logging.getLogger(__name__)


class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = scope_queryset(Asset.objects.select_related("owner", "organization"), self.request.user)
        org = self.request.query_params.get("organization")
        if org and (is_sys_admin(self.request.user) or org == str(self.request.user.organization_id)):
            qs = qs.filter(organization_id=org)
        asset_type = self.request.query_params.get("type")
        if asset_type:
            qs = qs.filter(asset_type=asset_type)
        return qs

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization, owner=self.request.user)

    def perform_update(self, serializer):
        serializer.save(organization=self.get_object().organization, owner=self.get_object().owner)

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
                    owner=request.user,
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
            if filename.endswith((".yaml", ".yml")):
                data = yaml.safe_load(content.decode("utf-8"))
            elif filename.endswith(".json"):
                data = json.loads(content.decode("utf-8"))
            else:
                return Response({"error": "Unsupported format. Use .json or .yaml"}, status=400)

            if data is None:
                data = []
            if not isinstance(data, list):
                data = [data]

            created = 0
            errors = []
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    errors.append({"row": i, "error": "Item must be an object"})
                    continue
                try:
                    Asset.objects.create(
                        organization=request.user.organization,
                        owner=request.user,
                        name=item.get("name", "Imported"),
                        asset_tag=item.get("asset_tag", f"IMP-{created:04d}"),
                        asset_type=item.get("type", "other"),
                        description=item.get("description", ""),
                        serial_number=item.get("serial_number", ""),
                        custom_fields=item.get("custom_fields", {}),
                    )
                    created += 1
                except Exception as e:
                    errors.append({"row": i, "error": str(e)})

            return Response({"created": created, "errors": errors, "format": filename.rsplit(".", 1)[-1]})
        except (json.JSONDecodeError, yaml.YAMLError, UnicodeDecodeError) as e:
            return Response({"error": f"Invalid file content: {str(e)}"}, status=400)
        except Exception:
            logger.exception("Import failed")
            return Response({"error": "Import failed"}, status=500)

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
        qs = scope_queryset(AssetLink.objects.select_related("asset", "ticket", "incident"), self.request.user, org_lookup="asset__organization")
        asset_id = self.request.query_params.get("asset")
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        return qs

    def perform_create(self, serializer):
        asset = serializer.validated_data.get("asset")
        if asset.organization_id != self.request.user.organization_id and not is_sys_admin(self.request.user):
            raise PermissionDenied("You cannot link assets outside your organization.")
        ticket = serializer.validated_data.get("ticket")
        incident = serializer.validated_data.get("incident")
        if ticket and ticket.organization_id != asset.organization_id:
            raise ValidationError("Linked ticket must belong to the same organization.")
        if incident and incident.organization_id != asset.organization_id:
            raise ValidationError("Linked incident must belong to the same organization.")
        serializer.save()

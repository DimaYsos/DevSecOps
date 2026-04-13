import csv
import logging
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.files.base import File
from django.db import models
from django.http import FileResponse
from django.utils import timezone

from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from vulnops.access import is_org_admin, scope_queryset
from vulnops.security import sanitize_filename

from apps.tickets.models import Ticket
from .models import ReportJob, ImportJob
from .serializers import ReportJobSerializer, ImportJobSerializer

logger = logging.getLogger(__name__)
ALLOWED_REPORT_TYPES = {"tickets"}
ALLOWED_FORMATS = {"csv", "json", "txt"}


class ReportJobViewSet(viewsets.ModelViewSet):
    serializer_class = ReportJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return scope_queryset(ReportJob.objects.select_related("created_by", "organization"), self.request.user)

    def perform_create(self, serializer):
        job = serializer.save(created_by=self.request.user, organization=self.request.user.organization, status="pending")
        self._generate_report(job)

    def _generate_report(self, job):
        try:
            job.status = "running"
            job.started_at = timezone.now()
            job.save(update_fields=["status", "started_at", "updated_at"])

            tickets = Ticket.objects.filter(organization=job.organization)
            params = job.parameters or {}
            if params.get("status"):
                tickets = tickets.filter(status=params["status"])
            if params.get("priority"):
                tickets = tickets.filter(priority=params["priority"])

            reports_dir = Path(settings.MEDIA_ROOT) / "reports" / datetime.now().strftime("%Y/%m")
            reports_dir.mkdir(parents=True, exist_ok=True)

            safe_name = sanitize_filename(params.get("filename", f"report_{job.id}"), default=f"report_{job.id}")
            output_path = reports_dir / f"{safe_name}.csv"

            with output_path.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "title", "status", "priority", "reporter", "created_at"])
                count = 0
                for t in tickets:
                    writer.writerow([str(t.id), t.title, t.status, t.priority, t.reporter.username if t.reporter else "", str(t.created_at)])
                    count += 1

            with output_path.open("rb") as f:
                job.output_file.save(output_path.name, File(f), save=False)
            job.output_filename = output_path.name
            job.row_count = count
            job.status = "completed"
            job.completed_at = timezone.now()
            job.save(update_fields=["output_file", "output_filename", "row_count", "status", "completed_at", "updated_at"])
        except Exception as e:
            logger.exception("Report generation failed")
            job.status = "failed"
            job.error_message = str(e)
            job.save(update_fields=["status", "error_message", "updated_at"])

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        job = self.get_object()
        if job.output_file:
            return FileResponse(job.output_file.open("rb"), as_attachment=True, filename=job.output_filename)
        return Response({"error": "No output file"}, status=404)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_report_preview(request):
    report_type = request.data.get("type", "tickets")
    output_format = request.data.get("format", "csv")
    custom_header = sanitize_filename(request.data.get("header", "VulnOps Report"), default="VulnOps_Report")

    if report_type not in ALLOWED_REPORT_TYPES:
        raise ValidationError("Unsupported report type.")
    if output_format not in ALLOWED_FORMATS:
        raise ValidationError("Unsupported output format.")

    content = "\n".join([
        custom_header,
        timezone.now().isoformat(),
        f"Report: {report_type}",
        f"Format: {output_format}",
    ]) + "\n"
    return Response({"preview": content})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def maintenance_cleanup(request):
    if not is_org_admin(request.user):
        raise PermissionDenied("Administrative access required.")

    days_old = int(request.data.get("days", 30))
    if days_old < 1 or days_old > 365:
        raise ValidationError("days must be between 1 and 365")

    reports_dir = Path(settings.MEDIA_ROOT) / "reports"
    cutoff = timezone.now().timestamp() - (days_old * 86400)
    deleted = []

    if reports_dir.exists():
        for path in reports_dir.rglob("*.csv"):
            if path.is_file() and path.stat().st_mtime < cutoff:
                deleted.append(path.name)
                path.unlink(missing_ok=True)

    return Response({"message": "Cleanup completed", "deleted_files": deleted})


class ImportJobViewSet(viewsets.ModelViewSet):
    serializer_class = ImportJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return scope_queryset(ImportJob.objects.select_related("created_by", "organization"), self.request.user)

    def perform_create(self, serializer):
        uploaded = self.request.FILES.get("file")
        if not uploaded:
            raise ValidationError("file is required")
        serializer.save(
            created_by=self.request.user,
            organization=self.request.user.organization,
            source_filename=sanitize_filename(uploaded.name, default="import.csv"),
            status="pending",
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_report_files(request):
    files = []
    jobs = scope_queryset(ReportJob.objects.exclude(output_filename=""), request.user).order_by("-created_at")[:100]
    for job in jobs:
        files.append({
            "name": job.output_filename,
            "size": job.output_file.size if job.output_file else 0,
            "report_job_id": str(job.id),
        })
    return Response({"files": files})

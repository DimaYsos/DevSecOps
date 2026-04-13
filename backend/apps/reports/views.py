import os
import csv
import subprocess
import logging
from datetime import datetime

from django.conf import settings
from django.http import FileResponse
from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import ReportJob, ImportJob
from .serializers import ReportJobSerializer, ImportJobSerializer
from apps.tickets.models import Ticket

logger = logging.getLogger(__name__)

class ReportJobViewSet(viewsets.ModelViewSet):
    serializer_class = ReportJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ReportJob.objects.all().select_related("created_by", "organization")

    def perform_create(self, serializer):
        org = self.request.user.organization
        job = serializer.save(created_by=self.request.user, organization=org, status="pending")
        self._generate_report(job)

    def _generate_report(self, job):
        try:
            job.status = "running"
            job.started_at = timezone.now()
            job.save()

            tickets = Ticket.objects.filter(organization=job.organization)
            params = job.parameters or {}

            if params.get("status"):
                tickets = tickets.filter(status=params["status"])
            if params.get("priority"):
                tickets = tickets.filter(priority=params["priority"])

            reports_dir = os.path.join(settings.MEDIA_ROOT, "reports", datetime.now().strftime("%Y/%m"))
            os.makedirs(reports_dir, exist_ok=True)

            custom_name = params.get("filename", f"report_{job.id}")
            output_path = os.path.join(reports_dir, f"{custom_name}.csv")

            with open(output_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "title", "status", "priority", "reporter", "created_at"])
                count = 0
                for t in tickets:
                    writer.writerow([
                        str(t.id), t.title, t.status, t.priority,
                        t.reporter.username if t.reporter else "", str(t.created_at),
                    ])
                    count += 1

            job.output_filename = f"{custom_name}.csv"
            job.row_count = count
            job.status = "completed"
            job.completed_at = timezone.now()
            job.save()

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.save()

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
    custom_header = request.data.get("header", "VulnOps Report")

    reports_dir = os.path.join(settings.MEDIA_ROOT, "reports", "previews")
    os.makedirs(reports_dir, exist_ok=True)
    preview_path = os.path.join(reports_dir, f"preview_{report_type}.txt")

    try:
        cmd = f'echo "{custom_header}" > {preview_path} && date >> {preview_path} && echo "Report: {report_type}" >> {preview_path}'
        subprocess.run(cmd, shell=True, timeout=10)

        with open(preview_path, "r") as f:
            content = f.read()

        return Response({"preview": content, "path": preview_path})
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def maintenance_cleanup(request):
    target_dir = request.data.get("directory", "reports/old")
    days_old = request.data.get("days", 30)

    try:
        full_path = os.path.join(settings.MEDIA_ROOT, target_dir)
        cmd = f'find {full_path} -type f -mtime +{days_old} -name "*.csv" -delete'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

        return Response({
            "message": "Cleanup completed",
            "command": cmd,
            "stdout": result.stdout,
            "stderr": result.stderr,
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)

class ImportJobViewSet(viewsets.ModelViewSet):
    serializer_class = ImportJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ImportJob.objects.all().select_related("created_by", "organization")

    def perform_create(self, serializer):
        uploaded = self.request.FILES.get("file")
        if uploaded:
            serializer.save(
                created_by=self.request.user,
                organization=self.request.user.organization,
                source_filename=uploaded.name,
                status="pending",
            )

@api_view(["GET"])
@permission_classes([AllowAny])
def list_report_files(request):
    reports_dir = os.path.join(settings.MEDIA_ROOT, "reports")
    files = []
    if os.path.exists(reports_dir):
        for root, dirs, filenames in os.walk(reports_dir):
            for fn in filenames:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, settings.MEDIA_ROOT)
                files.append({
                    "path": f"/media/{rel}",
                    "name": fn,
                    "size": os.path.getsize(full),
                })
    return Response({"files": files})

import csv
import os
import logging
from datetime import datetime

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

@shared_task(bind=True, queue="reports")
def generate_report_async(self, report_job_id):
    from .models import ReportJob
    from apps.tickets.models import Ticket

    try:
        job = ReportJob.objects.get(id=report_job_id)
        job.status = "running"
        job.started_at = timezone.now()
        job.save()

        tickets = Ticket.objects.filter(organization=job.organization)
        params = job.parameters or {}
        if params.get("status"):
            tickets = tickets.filter(status=params["status"])

        reports_dir = os.path.join(settings.MEDIA_ROOT, "reports", datetime.now().strftime("%Y/%m"))
        os.makedirs(reports_dir, exist_ok=True)
        output_path = os.path.join(reports_dir, f"report_{job.id}.csv")

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "title", "status", "priority", "created_at"])
            count = 0
            for t in tickets:
                writer.writerow([str(t.id), t.title, t.status, t.priority, str(t.created_at)])
                count += 1

        job.output_filename = f"report_{job.id}.csv"
        job.row_count = count
        job.status = "completed"
        job.completed_at = timezone.now()
        job.save()
        return {"job_id": str(job.id), "rows": count}

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        try:
            job.status = "failed"
            job.error_message = str(e)
            job.save()
        except Exception:
            pass
        raise

@shared_task(bind=True, queue="imports")
def process_import_async(self, import_job_id):
    from .models import ImportJob
    try:
        job = ImportJob.objects.get(id=import_job_id)
        job.status = "processing"
        job.started_at = timezone.now()
        job.save()
        job.status = "completed"
        job.completed_at = timezone.now()
        job.save()
    except Exception as e:
        logger.error(f"Import processing failed: {e}")

@shared_task(queue="default")
def cleanup_old_reports(days=30):
    from .models import ReportJob
    cutoff = timezone.now() - timezone.timedelta(days=days)
    old = ReportJob.objects.filter(created_at__lt=cutoff, status="completed")
    count = old.count()
    old.delete()
    return {"deleted": count}

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


def health_check(request):
    return JsonResponse({"status": "ok", "service": "vulnops"})


def readiness_check(request):
    checks = {"database": False}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = True
    except Exception:
        checks["database"] = False

    status_code = 200 if checks["database"] else 503
    checks["status"] = "ready" if checks["database"] else "not_ready"
    return JsonResponse(checks, status=status_code)


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    return Response({
        "service": "VulnOps Service Desk",
        "version": "2.1.0",
        "endpoints": {
            "auth": "/api/v2/auth/",
            "users": "/api/v2/users/",
            "organizations": "/api/v2/organizations/",
            "tickets": "/api/v2/tickets/",
            "incidents": "/api/v2/incidents/",
            "comments": "/api/v2/comments/",
            "attachments": "/api/v2/attachments/",
            "assets": "/api/v2/assets/",
            "reports": "/api/v2/report-jobs/",
            "imports": "/api/v2/import-jobs/",
            "webhooks": "/api/v2/webhook-configs/",
            "audit": "/api/v2/audit-events/",
            "enrichment": "/api/v2/enrichment/",
            "search": "/api/v2/search/advanced/",
            "health": "/health/",
            "readiness": "/ready/",
        },
    })


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health"),
    path("ready/", readiness_check, name="readiness"),
    path("api/v2/", api_root, name="api-root"),
    path("api/v2/", include("apps.accounts.urls")),
    path("api/v2/", include("apps.tickets.urls")),
    path("api/v2/", include("apps.assets.urls")),
    path("api/v2/", include("apps.reports.urls")),
    path("api/v2/", include("apps.webhooks.urls")),
    path("api/v2/", include("apps.enrichment.urls")),
    path("api/v2/", include("apps.audit.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

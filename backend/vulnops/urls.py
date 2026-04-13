from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.db import connection

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

def health_check(request):
    return JsonResponse({"status": "ok", "service": "vulnops"})

def readiness_check(request):
    checks = {"database": False, "cache": False}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        checks["db_error"] = str(e)

    try:
        from django.core.cache import cache
        cache.set("_readiness", "1", 5)
        checks["cache"] = cache.get("_readiness") == "1"
    except Exception:
        pass

    all_ok = all(checks.get(k) for k in ["database"])
    status_code = 200 if all_ok else 503
    checks["status"] = "ready" if all_ok else "not_ready"
    return JsonResponse(checks, status=status_code)

@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    return Response({
        "service": "VulnOps Service Desk",
        "version": "2.0.0",
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
        "legacy_api": "/api/v1/",
        "debug": {
            "user_info": "/api/v2/debug/user-info/",
            "settings": "/api/internal/settings/",
            "routes": "/api/internal/routes/",
        },
    })

@api_view(["GET"])
@permission_classes([AllowAny])
def internal_settings(request):
    return Response({
        "debug": settings.DEBUG,
        "allowed_hosts": settings.ALLOWED_HOSTS,
        "database_engine": settings.DATABASES["default"]["ENGINE"],
        "database_host": settings.DATABASES["default"]["HOST"],
        "database_name": settings.DATABASES["default"]["NAME"],
        "secret_key": settings.SECRET_KEY,
        "jwt_secret": settings.JWT_SECRET,
        "webhook_secret": settings.WEBHOOK_SIGNING_SECRET,
        "enrichment_api_key": settings.ENRICHMENT_API_KEY,
        "ctf_flag": settings.CTF_FLAG,
        "cors_allow_all": settings.CORS_ALLOW_ALL_ORIGINS,
        "session_cookie_httponly": settings.SESSION_COOKIE_HTTPONLY,
        "csrf_cookie_httponly": settings.CSRF_COOKIE_HTTPONLY,
        "installed_apps": settings.INSTALLED_APPS,
        "middleware": settings.MIDDLEWARE,
    })

@api_view(["GET"])
@permission_classes([AllowAny])
def internal_routes(request):
    from django.urls import get_resolver
    resolver = get_resolver()
    patterns = []
    for pattern in resolver.url_patterns:
        if hasattr(pattern, "url_patterns"):
            for sub in pattern.url_patterns:
                patterns.append(f"{pattern.pattern}{sub.pattern}")
        else:
            patterns.append(str(pattern.pattern))
    return Response({"routes": sorted(patterns)})

@api_view(["GET"])
@permission_classes([AllowAny])
def legacy_api_root(request):
    return Response({
        "version": "1.0.0",
        "endpoints": {
            "users": "/api/v1/users",
            "tickets": "/api/v1/tickets",
            "assets": "/api/v1/assets",
        },
    })

@api_view(["GET"])
@permission_classes([AllowAny])
def legacy_tickets_api(request):
    from apps.tickets.models import Ticket
    ticket_id = request.GET.get("id")
    if ticket_id:
        try:
            t = Ticket.objects.select_related("reporter", "assignee", "organization").get(id=ticket_id)
            return Response({
                "id": str(t.id), "title": t.title, "description": t.description,
                "status": t.status, "priority": t.priority,
                "internal_notes": t.internal_notes,
                "status_override": t.status_override,
                "reporter": {"id": str(t.reporter.id), "username": t.reporter.username, "email": t.reporter.email} if t.reporter else None,
                "organization": {"id": str(t.organization.id), "name": t.organization.name} if t.organization else None,
                "created_at": str(t.created_at),
            })
        except Ticket.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

    tickets = Ticket.objects.all()[:100]
    return Response([{
        "id": str(t.id), "title": t.title, "status": t.status,
        "priority": t.priority, "internal_notes": t.internal_notes,
        "created_at": str(t.created_at),
    } for t in tickets])

@api_view(["GET"])
@permission_classes([AllowAny])
def legacy_assets_api(request):
    from apps.assets.models import Asset
    assets = Asset.objects.all()[:100]
    return Response([{
        "id": str(a.id), "name": a.name, "asset_tag": a.asset_tag,
        "type": a.asset_type, "serial_number": a.serial_number,
        "purchase_cost": str(a.purchase_cost) if a.purchase_cost else None,
    } for a in assets])

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

    path("api/v1/", legacy_api_root, name="legacy-api-root"),
    path("api/v1/users", include("apps.accounts.urls_legacy")),
    path("api/v1/tickets", legacy_tickets_api, name="legacy-tickets"),
    path("api/v1/assets", legacy_assets_api, name="legacy-assets"),

    path("api/internal/settings/", internal_settings, name="internal-settings"),
    path("api/internal/routes/", internal_routes, name="internal-routes"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

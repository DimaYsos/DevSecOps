from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"report-jobs", views.ReportJobViewSet, basename="report-job")
router.register(r"import-jobs", views.ImportJobViewSet, basename="import-job")

urlpatterns = [
    path("", include(router.urls)),
    path("reports/preview/", views.generate_report_preview, name="report-preview"),
    path("reports/files/", views.list_report_files, name="report-files"),
    path("maintenance/cleanup/", views.maintenance_cleanup, name="maintenance-cleanup"),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"audit-events", views.AuditEventViewSet, basename="audit-event")

urlpatterns = [
    path("", include(router.urls)),
]

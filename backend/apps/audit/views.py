from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from vulnops.access import is_sys_admin, scope_queryset

from .models import AuditEvent
from .serializers import AuditEventSerializer


class AuditEventViewSet(viewsets.ModelViewSet):
    serializer_class = AuditEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = scope_queryset(AuditEvent.objects.select_related("user", "organization"), self.request.user)
        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)
        resource_type = self.request.query_params.get("resource_type")
        if resource_type:
            qs = qs.filter(resource_type=resource_type)
        user_id = self.request.query_params.get("user_id")
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
            organization=self.request.user.organization,
            ip_address=self.request.META.get("REMOTE_ADDR"),
            user_agent=self.request.META.get("HTTP_USER_AGENT", ""),
        )


def log_event(user=None, action="other", resource_type="", resource_id="", description="", request=None, metadata=None):
    AuditEvent.objects.create(
        user=user,
        organization=user.organization if user and hasattr(user, "organization") else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        description=description,
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
        metadata=metadata or {},
    )

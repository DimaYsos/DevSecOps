import os
import uuid
import logging
from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from django.db import models
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from vulnops.access import is_org_admin, is_sys_admin, scope_queryset
from vulnops.security import sanitize_filename

from .models import Ticket, Incident, Comment, Attachment
from .serializers import TicketSerializer, TicketCreateSerializer, IncidentSerializer, CommentSerializer, AttachmentSerializer

logger = logging.getLogger(__name__)

VALID_TRANSITIONS = {
    "draft": ["open"],
    "open": ["in_progress", "closed"],
    "in_progress": ["waiting_customer", "waiting_vendor", "escalated", "resolved"],
    "waiting_customer": ["in_progress", "resolved", "closed"],
    "waiting_vendor": ["in_progress"],
    "escalated": ["in_progress", "resolved"],
    "resolved": ["closed", "reopened"],
    "closed": ["reopened"],
    "reopened": ["in_progress", "closed"],
}
ALLOWED_SORT_FIELDS = {"created_at", "title", "status", "priority"}
ALLOWED_ORDER = {"asc", "desc"}


def _org_scoped_ticket_queryset(user):
    return scope_queryset(Ticket.objects.select_related("reporter", "assignee", "organization"), user)


def _org_scoped_incident_queryset(user):
    return scope_queryset(Incident.objects.select_related("reporter", "commander", "organization"), user)


def _org_scoped_comment_queryset(user):
    return scope_queryset(Comment.objects.select_related("author", "ticket", "incident"), user, org_lookup="ticket__organization") | scope_queryset(Comment.objects.select_related("author", "ticket", "incident"), user, org_lookup="incident__organization")


def _can_access_attachment(user, attachment):
    if attachment.is_public:
        return True
    if not getattr(user, "is_authenticated", False):
        return False
    if is_sys_admin(user):
        return True
    return attachment.organization_id == user.organization_id


class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = _org_scoped_ticket_queryset(self.request.user)
        stat = self.request.query_params.get("status")
        if stat:
            qs = qs.filter(status=stat)
        priority = self.request.query_params.get("priority")
        if priority:
            qs = qs.filter(priority=priority)
        assignee = self.request.query_params.get("assignee")
        if assignee:
            qs = qs.filter(assignee_id=assignee)
        return qs

    def get_serializer_class(self):
        return TicketCreateSerializer if self.action == "create" else TicketSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user, organization=self.request.user.organization)

    def perform_update(self, serializer):
        serializer.save(organization=self.get_object().organization, reporter=self.get_object().reporter)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        ticket = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            return Response({"error": "status field required"}, status=status.HTTP_400_BAD_REQUEST)
        allowed = VALID_TRANSITIONS.get(ticket.status, [])
        if new_status not in allowed:
            return Response({"error": f"Cannot transition from {ticket.status} to {new_status}. Allowed: {allowed}"}, status=status.HTTP_400_BAD_REQUEST)
        ticket.status = new_status
        ticket.save(update_fields=["status", "updated_at"])
        return Response(TicketSerializer(ticket, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        if not is_org_admin(request.user):
            raise PermissionDenied("Only organization administrators can escalate tickets.")
        ticket = self.get_object()
        ticket.status = "escalated"
        ticket.priority = "critical"
        ticket.save(update_fields=["status", "priority", "updated_at"])
        return Response(TicketSerializer(ticket, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def self_approve(self, request, pk=None):
        ticket = self.get_object()
        if ticket.reporter_id != request.user.id and not is_org_admin(request.user):
            raise PermissionDenied("Only the reporter or an admin can resolve this ticket.")
        ticket.status = "resolved"
        ticket.save(update_fields=["status", "updated_at"])
        return Response(TicketSerializer(ticket, context={"request": request}).data)


class IncidentViewSet(viewsets.ModelViewSet):
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _org_scoped_incident_queryset(self.request.user)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user, organization=self.request.user.organization)

    def perform_update(self, serializer):
        serializer.save(organization=self.get_object().organization, reporter=self.get_object().reporter)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Comment.objects.select_related("author", "ticket", "incident")
        if not is_sys_admin(self.request.user):
            qs = qs.filter(
                (models.Q(ticket__organization_id=self.request.user.organization_id)) |
                (models.Q(incident__organization_id=self.request.user.organization_id))
            )
        ticket_id = self.request.query_params.get("ticket")
        if ticket_id:
            qs = qs.filter(ticket_id=ticket_id)
        incident_id = self.request.query_params.get("incident")
        if incident_id:
            qs = qs.filter(incident_id=incident_id)
        return qs.distinct()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_create(self, serializer):
        ticket = serializer.validated_data.get("ticket")
        incident = serializer.validated_data.get("incident")
        org_id = ticket.organization_id if ticket else incident.organization_id if incident else None
        if not org_id or (org_id != self.request.user.organization_id and not is_sys_admin(self.request.user)):
            raise PermissionDenied("You cannot comment on resources outside your organization.")
        serializer.save(author=self.request.user)


class AttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = scope_queryset(Attachment.objects.select_related("ticket", "incident", "comment"), self.request.user)
        ticket_id = self.request.query_params.get("ticket")
        if ticket_id:
            qs = qs.filter(ticket_id=ticket_id)
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_create(self, serializer):
        uploaded_file = self.request.FILES.get("file")
        if not uploaded_file:
            raise ValidationError("file is required")
        if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
            raise ValidationError("File is too large")
        ticket = serializer.validated_data.get("ticket")
        incident = serializer.validated_data.get("incident")
        comment = serializer.validated_data.get("comment")
        org_id = None
        if ticket:
            org_id = ticket.organization_id
        elif incident:
            org_id = incident.organization_id
        elif comment:
            org_id = comment.ticket.organization_id if comment.ticket else comment.incident.organization_id if comment.incident else None
        if not org_id or (org_id != self.request.user.organization_id and not is_sys_admin(self.request.user)):
            raise PermissionDenied("You cannot upload attachments outside your organization.")
        safe_name = sanitize_filename(uploaded_file.name, default="attachment")
        filename = f"{uuid.uuid4().hex}_{safe_name}"
        serializer.save(
            uploaded_by=self.request.user,
            organization=self.request.user.organization,
            filename=filename,
            original_filename=safe_name,
            content_type=uploaded_file.content_type or "application/octet-stream",
            file_size=uploaded_file.size,
        )


@api_view(["GET"])
def download_attachment(request, attachment_id):
    attachment = Attachment.objects.filter(id=attachment_id).first()
    if not attachment:
        return Response({"error": "Attachment not found"}, status=404)
    if not _can_access_attachment(request.user, attachment):
        return Response({"error": "Not found"}, status=404)
    if attachment.file:
        return FileResponse(attachment.file.open("rb"), as_attachment=True, filename=attachment.original_filename)
    return Response({"error": "File not found"}, status=404)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def advanced_search(request):
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    sort = request.GET.get("sort", "created_at").strip()
    order = request.GET.get("order", "desc").strip().lower()

    if sort not in ALLOWED_SORT_FIELDS:
        sort = "created_at"
    if order not in ALLOWED_ORDER:
        order = "desc"

    qs = _org_scoped_ticket_queryset(request.user)
    if query:
        qs = qs.filter(models.Q(title__icontains=query) | models.Q(description__icontains=query))
    if status_filter:
        qs = qs.filter(status=status_filter)

    ordering = f"-{sort}" if order == "desc" else sort
    qs = qs.order_by(ordering)[:100]
    results = [{
        "id": str(t.id),
        "title": t.title,
        "status": t.status,
        "priority": t.priority,
        "created_at": t.created_at,
        "reporter_name": t.reporter.username if t.reporter else "",
        "org_name": t.organization.name if t.organization else "",
    } for t in qs]
    return Response({"results": results, "count": len(results)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def internal_tickets(request):
    tickets = _org_scoped_ticket_queryset(request.user).filter(is_internal=True)
    if not is_org_admin(request.user):
        tickets = tickets.filter(reporter=request.user)
    return Response(TicketSerializer(tickets, many=True, context={"request": request}).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def public_ticket_export(request):
    export_dir = Path(settings.MEDIA_ROOT) / "exports"
    files = []
    if export_dir.exists():
        for path in export_dir.iterdir():
            if path.is_file() and path.suffix.lower() in {".csv", ".json"}:
                files.append({"name": path.name, "size": path.stat().st_size})
    return Response({"files": files})

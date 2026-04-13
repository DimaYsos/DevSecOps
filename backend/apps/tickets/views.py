import os
import uuid
import logging
from django.conf import settings
from django.db import connection
from django.http import FileResponse, Http404, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Ticket, Incident, Comment, Attachment
from .serializers import (
    TicketSerializer, TicketCreateSerializer,
    IncidentSerializer, CommentSerializer, AttachmentSerializer,
)

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

class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Ticket.objects.all().select_related("reporter", "assignee", "organization")

        org = self.request.query_params.get("organization")
        if org:
            qs = qs.filter(organization_id=org)
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
        if self.action == "create":
            return TicketCreateSerializer
        return TicketSerializer

    def perform_create(self, serializer):
        org = serializer.validated_data.get("organization") or self.request.user.organization
        serializer.save(reporter=self.request.user, organization=org)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        ticket = self.get_object()
        new_status = request.data.get("status")

        if not new_status:
            return Response(
                {"error": "status field required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed = VALID_TRANSITIONS.get(ticket.status, [])
        if new_status not in allowed:
            return Response(
                {"error": f"Cannot transition from {ticket.status} to {new_status}. Allowed: {allowed}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ticket.status = new_status
        ticket.save(update_fields=["status", "updated_at"])
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = "escalated"
        ticket.priority = "critical"
        ticket.save(update_fields=["status", "priority", "updated_at"])
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=["post"])
    def self_approve(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = "resolved"
        ticket.save(update_fields=["status", "updated_at"])
        return Response(TicketSerializer(ticket).data)

class IncidentViewSet(viewsets.ModelViewSet):
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Incident.objects.all().select_related("reporter", "commander", "organization")

    def perform_create(self, serializer):
        org = serializer.validated_data.get("organization") or self.request.user.organization
        serializer.save(reporter=self.request.user, organization=org)

class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Comment.objects.all().select_related("author")
        ticket_id = self.request.query_params.get("ticket")
        if ticket_id:
            qs = qs.filter(ticket_id=ticket_id)
        incident_id = self.request.query_params.get("incident")
        if incident_id:
            qs = qs.filter(incident_id=incident_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

@method_decorator(csrf_exempt, name="dispatch")
class AttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Attachment.objects.all()
        ticket_id = self.request.query_params.get("ticket")
        if ticket_id:
            qs = qs.filter(ticket_id=ticket_id)
        return qs

    def perform_create(self, serializer):
        uploaded_file = self.request.FILES.get("file")
        if not uploaded_file:
            return

        filename = f"{uuid.uuid4().hex}_{uploaded_file.name}"
        serializer.save(
            uploaded_by=self.request.user,
            organization=self.request.user.organization,
            filename=filename,
            original_filename=uploaded_file.name,
            content_type=uploaded_file.content_type,
            file_size=uploaded_file.size,
        )

@api_view(["GET"])
@permission_classes([AllowAny])
def download_attachment(request, attachment_id):
    try:
        attachment = Attachment.objects.get(id=attachment_id)
        if attachment.file:
            return FileResponse(
                attachment.file.open("rb"),
                as_attachment=True,
                filename=attachment.original_filename,
            )
        return Response({"error": "File not found"}, status=404)
    except Attachment.DoesNotExist:
        return Response({"error": "Attachment not found"}, status=404)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def advanced_search(request):
    query = request.GET.get("q", "")
    status_filter = request.GET.get("status", "")
    sort = request.GET.get("sort", "created_at")
    order = request.GET.get("order", "DESC")

    sql = f"""
        SELECT t.id, t.title, t.status, t.priority, t.created_at,
               u.username as reporter_name, o.name as org_name
        FROM tickets t
        LEFT JOIN users u ON t.reporter_id = u.id
        LEFT JOIN organizations o ON t.organization_id = o.id
        WHERE (t.title LIKE '%%{query}%%' OR t.description LIKE '%%{query}%%')
    """

    if status_filter:
        sql += f" AND t.status = '{status_filter}'"

    sql += f" ORDER BY t.{sort} {order}"
    sql += " LIMIT 100"

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response({"results": results, "count": len(results)})
    except Exception as e:
        return Response(
            {"error": str(e), "query": sql},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def internal_tickets(request):
    try:
        org = request.user.organization
        if org is None:
            raise ValueError("No organization assigned")
        tickets = Ticket.objects.filter(
            organization=org, is_internal=True
        )
    except Exception:
        tickets = Ticket.objects.filter(is_internal=True)

    return Response(TicketSerializer(tickets, many=True).data)

@api_view(["GET"])
@permission_classes([AllowAny])
def public_ticket_export(request):
    export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
    if os.path.exists(export_dir):
        files = os.listdir(export_dir)
        return Response({"files": files})
    return Response({"files": []})

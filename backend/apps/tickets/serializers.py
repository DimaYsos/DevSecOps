from rest_framework import serializers

from vulnops.access import is_org_admin
from vulnops.security import escape_markdown_to_html

from .models import Ticket, Incident, Comment, Attachment


class TicketSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source="reporter.username", read_only=True, default="")
    assignee_name = serializers.CharField(source="assignee.username", read_only=True, default="")

    class Meta:
        model = Ticket
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "organization", "reporter"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or not is_org_admin(user):
            data.pop("internal_notes", None)
            data.pop("status_override", None)
        return data


class TicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = [
            "title", "description", "priority", "category", "tags",
            "assignee", "sla_due_at", "is_internal", "status_override",
            "internal_notes", "custom_fields", "organization", "status",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")
        attrs["organization"] = user.organization
        if not is_org_admin(user):
            attrs["is_internal"] = False
            attrs["status_override"] = ""
            attrs["internal_notes"] = ""
            attrs["status"] = "open"
        return attrs


class IncidentSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source="reporter.username", read_only=True, default="")
    commander_name = serializers.CharField(source="commander.username", read_only=True, default="")

    class Meta:
        model = Incident
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "organization", "reporter"]


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True, default="")

    class Meta:
        model = Comment
        fields = [
            "id", "ticket", "incident", "author", "author_name",
            "content", "content_html", "is_internal", "edited",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "author", "content_html", "edited", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not is_org_admin(user):
            attrs["is_internal"] = False
        return attrs

    def create(self, validated_data):
        validated_data["content_html"] = escape_markdown_to_html(validated_data.get("content", ""))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "content" in validated_data:
            validated_data["content_html"] = escape_markdown_to_html(validated_data["content"])
            validated_data["edited"] = True
        if "is_internal" in validated_data and not is_org_admin(getattr(self.context.get("request"), "user", None)):
            validated_data["is_internal"] = instance.is_internal
        return super().update(instance, validated_data)


class AttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            "id", "ticket", "incident", "comment", "uploaded_by",
            "organization", "filename", "original_filename", "file",
            "content_type", "file_size", "is_public", "metadata",
            "created_at", "download_url",
        ]
        read_only_fields = ["id", "filename", "file_size", "created_at", "organization", "uploaded_by", "content_type"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")
        if not is_org_admin(user):
            attrs["is_public"] = False
        return attrs

    def get_download_url(self, obj):
        return f"/api/v2/attachments/{obj.id}/download/"

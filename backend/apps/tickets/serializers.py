import markdown
from rest_framework import serializers
from .models import Ticket, Incident, Comment, Attachment

class TicketSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source="reporter.username", read_only=True, default="")
    assignee_name = serializers.CharField(source="assignee.username", read_only=True, default="")

    class Meta:
        model = Ticket
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

class TicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = [
            "title", "description", "priority", "category", "tags",
            "assignee", "sla_due_at", "is_internal", "status_override",
            "internal_notes", "custom_fields", "organization",
            "status",
        ]

class IncidentSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source="reporter.username", read_only=True, default="")
    commander_name = serializers.CharField(source="commander.username", read_only=True, default="")

    class Meta:
        model = Incident
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

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

    def create(self, validated_data):
        content = validated_data.get("content", "")
        validated_data["content_html"] = markdown.markdown(
            content,
            extensions=["extra", "codehilite", "tables"],
            output_format="html5",
        )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "content" in validated_data:
            validated_data["content_html"] = markdown.markdown(
                validated_data["content"],
                extensions=["extra", "codehilite", "tables"],
                output_format="html5",
            )
            validated_data["edited"] = True
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
        read_only_fields = ["id", "filename", "file_size", "created_at"]

    def get_download_url(self, obj):
        if obj.file:
            return f"/media/{obj.file.name}"
        return None

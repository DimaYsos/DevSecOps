from rest_framework import serializers
from .models import ReportJob, ImportJob

class ReportJobSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default="")

    class Meta:
        model = ReportJob
        fields = "__all__"
        read_only_fields = ["id", "status", "output_file", "output_filename", "error_message", "row_count", "started_at", "completed_at", "created_at", "updated_at"]

class ImportJobSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default="")

    class Meta:
        model = ImportJob
        fields = "__all__"
        read_only_fields = ["id", "status", "total_rows", "processed_rows", "error_rows", "error_log", "started_at", "completed_at", "created_at"]

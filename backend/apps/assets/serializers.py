from rest_framework import serializers

from .models import Asset, AssetLink


class AssetSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.username", read_only=True, default="")

    class Meta:
        model = Asset
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "organization", "owner"]


class AssetLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetLink
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

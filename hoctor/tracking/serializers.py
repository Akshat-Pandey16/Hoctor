from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from hoctor.venues.models import Venue

from .models import AccessPointSample, Device, Fingerprint, Scan


class AccessPointSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPointSample
        fields = ("id", "ssid", "bssid", "signal", "frequency")
        read_only_fields = ("id",)


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ("id", "name", "description", "last_seen_at", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class FingerprintSerializer(serializers.ModelSerializer):
    samples = AccessPointSampleSerializer(many=True)
    venue_slug = serializers.SlugRelatedField(
        source="room.venue", slug_field="slug", read_only=True
    )
    room_slug = serializers.SlugRelatedField(source="room", slug_field="slug", read_only=True)

    class Meta:
        model = Fingerprint
        fields = (
            "id",
            "room",
            "room_slug",
            "venue_slug",
            "device",
            "captured_at",
            "notes",
            "samples",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "room_slug", "venue_slug", "created_at", "updated_at")

    def validate_samples(self, value):
        if not value:
            raise serializers.ValidationError("At least one access point sample is required.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        samples_data = validated_data.pop("samples")
        if not validated_data.get("captured_at"):
            validated_data["captured_at"] = timezone.now()
        fingerprint = Fingerprint.objects.create(**validated_data)
        AccessPointSample.objects.bulk_create(
            [AccessPointSample(fingerprint=fingerprint, **s) for s in samples_data]
        )
        return fingerprint


class ScanInputSerializer(serializers.Serializer):
    venue = serializers.SlugRelatedField(slug_field="slug", queryset=Venue.objects.all())
    device = serializers.CharField(required=False, allow_blank=True)
    samples = AccessPointSampleSerializer(many=True, required=False)
    use_scanner = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if not attrs.get("samples") and not attrs.get("use_scanner"):
            raise serializers.ValidationError(
                "Provide `samples` or set `use_scanner=true` to scan from hardware."
            )
        return attrs


class ScanSerializer(serializers.ModelSerializer):
    venue_slug = serializers.SlugRelatedField(source="venue", slug_field="slug", read_only=True)
    device_name = serializers.SlugRelatedField(source="device", slug_field="name", read_only=True)
    predicted_room_slug = serializers.SlugRelatedField(
        source="predicted_room", slug_field="slug", read_only=True
    )
    predicted_room_name = serializers.SlugRelatedField(
        source="predicted_room", slug_field="name", read_only=True
    )

    class Meta:
        model = Scan
        fields = (
            "id",
            "venue",
            "venue_slug",
            "device",
            "device_name",
            "predicted_room",
            "predicted_room_slug",
            "predicted_room_name",
            "confidence",
            "probabilities",
            "status",
            "error",
            "raw_samples",
            "created_at",
        )
        read_only_fields = fields

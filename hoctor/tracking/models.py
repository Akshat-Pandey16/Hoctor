from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from hoctor.venues.models import Room, TimeStampedModel, Venue


class Device(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    description = models.CharField(max_length=255, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Fingerprint(TimeStampedModel):
    room = models.ForeignKey(Room, related_name="fingerprints", on_delete=models.CASCADE)
    device = models.ForeignKey(
        Device,
        related_name="fingerprints",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    captured_at = models.DateTimeField(db_index=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-captured_at",)
        indexes = [
            models.Index(fields=("room", "-captured_at"), name="fp_room_captured_idx"),
        ]

    def __str__(self) -> str:
        return f"Fingerprint #{self.pk} @ {self.room}"


class AccessPointSample(models.Model):
    fingerprint = models.ForeignKey(Fingerprint, related_name="samples", on_delete=models.CASCADE)
    ssid = models.CharField(max_length=64, db_index=True)
    bssid = models.CharField(max_length=32, blank=True, db_index=True)
    signal = models.IntegerField(
        validators=[MinValueValidator(-120), MaxValueValidator(0)],
    )
    frequency = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("-signal",)
        constraints = [
            models.UniqueConstraint(
                fields=("fingerprint", "bssid"),
                condition=~models.Q(bssid=""),
                name="ap_unique_bssid_per_fingerprint",
            ),
        ]
        indexes = [
            models.Index(fields=("ssid", "bssid"), name="ap_ssid_bssid_idx"),
        ]

    def __str__(self) -> str:
        label = self.bssid or self.ssid
        return f"{label} ({self.signal} dBm)"


class Scan(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PREDICTED = "predicted", "Predicted"
        FAILED = "failed", "Failed"

    venue = models.ForeignKey(Venue, related_name="scans", on_delete=models.CASCADE)
    device = models.ForeignKey(
        Device,
        related_name="scans",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    predicted_room = models.ForeignKey(
        Room,
        related_name="predicted_for",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    confidence = models.FloatField(null=True, blank=True)
    probabilities = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    error = models.CharField(max_length=255, blank=True)
    raw_samples = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("venue", "-created_at"), name="scan_venue_created_idx"),
            models.Index(fields=("device", "-created_at"), name="scan_device_created_idx"),
        ]

    def __str__(self) -> str:
        room = self.predicted_room.name if self.predicted_room else "?"
        return f"Scan #{self.pk} -> {room}"

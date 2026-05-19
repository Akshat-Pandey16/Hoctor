from __future__ import annotations

from django.contrib import admin

from .models import AccessPointSample, Device, Fingerprint, Scan


class AccessPointSampleInline(admin.TabularInline):
    model = AccessPointSample
    extra = 0
    fields = ("ssid", "bssid", "signal", "frequency")


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "last_seen_at", "created_at")
    list_filter = ("created_at", "last_seen_at")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Fingerprint)
class FingerprintAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "device", "captured_at", "sample_count")
    list_filter = ("room__venue", "captured_at")
    search_fields = ("room__name", "room__venue__name", "device__name")
    autocomplete_fields = ("room", "device")
    inlines = [AccessPointSampleInline]
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "captured_at"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("room", "room__venue", "device")
            .prefetch_related("samples")
        )

    @admin.display(description="Samples")
    def sample_count(self, obj: Fingerprint) -> int:
        return obj.samples.count()


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "venue",
        "device",
        "predicted_room",
        "confidence",
        "status",
        "created_at",
    )
    list_filter = ("status", "venue", "created_at")
    search_fields = (
        "venue__name",
        "device__name",
        "predicted_room__name",
    )
    autocomplete_fields = ("venue", "device", "predicted_room")
    readonly_fields = (
        "created_at",
        "updated_at",
        "probabilities",
        "raw_samples",
        "error",
    )
    date_hierarchy = "created_at"

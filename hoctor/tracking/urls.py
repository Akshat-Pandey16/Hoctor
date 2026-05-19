from __future__ import annotations

from django.urls import path

from .views import (
    CaptureView,
    DeviceDetailView,
    DeviceListView,
    FingerprintDetailView,
    FingerprintListView,
    HealthView,
    RoomStatsView,
    ScanDetailView,
    ScanListView,
)

app_name = "tracking"

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("devices/", DeviceListView.as_view(), name="device-list"),
    path("devices/<str:name>/", DeviceDetailView.as_view(), name="device-detail"),
    path("fingerprints/", FingerprintListView.as_view(), name="fingerprint-list"),
    path("fingerprints/<int:pk>/", FingerprintDetailView.as_view(), name="fingerprint-detail"),
    path("scans/", ScanListView.as_view(), name="scan-list"),
    path("scans/<int:pk>/", ScanDetailView.as_view(), name="scan-detail"),
    path("capture/", CaptureView.as_view(), name="capture"),
    path(
        "venues/<slug:venue_slug>/rooms/<slug:room_slug>/stats/",
        RoomStatsView.as_view(),
        name="room-stats",
    ),
]

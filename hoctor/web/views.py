from __future__ import annotations

from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.views.generic import TemplateView

from hoctor.tracking.models import Device, Scan
from hoctor.venues.models import Venue


class LandingView(TemplateView):
    template_name = "web/landing.html"


class DashboardView(TemplateView):
    template_name = "web/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["venues"] = Venue.objects.annotate(
            room_count=Count("rooms", distinct=True),
            fingerprint_count=Count("rooms__fingerprints", distinct=True),
        ).order_by("name")
        ctx["devices"] = Device.objects.order_by("-last_seen_at", "name")
        ctx["recent_scans"] = Scan.objects.select_related(
            "venue", "device", "predicted_room"
        ).order_by("-created_at")[:8]
        return ctx


class TrackView(TemplateView):
    template_name = "web/track.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["venues"] = Venue.objects.prefetch_related("rooms").order_by("name")
        ctx["devices"] = Device.objects.order_by("name")
        return ctx


class CaptureView(TemplateView):
    template_name = "web/capture.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["venues"] = Venue.objects.prefetch_related("rooms").order_by("name")
        ctx["devices"] = Device.objects.order_by("name")
        return ctx


def venue_detail(request, slug: str):
    venue = get_object_or_404(Venue.objects.prefetch_related("rooms__fingerprints"), slug=slug)
    rooms = list(
        venue.rooms.annotate(fingerprint_count=Count("fingerprints")).order_by("floor", "name")
    )
    recent_scans = (
        Scan.objects.filter(venue=venue)
        .select_related("device", "predicted_room")
        .order_by("-created_at")[:10]
    )
    return render(
        request,
        "web/venue_detail.html",
        {"venue": venue, "rooms": rooms, "recent_scans": recent_scans},
    )

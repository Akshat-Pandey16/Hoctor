from __future__ import annotations

from django.urls import path

from .views import CaptureView, DashboardView, LandingView, TrackView, venue_detail

app_name = "web"

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("track/", TrackView.as_view(), name="track"),
    path("capture/", CaptureView.as_view(), name="capture"),
    path("venues/<slug:slug>/", venue_detail, name="venue-detail"),
]

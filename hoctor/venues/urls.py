from __future__ import annotations

from django.urls import path

from .views import RoomDetailView, RoomListView, VenueDetailView, VenueListView

app_name = "venues"

urlpatterns = [
    path("venues/", VenueListView.as_view(), name="venue-list"),
    path("venues/<slug:slug>/", VenueDetailView.as_view(), name="venue-detail"),
    path(
        "venues/<slug:venue_slug>/rooms/",
        RoomListView.as_view(),
        name="room-list",
    ),
    path(
        "venues/<slug:venue_slug>/rooms/<slug:room_slug>/",
        RoomDetailView.as_view(),
        name="room-detail",
    ),
]

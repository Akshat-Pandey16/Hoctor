from __future__ import annotations

import pytest

from hoctor.venues.models import Room, Venue


@pytest.mark.django_db
class TestVenueAPI:
    def test_list_empty(self, api_client):
        res = api_client.get("/api/v1/venues/")
        assert res.status_code == 200
        assert res.json() == []

    def test_create(self, api_client):
        res = api_client.post(
            "/api/v1/venues/",
            data={"name": "Hash Society Home", "address": "Test"},
            format="json",
        )
        assert res.status_code == 201
        assert res.json()["slug"] == "hash-society-home"
        assert Venue.objects.count() == 1

    def test_detail_and_patch(self, api_client):
        Venue.objects.create(name="V")
        res = api_client.patch("/api/v1/venues/v/", data={"description": "hello"}, format="json")
        assert res.status_code == 200
        assert res.json()["description"] == "hello"

    def test_delete(self, api_client):
        Venue.objects.create(name="V")
        res = api_client.delete("/api/v1/venues/v/")
        assert res.status_code == 204
        assert Venue.objects.count() == 0

    def test_put_not_allowed(self, api_client):
        Venue.objects.create(name="V")
        res = api_client.put("/api/v1/venues/v/", data={"name": "X"}, format="json")
        assert res.status_code == 405


@pytest.mark.django_db
class TestRoomAPI:
    def test_nested_under_venue(self, api_client):
        v = Venue.objects.create(name="V")
        res = api_client.post(
            f"/api/v1/venues/{v.slug}/rooms/",
            data={"name": "Lab 01", "room_number": 1},
            format="json",
        )
        assert res.status_code == 201, res.json()
        assert Room.objects.count() == 1
        assert res.json()["venue_slug"] == "v"

from __future__ import annotations

import pytest
from django.utils import timezone

from hoctor.tracking.models import AccessPointSample, Device, Fingerprint, Scan
from hoctor.venues.models import Room, Venue


@pytest.fixture
def trained_venue(db):
    venue = Venue.objects.create(name="V")
    room_a = Room.objects.create(venue=venue, name="A")
    room_b = Room.objects.create(venue=venue, name="B")
    for _ in range(4):
        for room, signals in [
            (room_a, {"aa:01": -40, "aa:02": -80}),
            (room_b, {"aa:01": -85, "aa:02": -40}),
        ]:
            fp = Fingerprint.objects.create(room=room, captured_at=timezone.now())
            AccessPointSample.objects.bulk_create(
                [
                    AccessPointSample(fingerprint=fp, ssid=f"s-{b}", bssid=b, signal=s)
                    for b, s in signals.items()
                ]
            )
    return venue, room_a, room_b


@pytest.mark.django_db
class TestFingerprintAPI:
    def test_create_with_samples(self, api_client):
        venue = Venue.objects.create(name="V")
        room = Room.objects.create(venue=venue, name="Lab 01")
        res = api_client.post(
            "/api/v1/fingerprints/",
            data={
                "room": room.pk,
                "captured_at": timezone.now().isoformat(),
                "samples": [
                    {"ssid": "x", "bssid": "00:11:22:33:44:55", "signal": -50},
                    {"ssid": "y", "bssid": "00:11:22:33:44:56", "signal": -65},
                ],
            },
            format="json",
        )
        assert res.status_code == 201, res.json()
        assert Fingerprint.objects.count() == 1
        assert AccessPointSample.objects.count() == 2

    def test_create_requires_samples(self, api_client):
        venue = Venue.objects.create(name="V")
        room = Room.objects.create(venue=venue, name="L")
        res = api_client.post(
            "/api/v1/fingerprints/",
            data={"room": room.pk, "samples": []},
            format="json",
        )
        assert res.status_code == 400


@pytest.mark.django_db
class TestScanAPI:
    def test_scan_returns_prediction(self, api_client, trained_venue):
        venue, room_a, _ = trained_venue
        res = api_client.post(
            "/api/v1/scans/",
            data={
                "venue": venue.slug,
                "device": "tester",
                "samples": [
                    {"ssid": "s", "bssid": "aa:01", "signal": -42},
                    {"ssid": "s", "bssid": "aa:02", "signal": -82},
                ],
            },
            format="json",
        )
        assert res.status_code == 201, res.json()
        body = res.json()
        assert body["predicted_room"] == room_a.pk
        assert body["status"] == Scan.Status.PREDICTED
        assert body["device_name"] == "tester"
        assert Device.objects.filter(name="tester").exists()

    def test_scan_requires_samples_or_scanner(self, api_client, trained_venue):
        venue, _, _ = trained_venue
        res = api_client.post(
            "/api/v1/scans/",
            data={"venue": venue.slug},
            format="json",
        )
        assert res.status_code == 400

    def test_scan_with_hardware_uses_scanner(self, api_client, trained_venue):
        venue, _, _ = trained_venue
        res = api_client.post(
            "/api/v1/scans/",
            data={"venue": venue.slug, "use_scanner": True},
            format="json",
        )
        assert res.status_code in {200, 201}

    def test_list_filters_by_venue(self, api_client, trained_venue):
        venue, _, _ = trained_venue
        api_client.post(
            "/api/v1/scans/",
            data={
                "venue": venue.slug,
                "samples": [{"ssid": "x", "bssid": "aa:01", "signal": -40}],
            },
            format="json",
        )
        res = api_client.get(f"/api/v1/scans/?venue={venue.slug}")
        assert res.status_code == 200
        assert len(res.json()) >= 1


@pytest.mark.django_db
class TestHealth:
    def test_health(self, api_client):
        res = api_client.get("/api/v1/health/")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

from __future__ import annotations

import pytest
from django.utils import timezone

from hoctor.tracking.models import AccessPointSample, Fingerprint
from hoctor.tracking.services import AccessPointReading, get_predictor
from hoctor.venues.models import Room, Venue


def _train_fingerprint(room: Room, signals: dict[str, int]) -> Fingerprint:
    fp = Fingerprint.objects.create(room=room, captured_at=timezone.now())
    AccessPointSample.objects.bulk_create(
        [
            AccessPointSample(
                fingerprint=fp,
                ssid=f"ssid-{bssid}",
                bssid=bssid,
                signal=signal,
            )
            for bssid, signal in signals.items()
        ]
    )
    return fp


@pytest.mark.django_db
class TestPredictor:
    def test_insufficient_data_returns_error(self):
        venue = Venue.objects.create(name="V")
        Room.objects.create(venue=venue, name="A")
        readings = [AccessPointReading(ssid="x", bssid="00:11", signal=-50)]
        result = get_predictor().predict(venue, readings)
        assert not result.succeeded
        assert result.error == "insufficient_training_data"

    def test_empty_scan_returns_error(self):
        venue = Venue.objects.create(name="V")
        result = get_predictor().predict(venue, [])
        assert result.error == "empty_scan"

    def test_predicts_room_from_signature(self):
        venue = Venue.objects.create(name="V")
        room_a = Room.objects.create(venue=venue, name="A")
        room_b = Room.objects.create(venue=venue, name="B")

        for _ in range(4):
            _train_fingerprint(room_a, {"aa:01": -40, "aa:02": -80, "aa:03": -85})
            _train_fingerprint(room_b, {"aa:01": -85, "aa:02": -40, "aa:03": -45})

        readings_a = [
            AccessPointReading(ssid="s1", bssid="aa:01", signal=-42),
            AccessPointReading(ssid="s2", bssid="aa:02", signal=-78),
            AccessPointReading(ssid="s3", bssid="aa:03", signal=-86),
        ]
        result = get_predictor().predict(venue, readings_a)
        assert result.succeeded
        assert result.room_id == room_a.pk
        assert result.confidence > 0.5

        readings_b = [
            AccessPointReading(ssid="s1", bssid="aa:01", signal=-86),
            AccessPointReading(ssid="s2", bssid="aa:02", signal=-41),
            AccessPointReading(ssid="s3", bssid="aa:03", signal=-44),
        ]
        result_b = get_predictor().predict(venue, readings_b)
        assert result_b.room_id == room_b.pk

    def test_diagnostics_reports_accuracy(self):
        venue = Venue.objects.create(name="V")
        room_a = Room.objects.create(venue=venue, name="A")
        room_b = Room.objects.create(venue=venue, name="B")
        for _ in range(4):
            _train_fingerprint(room_a, {"aa:01": -40, "aa:02": -80})
            _train_fingerprint(room_b, {"aa:01": -85, "aa:02": -40})
        diag = get_predictor().diagnostics(venue)
        assert diag.fingerprint_count == 8
        assert diag.room_count == 2
        assert diag.classifier == "knn"
        assert diag.accuracy is not None
        assert diag.accuracy >= 0.75

    def test_diagnostics_empty_venue_emits_notes(self):
        venue = Venue.objects.create(name="V")
        diag = get_predictor().diagnostics(venue)
        assert diag.fingerprint_count == 0
        assert diag.accuracy is None
        assert any("at least one fingerprint" in n for n in diag.notes)

    def test_invalidates_on_new_fingerprint(self):
        venue = Venue.objects.create(name="V")
        room_a = Room.objects.create(venue=venue, name="A")
        room_b = Room.objects.create(venue=venue, name="B")
        for _ in range(3):
            _train_fingerprint(room_a, {"x:1": -40})
            _train_fingerprint(room_b, {"x:2": -40})
        predictor = get_predictor()
        predictor.predict(venue, [AccessPointReading("s", "x:1", -45)])
        assert venue.pk in predictor._cache
        _train_fingerprint(room_a, {"x:1": -38})
        assert venue.pk not in predictor._cache

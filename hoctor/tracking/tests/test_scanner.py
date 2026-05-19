from __future__ import annotations

import pytest

from hoctor.tracking.services import get_scanner
from hoctor.tracking.services.scanner import MockWifiScanner


def test_mock_scanner_returns_readings():
    scanner = MockWifiScanner(seed="room-1")
    readings = scanner.scan()
    assert len(readings) > 0
    assert all(-100 <= r.signal <= 0 for r in readings)
    assert all(r.bssid for r in readings)


def test_mock_scanner_is_deterministic():
    a = MockWifiScanner(seed="x").scan()
    b = MockWifiScanner(seed="x").scan()
    assert [(r.ssid, r.bssid, r.signal) for r in a] == [(r.ssid, r.bssid, r.signal) for r in b]


def test_get_scanner_default_is_mock():
    assert isinstance(get_scanner(), MockWifiScanner)


def test_get_scanner_unknown_raises():
    with pytest.raises(ValueError):
        get_scanner("nope")

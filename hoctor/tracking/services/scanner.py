from __future__ import annotations

import hashlib
import logging
import random
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AccessPointReading:
    ssid: str
    bssid: str
    signal: int
    frequency: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "ssid": self.ssid,
            "bssid": self.bssid,
            "signal": self.signal,
            "frequency": self.frequency,
        }


class WifiScanner(Protocol):
    def scan(self) -> list[AccessPointReading]: ...


class MockWifiScanner:
    DEFAULT_SSIDS = (
        "htl_main",
        "htl_hashsocietyhome",
        "htl_hack1",
        "htl_hack2",
        "htl_hack3",
        "entrance_bitd_cse",
        "cse_lab01",
        "cse_lab02",
    )

    def __init__(self, seed: str | None = None) -> None:
        self._seed = seed or "hoctor-default"

    def scan(self) -> list[AccessPointReading]:
        rng = random.Random(self._seed)
        readings: list[AccessPointReading] = []
        for ssid in self.DEFAULT_SSIDS:
            digest = hashlib.sha1(f"{self._seed}:{ssid}".encode()).hexdigest()
            bssid = ":".join(digest[i : i + 2] for i in range(0, 12, 2))
            signal = rng.randint(-85, -35)
            readings.append(
                AccessPointReading(ssid=ssid, bssid=bssid, signal=signal, frequency=2412)
            )
        return readings


class HardwareWifiScanner:
    def scan(self) -> list[AccessPointReading]:
        try:
            from access_points import get_scanner as _get_scanner
        except ImportError as exc:
            raise RuntimeError(
                "access_points is not installed. Install the `scan` extra: `uv sync --extra scan`."
            ) from exc

        scanner = _get_scanner()
        readings: list[AccessPointReading] = []
        for ap in scanner.get_access_points():
            quality_raw = getattr(ap, "quality", 0)
            try:
                quality = int(quality_raw)
            except (TypeError, ValueError):
                quality = 0
            signal = quality - 100 if quality > 0 else int(quality_raw or -100)
            readings.append(
                AccessPointReading(
                    ssid=getattr(ap, "ssid", "") or "",
                    bssid=getattr(ap, "bssid", "") or "",
                    signal=signal,
                    frequency=None,
                )
            )
        return readings


def get_scanner(backend: str | None = None) -> WifiScanner:
    name = (backend or settings.HOCTOR["SCANNER_BACKEND"]).lower()
    if name == "mock":
        return MockWifiScanner()
    if name in {"hardware", "real", "access_points"}:
        return HardwareWifiScanner()
    raise ValueError(f"Unknown scanner backend: {name!r}")

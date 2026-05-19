from __future__ import annotations

import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from hoctor.tracking.models import AccessPointSample, Device, Fingerprint
from hoctor.tracking.services import get_scanner
from hoctor.venues.models import Room, Venue


class Command(BaseCommand):
    help = "Capture one or more Wi-Fi fingerprints for a room using the configured scanner."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--venue", required=True, help="Venue slug (e.g. my-home)")
        parser.add_argument("--room", required=True, help="Room slug within that venue")
        parser.add_argument("--device", default=None, help="Optional device name")
        parser.add_argument(
            "--samples",
            type=int,
            default=5,
            help="How many fingerprints to capture in this run (default 5).",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=2.0,
            help="Seconds to wait between scans (default 2).",
        )
        parser.add_argument(
            "--backend",
            default=None,
            help="Override scanner backend (mock | hardware).",
        )

    @transaction.atomic
    def handle(self, *args, **opts) -> None:
        try:
            venue = Venue.objects.get(slug=opts["venue"])
        except Venue.DoesNotExist as exc:
            raise CommandError(f"No venue with slug {opts['venue']!r}.") from exc
        try:
            room = Room.objects.get(venue=venue, slug=opts["room"])
        except Room.DoesNotExist as exc:
            raise CommandError(
                f"No room with slug {opts['room']!r} in venue {venue.slug!r}."
            ) from exc

        device = None
        if opts["device"]:
            device, _ = Device.objects.get_or_create(name=opts["device"].strip())

        scanner = get_scanner(opts["backend"])
        n = opts["samples"]
        interval = max(opts["interval"], 0.0)

        self.stdout.write(
            self.style.NOTICE(
                f"Capturing {n} fingerprint(s) for {venue.name} / {room.name} "
                f"(backend={scanner.__class__.__name__})"
            )
        )

        for i in range(1, n + 1):
            readings = scanner.scan()
            if not readings:
                self.stdout.write(self.style.WARNING(f"[{i}/{n}] empty scan, skipping"))
                continue
            fp = Fingerprint.objects.create(
                room=room,
                device=device,
                captured_at=timezone.now(),
                notes=f"capture_fingerprint {i}/{n}",
            )
            AccessPointSample.objects.bulk_create(
                [
                    AccessPointSample(
                        fingerprint=fp,
                        ssid=r.ssid,
                        bssid=r.bssid,
                        signal=r.signal,
                        frequency=r.frequency,
                    )
                    for r in readings
                ]
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{i}/{n}] fingerprint #{fp.pk} stored with {len(readings)} samples"
                )
            )
            if i < n and interval > 0:
                time.sleep(interval)

        self.stdout.write(self.style.SUCCESS("Done."))

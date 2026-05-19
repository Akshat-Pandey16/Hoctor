from __future__ import annotations

import hashlib
import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from hoctor.tracking.models import AccessPointSample, Device, Fingerprint
from hoctor.venues.models import Room, Venue

VENUES = [
    {
        "name": "BitDurg CSE Block",
        "description": "Computer Science department building.",
        "address": "Bhilai Institute of Technology, Durg",
        "rooms": [
            ("Entrance", 0, 0),
            ("Lab 01", 101, 1),
            ("Lab 02", 102, 1),
            ("Faculty Room", 201, 2),
        ],
    },
    {
        "name": "Hash Society Home",
        "description": "Demo apartment for indoor positioning.",
        "address": "Demo location",
        "rooms": [
            ("Living Room", 1, 0),
            ("Hacking Zone", 2, 0),
            ("Kitchen", 3, 0),
            ("Bedroom", 4, 1),
        ],
    },
]

DEVICES = ["Tejas", "Sanskar", "Yash", "Akshat"]


class Command(BaseCommand):
    help = "Populate Hoctor with demo venues, rooms, devices, and Wi-Fi fingerprints."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--fingerprints",
            type=int,
            default=8,
            help="Fingerprints to generate per room (default: 8).",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing venues/devices before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        if options["reset"]:
            Venue.objects.all().delete()
            Device.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared existing data."))

        devices = [Device.objects.get_or_create(name=name)[0] for name in DEVICES]
        created_venues, created_rooms, created_fps = 0, 0, 0

        for venue_data in VENUES:
            venue, was_created = Venue.objects.update_or_create(
                name=venue_data["name"],
                defaults={
                    "description": venue_data["description"],
                    "address": venue_data["address"],
                },
            )
            created_venues += int(was_created)

            rooms = []
            for room_name, room_number, floor in venue_data["rooms"]:
                room, room_created = Room.objects.update_or_create(
                    venue=venue,
                    name=room_name,
                    defaults={"room_number": room_number, "floor": floor},
                )
                rooms.append(room)
                created_rooms += int(room_created)

            for room in rooms:
                created_fps += self._seed_fingerprints(
                    room=room,
                    devices=devices,
                    n=options["fingerprints"],
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded: venues={created_venues} rooms={created_rooms} fingerprints={created_fps}"
            )
        )

    def _seed_fingerprints(self, room: Room, devices: list[Device], n: int) -> int:
        rng = random.Random(f"{room.venue.slug}:{room.slug}")
        ssids = [f"ap_{room.venue.slug}_{i}" for i in range(12)]
        base_signals = {ssid: rng.randint(-90, -35) for ssid in ssids}

        created = 0
        for i in range(n):
            fp = Fingerprint.objects.create(
                room=room,
                device=devices[i % len(devices)],
                captured_at=timezone.now(),
                notes=f"seed sample {i + 1}",
            )
            samples = []
            for ssid in ssids:
                jitter = rng.randint(-6, 6)
                signal = max(min(base_signals[ssid] + jitter, -20), -100)
                bssid_digest = hashlib.sha1(f"{room.slug}:{ssid}".encode()).hexdigest()
                bssid = ":".join(bssid_digest[j : j + 2] for j in range(0, 12, 2))
                samples.append(
                    AccessPointSample(
                        fingerprint=fp,
                        ssid=ssid,
                        bssid=bssid,
                        signal=signal,
                        frequency=2412,
                    )
                )
            AccessPointSample.objects.bulk_create(samples)
            created += 1
        return created

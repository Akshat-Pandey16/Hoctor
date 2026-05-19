from __future__ import annotations

import factory
from django.utils import timezone

from hoctor.tracking.models import AccessPointSample, Device, Fingerprint, Scan
from hoctor.venues.models import Room, Venue


class VenueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Venue

    name = factory.Sequence(lambda n: f"Venue {n}")
    address = "Test address"


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Room

    venue = factory.SubFactory(VenueFactory)
    name = factory.Sequence(lambda n: f"Room {n}")
    floor = 0


class DeviceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Device

    name = factory.Sequence(lambda n: f"device-{n}")


class FingerprintFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Fingerprint

    room = factory.SubFactory(RoomFactory)
    device = factory.SubFactory(DeviceFactory)
    captured_at = factory.LazyFunction(timezone.now)


class AccessPointSampleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AccessPointSample

    fingerprint = factory.SubFactory(FingerprintFactory)
    ssid = factory.Sequence(lambda n: f"ssid-{n}")
    bssid = factory.Sequence(lambda n: f"00:11:22:33:44:{n:02x}")
    signal = -55


class ScanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Scan

    venue = factory.SubFactory(VenueFactory)

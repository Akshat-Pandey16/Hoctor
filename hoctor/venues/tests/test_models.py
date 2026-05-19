from __future__ import annotations

import pytest
from django.db import IntegrityError

from hoctor.venues.models import Room, Venue


@pytest.mark.django_db
class TestVenue:
    def test_slug_is_auto_generated_from_name(self):
        venue = Venue.objects.create(name="BitDurg CSE Block")
        assert venue.slug == "bitdurg-cse-block"

    def test_name_is_unique(self):
        Venue.objects.create(name="Same")
        with pytest.raises(IntegrityError):
            Venue.objects.create(name="Same")

    def test_str(self):
        assert str(Venue.objects.create(name="X")) == "X"


@pytest.mark.django_db
class TestRoom:
    def test_unique_name_per_venue(self):
        v = Venue.objects.create(name="V")
        Room.objects.create(venue=v, name="Lab 01")
        with pytest.raises(IntegrityError):
            Room.objects.create(venue=v, name="Lab 01")

    def test_same_name_in_different_venues(self):
        v1 = Venue.objects.create(name="V1")
        v2 = Venue.objects.create(name="V2")
        Room.objects.create(venue=v1, name="Lab 01")
        Room.objects.create(venue=v2, name="Lab 01")

    def test_slug_auto(self):
        v = Venue.objects.create(name="V")
        room = Room.objects.create(venue=v, name="Lab 01")
        assert room.slug == "lab-01"

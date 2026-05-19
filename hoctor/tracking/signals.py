from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import AccessPointSample, Fingerprint
from .services import get_predictor


@receiver([post_save, post_delete], sender=Fingerprint)
def _invalidate_on_fingerprint_change(sender, instance: Fingerprint, **kwargs) -> None:
    venue = instance.room.venue
    get_predictor().invalidate(venue)


@receiver([post_save, post_delete], sender=AccessPointSample)
def _invalidate_on_sample_change(sender, instance: AccessPointSample, **kwargs) -> None:
    venue = instance.fingerprint.room.venue
    get_predictor().invalidate(venue)

from __future__ import annotations

from django.apps import AppConfig


class VenuesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hoctor.venues"
    label = "venues"
    verbose_name = "Venues"

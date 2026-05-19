from __future__ import annotations

from django.apps import AppConfig


class TrackingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hoctor.tracking"
    label = "tracking"
    verbose_name = "Tracking"

    def ready(self) -> None:
        from . import signals  # noqa: F401

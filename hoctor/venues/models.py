from __future__ import annotations

from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Venue(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ("name",)
        indexes = [
            models.Index(fields=("slug",), name="venue_slug_idx"),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: object, **kwargs: object) -> None:
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)


class Room(TimeStampedModel):
    venue = models.ForeignKey(Venue, related_name="rooms", on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, blank=True)
    room_number = models.PositiveIntegerField(null=True, blank=True)
    floor = models.IntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("venue__name", "floor", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("venue", "slug"),
                name="room_unique_slug_per_venue",
            ),
            models.UniqueConstraint(
                fields=("venue", "name"),
                name="room_unique_name_per_venue",
            ),
        ]
        indexes = [
            models.Index(fields=("venue", "floor"), name="room_venue_floor_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.venue.name} / {self.name}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)

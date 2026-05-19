from __future__ import annotations

from rest_framework import serializers

from .models import Room, Venue


class RoomSerializer(serializers.ModelSerializer):
    venue_slug = serializers.SlugRelatedField(source="venue", slug_field="slug", read_only=True)

    class Meta:
        model = Room
        fields = (
            "id",
            "venue",
            "venue_slug",
            "name",
            "slug",
            "room_number",
            "floor",
            "description",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "venue_slug", "created_at", "updated_at")


class VenueSerializer(serializers.ModelSerializer):
    room_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Venue
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "address",
            "latitude",
            "longitude",
            "room_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "room_count", "created_at", "updated_at")


class VenueDetailSerializer(VenueSerializer):
    rooms = RoomSerializer(many=True, read_only=True)

    class Meta(VenueSerializer.Meta):
        fields = (*VenueSerializer.Meta.fields, "rooms")

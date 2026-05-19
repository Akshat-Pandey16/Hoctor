from __future__ import annotations

from django.contrib import admin

from .models import Room, Venue


class RoomInline(admin.TabularInline):
    model = Room
    extra = 0
    fields = ("name", "room_number", "floor")
    show_change_link = True


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "address", "room_count", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "slug", "address")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [RoomInline]
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("rooms")

    @admin.display(description="Rooms")
    def room_count(self, obj: Venue) -> int:
        return obj.rooms.count()


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "venue", "room_number", "floor", "created_at")
    list_filter = ("venue", "floor")
    search_fields = ("name", "venue__name")
    autocomplete_fields = ("venue",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")

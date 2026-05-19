from __future__ import annotations

from django.db.models import Count
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Room, Venue
from .serializers import RoomSerializer, VenueDetailSerializer, VenueSerializer


class VenueListView(APIView):
    serializer_class = VenueSerializer

    @extend_schema(
        operation_id="venues_list",
        responses=VenueSerializer(many=True),
    )
    def get(self, request):
        queryset = Venue.objects.annotate(room_count=Count("rooms")).order_by("name")
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)
        serializer = VenueSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        operation_id="venues_create",
        request=VenueSerializer,
        responses={201: VenueSerializer},
    )
    def post(self, request):
        serializer = VenueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class VenueDetailView(APIView):
    serializer_class = VenueDetailSerializer

    def get_object(self, slug: str) -> Venue:
        return get_object_or_404(
            Venue.objects.annotate(room_count=Count("rooms")).prefetch_related("rooms"),
            slug=slug,
        )

    @extend_schema(operation_id="venues_retrieve", responses=VenueDetailSerializer)
    def get(self, request, slug: str):
        venue = self.get_object(slug)
        return Response(VenueDetailSerializer(venue).data)

    @extend_schema(
        operation_id="venues_partial_update",
        request=VenueSerializer,
        responses=VenueSerializer,
    )
    def patch(self, request, slug: str):
        venue = self.get_object(slug)
        serializer = VenueSerializer(venue, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(operation_id="venues_destroy", responses={204: None})
    def delete(self, request, slug: str):
        self.get_object(slug).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoomListView(APIView):
    serializer_class = RoomSerializer

    @extend_schema(operation_id="rooms_list", responses=RoomSerializer(many=True))
    def get(self, request, venue_slug: str):
        venue = get_object_or_404(Venue, slug=venue_slug)
        serializer = RoomSerializer(venue.rooms.all(), many=True)
        return Response(serializer.data)

    @extend_schema(
        operation_id="rooms_create",
        request=RoomSerializer,
        responses={201: RoomSerializer},
    )
    def post(self, request, venue_slug: str):
        venue = get_object_or_404(Venue, slug=venue_slug)
        data = {**request.data, "venue": venue.pk}
        serializer = RoomSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RoomDetailView(APIView):
    serializer_class = RoomSerializer

    def get_object(self, venue_slug: str, room_slug: str) -> Room:
        return get_object_or_404(
            Room.objects.select_related("venue"),
            venue__slug=venue_slug,
            slug=room_slug,
        )

    @extend_schema(operation_id="rooms_retrieve", responses=RoomSerializer)
    def get(self, request, venue_slug: str, room_slug: str):
        return Response(RoomSerializer(self.get_object(venue_slug, room_slug)).data)

    @extend_schema(
        operation_id="rooms_partial_update",
        request=RoomSerializer,
        responses=RoomSerializer,
    )
    def patch(self, request, venue_slug: str, room_slug: str):
        room = self.get_object(venue_slug, room_slug)
        serializer = RoomSerializer(room, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(operation_id="rooms_destroy", responses={204: None})
    def delete(self, request, venue_slug: str, room_slug: str):
        self.get_object(venue_slug, room_slug).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

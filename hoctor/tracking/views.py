from __future__ import annotations

import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from hoctor.venues.models import Room

from .models import Device, Fingerprint, Scan
from .serializers import (
    CaptureInputSerializer,
    DeviceSerializer,
    FingerprintSerializer,
    ScanInputSerializer,
    ScanSerializer,
)
from .services import AccessPointReading, get_predictor, get_scanner

logger = logging.getLogger(__name__)


class DeviceListView(APIView):
    serializer_class = DeviceSerializer

    @extend_schema(operation_id="devices_list", responses=DeviceSerializer(many=True))
    def get(self, request):
        return Response(DeviceSerializer(Device.objects.all().order_by("name"), many=True).data)

    @extend_schema(
        operation_id="devices_create",
        request=DeviceSerializer,
        responses={201: DeviceSerializer},
    )
    def post(self, request):
        serializer = DeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DeviceDetailView(APIView):
    serializer_class = DeviceSerializer

    def get_object(self, name: str) -> Device:
        return get_object_or_404(Device, name=name)

    @extend_schema(operation_id="devices_retrieve", responses=DeviceSerializer)
    def get(self, request, name: str):
        return Response(DeviceSerializer(self.get_object(name)).data)

    @extend_schema(
        operation_id="devices_partial_update",
        request=DeviceSerializer,
        responses=DeviceSerializer,
    )
    def patch(self, request, name: str):
        device = self.get_object(name)
        serializer = DeviceSerializer(device, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(operation_id="devices_destroy", responses={204: None})
    def delete(self, request, name: str):
        self.get_object(name).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FingerprintListView(APIView):
    serializer_class = FingerprintSerializer

    @extend_schema(
        operation_id="fingerprints_list",
        responses=FingerprintSerializer(many=True),
    )
    def get(self, request):
        queryset = (
            Fingerprint.objects.select_related("room", "room__venue", "device")
            .prefetch_related("samples")
            .order_by("-captured_at")
        )
        venue = request.query_params.get("venue")
        room = request.query_params.get("room")
        if venue:
            queryset = queryset.filter(room__venue__slug=venue)
        if room:
            queryset = queryset.filter(room__slug=room)
        return Response(FingerprintSerializer(queryset[:200], many=True).data)

    @extend_schema(
        operation_id="fingerprints_create",
        request=FingerprintSerializer,
        responses={201: FingerprintSerializer},
    )
    def post(self, request):
        serializer = FingerprintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FingerprintDetailView(APIView):
    serializer_class = FingerprintSerializer

    def get_object(self, pk: int) -> Fingerprint:
        return get_object_or_404(
            Fingerprint.objects.select_related("room", "room__venue", "device").prefetch_related(
                "samples"
            ),
            pk=pk,
        )

    @extend_schema(operation_id="fingerprints_retrieve", responses=FingerprintSerializer)
    def get(self, request, pk: int):
        return Response(FingerprintSerializer(self.get_object(pk)).data)

    @extend_schema(operation_id="fingerprints_destroy", responses={204: None})
    def delete(self, request, pk: int):
        self.get_object(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ScanListView(APIView):
    serializer_class = ScanSerializer

    @extend_schema(operation_id="scans_list", responses=ScanSerializer(many=True))
    def get(self, request):
        queryset = Scan.objects.select_related("venue", "device", "predicted_room").order_by(
            "-created_at"
        )
        venue = request.query_params.get("venue")
        device = request.query_params.get("device")
        if venue:
            queryset = queryset.filter(venue__slug=venue)
        if device:
            queryset = queryset.filter(device__name=device)
        limit = min(int(request.query_params.get("limit", 50)), 200)
        return Response(ScanSerializer(queryset[:limit], many=True).data)

    @extend_schema(
        operation_id="scans_create",
        request=ScanInputSerializer,
        responses={201: ScanSerializer, 200: ScanSerializer},
    )
    @transaction.atomic
    def post(self, request):
        input_serializer = ScanInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data
        venue = data["venue"]

        readings = self._collect_readings(data)
        device = self._resolve_device(data.get("device"))

        scan = Scan.objects.create(
            venue=venue,
            device=device,
            status=Scan.Status.PENDING,
            raw_samples=[r.to_dict() for r in readings],
        )

        try:
            result = get_predictor().predict(venue, readings)
        except Exception as exc:
            logger.exception("predictor failed for venue=%s", venue.slug)
            scan.status = Scan.Status.FAILED
            scan.error = str(exc)[:255]
            scan.save(update_fields=["status", "error", "updated_at"])
            return Response(ScanSerializer(scan).data, status=status.HTTP_502_BAD_GATEWAY)

        if not result.succeeded:
            scan.status = Scan.Status.FAILED
            scan.error = result.error or "unknown"
            scan.probabilities = result.probabilities
            scan.save(update_fields=["status", "error", "probabilities", "updated_at"])
            return Response(ScanSerializer(scan).data, status=status.HTTP_200_OK)

        scan.predicted_room = Room.objects.filter(pk=result.room_id).first()
        scan.confidence = result.confidence
        scan.probabilities = result.probabilities
        scan.status = Scan.Status.PREDICTED
        scan.save(
            update_fields=[
                "predicted_room",
                "confidence",
                "probabilities",
                "status",
                "updated_at",
            ]
        )
        if device is not None:
            device.last_seen_at = timezone.now()
            device.save(update_fields=["last_seen_at", "updated_at"])

        return Response(ScanSerializer(scan).data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _collect_readings(data) -> list[AccessPointReading]:
        if data.get("use_scanner"):
            return get_scanner().scan()
        return [
            AccessPointReading(
                ssid=s["ssid"],
                bssid=s.get("bssid", ""),
                signal=s["signal"],
                frequency=s.get("frequency"),
            )
            for s in data.get("samples", [])
        ]

    @staticmethod
    def _resolve_device(name: str | None) -> Device | None:
        if not name:
            return None
        device, _ = Device.objects.get_or_create(name=name.strip())
        return device


class ScanDetailView(APIView):
    serializer_class = ScanSerializer

    @extend_schema(operation_id="scans_retrieve", responses=ScanSerializer)
    def get(self, request, pk: int):
        scan = get_object_or_404(
            Scan.objects.select_related("venue", "device", "predicted_room"),
            pk=pk,
        )
        return Response(ScanSerializer(scan).data)


class CaptureView(APIView):
    serializer_class = CaptureInputSerializer

    @extend_schema(
        operation_id="capture_create",
        request=CaptureInputSerializer,
        responses={201: FingerprintSerializer},
    )
    @transaction.atomic
    def post(self, request):
        serializer = CaptureInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        room = get_object_or_404(
            Room.objects.select_related("venue"),
            venue__slug=data["venue"],
            slug=data["room"],
        )

        readings = (
            get_scanner().scan()
            if data.get("use_scanner")
            else [
                AccessPointReading(
                    ssid=s["ssid"],
                    bssid=s.get("bssid", ""),
                    signal=s["signal"],
                    frequency=s.get("frequency"),
                )
                for s in data.get("samples", [])
            ]
        )
        if not readings:
            return Response(
                {"detail": "Scan returned no access points."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        device = None
        if data.get("device"):
            device, _ = Device.objects.get_or_create(name=data["device"].strip())

        fingerprint = Fingerprint.objects.create(
            room=room,
            device=device,
            captured_at=timezone.now(),
            notes=data.get("notes", "")[:255],
        )
        from .models import AccessPointSample

        AccessPointSample.objects.bulk_create(
            [
                AccessPointSample(
                    fingerprint=fingerprint,
                    ssid=r.ssid,
                    bssid=r.bssid,
                    signal=r.signal,
                    frequency=r.frequency,
                )
                for r in readings
            ]
        )
        return Response(FingerprintSerializer(fingerprint).data, status=status.HTTP_201_CREATED)


class RoomStatsView(APIView):
    @extend_schema(
        operation_id="rooms_stats",
        responses=inline_serializer(
            name="RoomStats",
            fields={
                "venue": serializers.CharField(),
                "room": serializers.CharField(),
                "fingerprint_count": serializers.IntegerField(),
                "last_captured_at": serializers.DateTimeField(allow_null=True),
            },
        ),
    )
    def get(self, request, venue_slug: str, room_slug: str):
        room = get_object_or_404(
            Room.objects.select_related("venue"),
            venue__slug=venue_slug,
            slug=room_slug,
        )
        last = (
            Fingerprint.objects.filter(room=room)
            .order_by("-captured_at")
            .values_list("captured_at", flat=True)
            .first()
        )
        return Response(
            {
                "venue": room.venue.slug,
                "room": room.slug,
                "fingerprint_count": Fingerprint.objects.filter(room=room).count(),
                "last_captured_at": last,
            }
        )


class HealthView(APIView):
    permission_classes = ()
    authentication_classes = ()

    @extend_schema(
        operation_id="health_check",
        responses=inline_serializer(
            name="HealthResponse",
            fields={
                "status": serializers.CharField(),
                "time": serializers.DateTimeField(),
            },
        ),
    )
    def get(self, request):
        return Response({"status": "ok", "time": timezone.now().isoformat()})

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import joblib
import numpy as np
from django.conf import settings
from sklearn.ensemble import RandomForestClassifier

from hoctor.venues.models import Room, Venue

from .scanner import AccessPointReading

if TYPE_CHECKING:
    from hoctor.tracking.models import Fingerprint

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PredictionResult:
    room_id: int | None
    confidence: float | None
    probabilities: dict[str, float]
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.room_id is not None and self.error is None


@dataclass(slots=True)
class _TrainedModel:
    classifier: RandomForestClassifier
    feature_keys: list[str]
    room_ids: list[int]


class RoomPredictor:
    _instance: RoomPredictor | None = None
    _instance_lock = threading.Lock()

    def __init__(self, model_dir: Path | None = None) -> None:
        self._model_dir = Path(model_dir or settings.HOCTOR["MODEL_DIR"])
        self._model_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[int, _TrainedModel] = {}
        self._lock = threading.RLock()

    @classmethod
    def instance(cls) -> RoomPredictor:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        with cls._instance_lock:
            cls._instance = None

    def predict(self, venue: Venue, readings: list[AccessPointReading]) -> PredictionResult:
        if not readings:
            return PredictionResult(None, None, {}, error="empty_scan")

        model = self._get_or_train(venue)
        if model is None:
            return PredictionResult(None, None, {}, error="insufficient_training_data")

        features = self._vectorize(readings, model.feature_keys)
        probas = model.classifier.predict_proba(features.reshape(1, -1))[0]
        order = np.argsort(probas)[::-1]
        best_idx = int(order[0])
        best_room_id = int(model.classifier.classes_[best_idx])
        confidence = float(probas[best_idx])

        id_to_name = {
            r.pk: r.name for r in Room.objects.filter(pk__in=model.classifier.classes_.tolist())
        }
        probabilities = {
            id_to_name.get(
                int(model.classifier.classes_[i]), str(model.classifier.classes_[i])
            ): float(probas[i])
            for i in order
        }
        return PredictionResult(
            room_id=best_room_id,
            confidence=confidence,
            probabilities=probabilities,
        )

    def invalidate(self, venue: Venue) -> None:
        with self._lock:
            self._cache.pop(venue.pk, None)
            path = self._model_path(venue)
            if path.exists():
                path.unlink()

    def _get_or_train(self, venue: Venue) -> _TrainedModel | None:
        with self._lock:
            cached = self._cache.get(venue.pk)
            if cached is not None:
                return cached

            from hoctor.tracking.models import Fingerprint

            min_samples = settings.HOCTOR["PREDICTION_MIN_SAMPLES"]
            fingerprints = list(
                Fingerprint.objects.filter(room__venue=venue)
                .select_related("room")
                .prefetch_related("samples")
            )
            distinct_rooms = {fp.room_id for fp in fingerprints}
            if len(fingerprints) < min_samples or len(distinct_rooms) < 2:
                return None

            features, labels, feature_keys = self._build_matrix(fingerprints)
            classifier = RandomForestClassifier(
                n_estimators=200,
                max_depth=None,
                random_state=42,
                n_jobs=-1,
            )
            classifier.fit(features, labels)
            trained = _TrainedModel(
                classifier=classifier,
                feature_keys=feature_keys,
                room_ids=sorted(distinct_rooms),
            )
            self._cache[venue.pk] = trained
            joblib.dump(trained, self._model_path(venue))
            logger.info(
                "trained predictor for venue=%s rooms=%d fingerprints=%d features=%d",
                venue.slug,
                len(distinct_rooms),
                len(fingerprints),
                len(feature_keys),
            )
            return trained

    def _model_path(self, venue: Venue) -> Path:
        return self._model_dir / f"venue-{venue.pk}.joblib"

    @staticmethod
    def _feature_key(sample_bssid: str, sample_ssid: str) -> str:
        return sample_bssid or f"ssid::{sample_ssid}"

    def _build_matrix(
        self, fingerprints: list[Fingerprint]
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        feature_index: dict[str, int] = {}
        rows: list[dict[str, int]] = []
        labels: list[int] = []

        for fp in fingerprints:
            row: dict[str, int] = {}
            for sample in fp.samples.all():
                key = self._feature_key(sample.bssid, sample.ssid)
                if key not in feature_index:
                    feature_index[key] = len(feature_index)
                row[key] = sample.signal
            rows.append(row)
            labels.append(fp.room_id)

        feature_keys = sorted(feature_index, key=feature_index.get)
        matrix = np.full((len(rows), len(feature_keys)), fill_value=-100, dtype=np.int16)
        for row_idx, row in enumerate(rows):
            for key, signal in row.items():
                matrix[row_idx, feature_index[key]] = signal
        return matrix, np.array(labels, dtype=np.int64), feature_keys

    def _vectorize(self, readings: list[AccessPointReading], feature_keys: list[str]) -> np.ndarray:
        lookup = {key: idx for idx, key in enumerate(feature_keys)}
        vector = np.full(len(feature_keys), fill_value=-100, dtype=np.int16)
        for reading in readings:
            key = self._feature_key(reading.bssid, reading.ssid)
            idx = lookup.get(key)
            if idx is not None:
                vector[idx] = reading.signal
        return vector


def get_predictor() -> RoomPredictor:
    return RoomPredictor.instance()

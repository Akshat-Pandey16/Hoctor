from __future__ import annotations

import logging
import threading
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import joblib
import numpy as np
from django.conf import settings
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import LeaveOneOut, cross_val_score
from sklearn.neighbors import KNeighborsClassifier

from hoctor.venues.models import Room, Venue

from .scanner import AccessPointReading

if TYPE_CHECKING:
    from hoctor.tracking.models import Fingerprint

logger = logging.getLogger(__name__)

ABSENT_OFFSET = 10
DEFAULT_ABSENT = -100


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
    classifier: object
    feature_keys: list[str]
    absent_value: int
    room_ids: list[int]
    sample_count: int


@dataclass(frozen=True, slots=True)
class VenueDiagnostics:
    venue_slug: str
    fingerprint_count: int
    room_count: int
    feature_count: int
    classifier: str
    accuracy: float | None
    per_room_counts: dict[str, int]
    notes: list[str]


def _normalize_bssid(value: str) -> str:
    return (value or "").strip().lower().replace("-", ":")


def _feature_key(bssid: str, ssid: str) -> str:
    bssid = _normalize_bssid(bssid)
    return bssid or f"ssid::{ssid.strip()}"


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

        vector = self._vectorize(readings, model.feature_keys, model.absent_value)
        clf = model.classifier
        probas = clf.predict_proba(vector.reshape(1, -1))[0]
        order = np.argsort(probas)[::-1]
        best_idx = int(order[0])
        best_room_id = int(clf.classes_[best_idx])
        confidence = float(probas[best_idx])

        id_to_name = {r.pk: r.name for r in Room.objects.filter(pk__in=clf.classes_.tolist())}
        probabilities = {
            id_to_name.get(int(clf.classes_[i]), str(clf.classes_[i])): float(probas[i])
            for i in order
        }
        return PredictionResult(
            room_id=best_room_id,
            confidence=confidence,
            probabilities=probabilities,
        )

    def diagnostics(self, venue: Venue) -> VenueDiagnostics:
        with self._lock:
            from hoctor.tracking.models import Fingerprint

            fingerprints = list(
                Fingerprint.objects.filter(room__venue=venue)
                .select_related("room")
                .prefetch_related("samples")
            )
            per_room = Counter(fp.room.name for fp in fingerprints)
            notes: list[str] = []
            classifier_name = settings.HOCTOR["CLASSIFIER"]

            if not fingerprints:
                notes.append("Capture at least one fingerprint per room to begin training.")
                return VenueDiagnostics(
                    venue_slug=venue.slug,
                    fingerprint_count=0,
                    room_count=0,
                    feature_count=0,
                    classifier=classifier_name,
                    accuracy=None,
                    per_room_counts={},
                    notes=notes,
                )

            distinct_rooms = {fp.room_id for fp in fingerprints}
            min_samples = settings.HOCTOR["PREDICTION_MIN_SAMPLES"]
            if len(distinct_rooms) < 2:
                notes.append("Need fingerprints in at least 2 rooms before the model can train.")
            if len(fingerprints) < min_samples:
                notes.append(
                    f"Only {len(fingerprints)} fingerprints total — need at least {min_samples}."
                )
            thin_rooms = [name for name, c in per_room.items() if c < 5]
            if thin_rooms:
                notes.append(
                    "These rooms have fewer than 5 fingerprints — capture more for better accuracy: "
                    + ", ".join(sorted(thin_rooms))
                )

            features, labels, feature_keys, _absent = self._build_matrix(fingerprints)
            accuracy: float | None = None

            if (
                len(distinct_rooms) >= 2
                and len(fingerprints) >= min_samples
                and features.size > 0
                and min(per_room.values()) >= 2
            ):
                clf = self._build_classifier(features.shape[0])
                try:
                    scores = cross_val_score(clf, features, labels, cv=LeaveOneOut())
                    accuracy = float(scores.mean())
                except Exception as exc:
                    logger.warning("LOOCV failed for venue=%s: %s", venue.slug, exc)
                    notes.append("Could not compute cross-validated accuracy.")
            else:
                notes.append("Need at least 2 fingerprints per room for cross-validated accuracy.")

            if accuracy is not None and accuracy < 0.6:
                notes.append(
                    "Accuracy is low. Try: 10–20 fingerprints per room, captured from multiple "
                    "positions and at different times so the model sees natural signal variance."
                )

            return VenueDiagnostics(
                venue_slug=venue.slug,
                fingerprint_count=len(fingerprints),
                room_count=len(distinct_rooms),
                feature_count=len(feature_keys),
                classifier=classifier_name,
                accuracy=accuracy,
                per_room_counts=dict(per_room),
                notes=notes,
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

            features, labels, feature_keys, absent_value = self._build_matrix(fingerprints)
            if features.size == 0:
                return None
            classifier = self._build_classifier(features.shape[0])
            classifier.fit(features, labels)
            trained = _TrainedModel(
                classifier=classifier,
                feature_keys=feature_keys,
                absent_value=absent_value,
                room_ids=sorted(distinct_rooms),
                sample_count=len(fingerprints),
            )
            self._cache[venue.pk] = trained
            joblib.dump(trained, self._model_path(venue))
            logger.info(
                "trained predictor venue=%s clf=%s rooms=%d fp=%d features=%d",
                venue.slug,
                settings.HOCTOR["CLASSIFIER"],
                len(distinct_rooms),
                len(fingerprints),
                len(feature_keys),
            )
            return trained

    def _build_classifier(self, n_samples: int):
        kind = settings.HOCTOR["CLASSIFIER"]
        if kind == "knn":
            k = max(1, min(settings.HOCTOR["KNN_NEIGHBORS"], n_samples))
            return KNeighborsClassifier(
                n_neighbors=k, weights="distance", metric="euclidean", n_jobs=-1
            )
        if kind in {"rf", "random_forest", "randomforest"}:
            return RandomForestClassifier(
                n_estimators=300,
                max_depth=None,
                min_samples_leaf=1,
                random_state=42,
                n_jobs=-1,
            )
        raise ValueError(f"Unknown HOCTOR_CLASSIFIER={kind!r}")

    def _build_matrix(
        self, fingerprints: list[Fingerprint]
    ) -> tuple[np.ndarray, np.ndarray, list[str], int]:
        observations: Counter[str] = Counter()
        rows_raw: list[dict[str, int]] = []
        labels: list[int] = []
        all_signals: list[int] = []

        for fp in fingerprints:
            row: dict[str, int] = {}
            for sample in fp.samples.all():
                key = _feature_key(sample.bssid, sample.ssid)
                row[key] = sample.signal
                all_signals.append(int(sample.signal))
            for key in row:
                observations[key] += 1
            rows_raw.append(row)
            labels.append(fp.room_id)

        min_obs = max(1, settings.HOCTOR["AP_MIN_OBSERVATIONS"])
        kept = {k for k, c in observations.items() if c >= min_obs}
        if not kept:
            kept = set(observations)
        feature_keys = sorted(kept)
        absent_value = int(min(all_signals) - ABSENT_OFFSET) if all_signals else DEFAULT_ABSENT
        absent_value = max(absent_value, -120)

        index = {k: i for i, k in enumerate(feature_keys)}
        matrix = np.full((len(rows_raw), len(feature_keys)), absent_value, dtype=np.int16)
        for row_idx, row in enumerate(rows_raw):
            for key, signal in row.items():
                col = index.get(key)
                if col is not None:
                    matrix[row_idx, col] = signal
        return matrix, np.array(labels, dtype=np.int64), feature_keys, absent_value

    def _vectorize(
        self, readings: list[AccessPointReading], feature_keys: list[str], absent_value: int
    ) -> np.ndarray:
        lookup = {key: idx for idx, key in enumerate(feature_keys)}
        vector = np.full(len(feature_keys), absent_value, dtype=np.int16)
        for reading in readings:
            key = _feature_key(reading.bssid, reading.ssid)
            idx = lookup.get(key)
            if idx is not None:
                vector[idx] = reading.signal
        return vector


def get_predictor() -> RoomPredictor:
    return RoomPredictor.instance()

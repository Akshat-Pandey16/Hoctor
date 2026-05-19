from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from hoctor.tracking.services.predictor import RoomPredictor


@pytest.fixture(autouse=True)
def _reset_predictor_singleton():
    RoomPredictor.reset()
    yield
    RoomPredictor.reset()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()

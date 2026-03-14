"""Replay VCR cassette for fear_greed — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "fear_greed" / "mocks"


def test_fear_greed_market_data_cassette() -> None:
    """Replay VCR cassette for fear_greed — verifies schema shape without live network."""
    cassette_path = CASSETTE_DIR / "fng_latest.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.alternative.me/fng/?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert "data" in data and len(data["data"]) > 0


def test_fear_greed_reading_fields() -> None:
    """Value and classification fields are present in the first reading."""
    cassette_path = CASSETTE_DIR / "fng_latest.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.alternative.me/fng/?limit=1")
        data = response.json()
        reading = data["data"][0]
        assert "value" in reading
        assert "value_classification" in reading
        assert "timestamp" in reading

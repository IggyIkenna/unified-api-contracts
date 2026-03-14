"""Replay VCR cassette for fred — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "fred" / "mocks"


def test_fred_market_data_cassette() -> None:
    """Replay VCR cassette for fred — verifies schema shape without live network."""
    cassette_path = CASSETTE_DIR / "series_observations_dgs10.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id": "DGS10",
                "api_key": "abcdefghijklmnop",
                "file_type": "json",
                "limit": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert "observations" in data


def test_fred_observation_fields() -> None:
    """Observation entries have date and value fields."""
    cassette_path = CASSETTE_DIR / "series_observations_dgs10.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id": "DGS10",
                "api_key": "abcdefghijklmnop",
                "file_type": "json",
                "limit": 1,
            },
        )
        data = response.json()
        assert len(data["observations"]) > 0
        obs = data["observations"][0]
        assert "date" in obs
        assert "value" in obs

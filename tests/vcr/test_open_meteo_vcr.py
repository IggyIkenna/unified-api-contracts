"""Replay VCR cassette for open_meteo — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "open_meteo" / "mocks"


def test_open_meteo_market_data_cassette() -> None:
    """Replay VCR cassette for open_meteo — verifies schema shape without live network."""
    cassette_path = CASSETTE_DIR / "forecast_current_weather.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": 51.5, "longitude": -0.12, "current_weather": "true"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert "current_weather" in data


@pytest.mark.parametrize("key", ["temperature", "windspeed", "winddirection", "weathercode"])
def test_open_meteo_current_weather_fields(key: str) -> None:
    """Each expected field is present in the current_weather block."""
    cassette_path = CASSETTE_DIR / "forecast_current_weather.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": 51.5, "longitude": -0.12, "current_weather": "true"},
        )
        data = response.json()
        assert key in data["current_weather"], f"Missing field: {key}"

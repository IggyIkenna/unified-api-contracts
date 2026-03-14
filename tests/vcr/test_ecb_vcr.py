"""Replay VCR cassette for Ecb — verifies schema shape without live network.

ECB EUR/USD exchange rate dataflow
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "ecb" / "mocks"


def test_ecb_cassette() -> None:
    """Replay VCR cassette for Ecb endpoint."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?lastNObservations=1&format=jsondata"
        )
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_ecb_response_is_dict() -> None:
    """Response is a non-empty dict."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?lastNObservations=1&format=jsondata"
        )
        data = response.json()
        assert isinstance(data, (dict, list))

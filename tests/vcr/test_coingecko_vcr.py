"""Replay VCR cassette for Coingecko — verifies schema shape without live network.

CoinGecko coins/markets; response is list
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "coingecko" / "mocks"


def test_coingecko_cassette() -> None:
    """Replay VCR cassette for Coingecko endpoint."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_coingecko_response_structure() -> None:
    """Response is a non-empty list."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin")
        data = response.json()
        assert isinstance(data, list) and len(data) > 0

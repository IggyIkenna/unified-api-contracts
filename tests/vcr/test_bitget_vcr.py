"""Replay VCR cassette for Bitget — verifies schema shape without live network.

Bitget BTCUSDT spot ticker
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "bitget" / "mocks"


def test_bitget_cassette() -> None:
    """Replay VCR cassette for Bitget endpoint."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.bitget.com/api/v2/spot/market/tickers?symbol=BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_bitget_response_structure() -> None:
    """Response dict contains 'data' key."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.bitget.com/api/v2/spot/market/tickers?symbol=BTCUSDT")
        data = response.json()
        assert isinstance(data, dict)
        assert "data" in data

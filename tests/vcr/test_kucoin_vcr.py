"""Replay VCR cassette for Kucoin — verifies schema shape without live network.

KuCoin level1 orderbook
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "kucoin" / "mocks"


def test_kucoin_cassette() -> None:
    """Replay VCR cassette for Kucoin endpoint."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=BTC-USDT")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_kucoin_response_structure() -> None:
    """Response dict contains 'data' key."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=BTC-USDT")
        data = response.json()
        assert isinstance(data, dict)
        assert "data" in data

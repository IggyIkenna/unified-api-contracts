"""Replay VCR cassette for Huobi — verifies schema shape without live network.

Huobi merged market detail
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "huobi" / "mocks"


def test_huobi_cassette() -> None:
    """Replay VCR cassette for Huobi endpoint."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.huobi.pro/market/detail/merged?symbol=btcusdt")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_huobi_response_structure() -> None:
    """Response dict contains 'tick' key."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.huobi.pro/market/detail/merged?symbol=btcusdt")
        data = response.json()
        assert isinstance(data, dict)
        assert "tick" in data

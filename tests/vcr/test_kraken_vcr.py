"""Replay VCR cassette for Kraken — verifies schema shape without live network.

Kraken Ticker; result dict has pair keys
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "kraken" / "mocks"


def test_kraken_cassette() -> None:
    """Replay VCR cassette for Kraken endpoint."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_kraken_response_structure() -> None:
    """Response dict contains 'result' key."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD")
        data = response.json()
        assert isinstance(data, dict)
        assert "result" in data

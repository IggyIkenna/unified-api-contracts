"""Replay VCR cassette for Bitfinex — verifies schema shape without live network.

Bitfinex tBTCUSD ticker array
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent
    / "unified_api_contracts"
    / "unified_api_contracts_external"
    / "bitfinex"
    / "mocks"
)


def test_bitfinex_cassette() -> None:
    """Replay VCR cassette for Bitfinex endpoint."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api-pub.bitfinex.com/v2/ticker/tBTCUSD")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_bitfinex_response_structure() -> None:
    """Response is a non-empty list."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api-pub.bitfinex.com/v2/ticker/tBTCUSD")
        data = response.json()
        assert isinstance(data, list) and len(data) > 0

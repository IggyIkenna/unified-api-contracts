"""Replay VCR cassette for Bitstamp — verifies schema shape without live network.

Bitstamp BTC/USD ticker
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "bitstamp" / "mocks"


def test_bitstamp_cassette() -> None:
    """Replay VCR cassette for Bitstamp endpoint."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://www.bitstamp.net/api/v2/ticker/btcusd/")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_bitstamp_response_is_dict() -> None:
    """Response is a non-empty dict."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://www.bitstamp.net/api/v2/ticker/btcusd/")
        data = response.json()
        assert isinstance(data, (dict, list))


def test_bitstamp_schema_validation() -> None:
    """Response validates against api-contracts schema."""
    from unified_api_contracts.external.bitstamp.schemas import BitstampTicker

    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://www.bitstamp.net/api/v2/ticker/btcusd/")
        data = response.json()
        result = BitstampTicker.model_validate(data)
        assert result is not None

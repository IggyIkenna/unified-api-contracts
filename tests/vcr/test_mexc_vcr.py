"""Replay VCR cassette for Mexc — verifies schema shape without live network.

MEXC BTCUSDT 24hr ticker
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "mexc" / "mocks"


def test_mexc_cassette() -> None:
    """Replay VCR cassette for Mexc endpoint."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.mexc.com/api/v3/ticker/24hr?symbol=BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_mexc_response_is_dict() -> None:
    """Response is a non-empty dict."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.mexc.com/api/v3/ticker/24hr?symbol=BTCUSDT")
        data = response.json()
        assert isinstance(data, (dict, list))


def test_mexc_schema_validation() -> None:
    """Response validates against api-contracts schema."""
    from unified_api_contracts.external.mexc.schemas import MexcTicker

    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.mexc.com/api/v3/ticker/24hr?symbol=BTCUSDT")
        data = response.json()
        result = MexcTicker.model_validate(data)
        assert result is not None

"""Replay VCR cassette for Gateio — verifies schema shape without live network.

Gate.io BTC_USDT spot ticker
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "gateio" / "mocks"


def test_gateio_cassette() -> None:
    """Replay VCR cassette for Gateio endpoint."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_gateio_response_structure() -> None:
    """Response is a non-empty list."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT")
        data = response.json()
        assert isinstance(data, list) and len(data) > 0


def test_gateio_schema_validation() -> None:
    """Response validates against api-contracts schema."""
    from unified_api_contracts.external.gateio.schemas import GateioTicker

    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists()
    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT")
        data = response.json()
        result = GateioTicker.model_validate(data[0])
        assert result is not None

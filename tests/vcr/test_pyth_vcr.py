"""Replay VCR cassette for Pyth price feed — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "pyth" / "mocks"

# BTC/USD Pyth price feed ID
_BTC_USD_FEED_ID = "H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4GGKKG"


def test_pyth_price_update_cassette() -> None:
    """Replay VCR cassette for Pyth Hermes latest price update."""
    cassette_path = CASSETTE_DIR / "pyth_ws_price_update.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        url = f"https://hermes.pyth.network/v2/updates/price/latest?ids[]={_BTC_USD_FEED_ID}"
        response = httpx.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_pyth_price_update_fields() -> None:
    """Pyth price update contains required fields."""
    cassette_path = CASSETTE_DIR / "pyth_ws_price_update.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        url = f"https://hermes.pyth.network/v2/updates/price/latest?ids[]={_BTC_USD_FEED_ID}"
        response = httpx.get(url)
        data = response.json()
        for field in ("price_account", "price", "conf", "status"):
            assert field in data, f"Missing field: {field}"
        assert float(data["price"]) > 0

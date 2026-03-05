"""Replay VCR cassette for Binance futures ticker — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent
    / "unified_api_contracts"
    / "unified_api_contracts_external"
    / "binance"
    / "mocks"
)


def test_binance_futures_ticker_cassette() -> None:
    """Replay VCR cassette for Binance futures 24hr ticker."""
    cassette_path = CASSETTE_DIR / "ticker_24hr.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_binance_futures_ticker_fields() -> None:
    """Required ticker fields present in Binance futures 24hr response."""
    cassette_path = CASSETTE_DIR / "ticker_24hr.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT")
        data = response.json()
        for field in ("symbol", "lastPrice", "priceChange", "priceChangePercent", "volume"):
            assert field in data, f"Missing field: {field}"
        assert data["symbol"] == "BTCUSDT"
        assert float(data["lastPrice"]) > 0


def test_binance_futures_ticker_schema() -> None:
    """Binance futures ticker validates against api-contracts BinanceFuturesTicker."""
    from unified_api_contracts.binance.market_schemas import BinanceFuturesTicker

    cassette_path = CASSETTE_DIR / "ticker_24hr.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT")
        data = response.json()
        ticker = BinanceFuturesTicker.model_validate(data)
        assert ticker.symbol == "BTCUSDT"
        assert ticker.lastPrice is not None

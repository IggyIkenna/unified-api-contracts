"""Replay VCR cassette for Bybit linear ticker — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent / "unified_api_contracts" / "unified_api_contracts_external" / "bybit" / "mocks"
)


def test_bybit_linear_ticker_cassette() -> None:
    """Replay VCR cassette for Bybit linear BTCUSDT ticker."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_bybit_ticker_envelope() -> None:
    """Bybit response envelope has retCode=0 and a result list."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT")
        data = response.json()
        assert data["retCode"] == 0
        assert data["retMsg"] == "OK"
        assert "result" in data
        assert "list" in data["result"]
        assert len(data["result"]["list"]) > 0


def test_bybit_ticker_fields() -> None:
    """Required ticker fields present in Bybit response."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT")
        data = response.json()
        ticker = data["result"]["list"][0]
        for field in ("symbol", "lastPrice", "markPrice", "indexPrice", "fundingRate"):
            assert field in ticker, f"Missing field: {field}"
        assert ticker["symbol"] == "BTCUSDT"
        assert float(ticker["lastPrice"]) > 0


def test_bybit_ticker_schema() -> None:
    """Bybit ticker validates against api-contracts BybitTicker."""
    from unified_api_contracts.bybit.schemas import BybitTicker

    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT")
        data = response.json()
        raw_ticker = data["result"]["list"][0]
        ticker = BybitTicker.model_validate(raw_ticker)
        assert ticker.symbol == "BTCUSDT"

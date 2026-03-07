"""Replay VCR cassette for upbit — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent / "unified_api_contracts" / "unified_api_contracts_external" / "upbit" / "mocks"
)


def _make_vcr() -> VCR:
    """Strip Content-Encoding so pre-decoded cassette bodies are not double-decompressed."""

    def _strip_encoding(response: dict) -> dict:  # type: ignore[type-arg]
        response["headers"].pop("Content-Encoding", None)
        response["headers"].pop("content-encoding", None)
        return response

    return VCR(before_record_response=_strip_encoding)


def test_upbit_market_data_cassette() -> None:
    """Replay VCR cassette for upbit — verifies schema shape without live network."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with _make_vcr().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC")
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert isinstance(data, list) and "trade_price" in data[0]


def test_upbit_ticker_fields() -> None:
    """Ticker has OHLCV and market identifier fields."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with _make_vcr().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC")
        data = response.json()
        ticker = data[0]
        for field in (
            "market",
            "trade_price",
            "opening_price",
            "high_price",
            "low_price",
            "change",
        ):
            assert field in ticker, f"Missing field: {field}"

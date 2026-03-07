"""Replay VCR cassette for OKX swap ticker — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent / "unified_api_contracts" / "unified_api_contracts_external" / "okx" / "mocks"
)


def _make_vcr() -> VCR:
    """Strip Content-Encoding so pre-decoded cassette bodies are not double-decompressed."""

    def _strip_encoding(response: dict) -> dict:  # type: ignore[type-arg]
        response["headers"].pop("Content-Encoding", None)
        response["headers"].pop("content-encoding", None)
        return response

    return VCR(before_record_response=_strip_encoding)


def test_okx_swap_ticker_cassette() -> None:
    """Replay VCR cassette for OKX BTC-USDT-SWAP ticker."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with _make_vcr().use_cassette(str(cassette_path)):
        response = httpx.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_okx_ticker_envelope() -> None:
    """OKX response envelope has code='0' and a data list."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with _make_vcr().use_cassette(str(cassette_path)):
        response = httpx.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP")
        data = response.json()
        assert data["code"] == "0"
        assert isinstance(data["data"], list) and len(data["data"]) > 0


def test_okx_ticker_fields() -> None:
    """Required ticker fields present in OKX response."""
    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with _make_vcr().use_cassette(str(cassette_path)):
        response = httpx.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP")
        data = response.json()
        ticker = data["data"][0]
        for field in (
            "instId",
            "instType",
            "last",
            "askPx",
            "bidPx",
            "open24h",
            "high24h",
            "low24h",
        ):
            assert field in ticker, f"Missing field: {field}"
        assert ticker["instId"] == "BTC-USDT-SWAP"
        assert float(ticker["last"]) > 0


def test_okx_ticker_schema() -> None:
    """OKX ticker validates against api-contracts OKXTicker."""
    from unified_api_contracts.okx.schemas import OKXTicker

    cassette_path = CASSETTE_DIR / "ticker.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with _make_vcr().use_cassette(str(cassette_path)):
        response = httpx.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP")
        data = response.json()
        raw_ticker = data["data"][0]
        ticker = OKXTicker.model_validate(raw_ticker)
        assert ticker.instId == "BTC-USDT-SWAP"

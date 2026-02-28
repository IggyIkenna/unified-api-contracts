"""Replay VCR cassette for yahoo_finance — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent / "api_contracts" / "api_contracts_external" / "yahoo_finance" / "mocks"
)


def test_yahoo_finance_market_data_cassette() -> None:
    """Replay VCR cassette for yahoo_finance — verifies schema shape without live network."""
    cassette_path = CASSETTE_DIR / "chart_aapl_1d.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/AAPL",
            params={"interval": "1d", "range": "1d"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert data["chart"]["result"] is not None


def test_yahoo_finance_ohlcv_fields() -> None:
    """OHLCV quote fields are present in the chart result."""
    cassette_path = CASSETTE_DIR / "chart_aapl_1d.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/AAPL",
            params={"interval": "1d", "range": "1d"},
        )
        data = response.json()
        quote = data["chart"]["result"][0]["indicators"]["quote"][0]
        for field in ("open", "high", "low", "close", "volume"):
            assert field in quote, f"Missing OHLCV field: {field}"

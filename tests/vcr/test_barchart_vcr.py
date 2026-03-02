"""Replay VCR cassette for barchart — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent
    / "unified_api_contracts"
    / "unified_api_contracts_external"
    / "barchart"
    / "mocks"
)


def test_barchart_market_data_cassette() -> None:
    """Replay VCR cassette for barchart — verifies schema shape without live network."""
    cassette_path = CASSETTE_DIR / "get_quote_es1.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://ondemand.websol.barchart.com/getQuote.json",
            params={"apikey": "MOCK_KEY", "symbols": "ES,1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert data["status"]["code"] == 200


def test_barchart_quote_fields() -> None:
    """Quote result has expected price fields."""
    cassette_path = CASSETTE_DIR / "get_quote_es1.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://ondemand.websol.barchart.com/getQuote.json",
            params={"apikey": "MOCK_KEY", "symbols": "ES,1"},
        )
        data = response.json()
        assert len(data["results"]) > 0
        quote = data["results"][0]
        for field in ("symbol", "lastPrice", "netChange", "volume"):
            assert field in quote, f"Missing field: {field}"

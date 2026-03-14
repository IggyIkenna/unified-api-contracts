"""Replay VCR cassette for polymarket — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "polymarket" / "mocks"


def test_polymarket_market_data_cassette() -> None:
    """Replay VCR cassette for polymarket — verifies schema shape without live network."""
    cassette_path = CASSETTE_DIR / "clob_markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://clob.polymarket.com/markets",
            params={"next_cursor": "", "limit": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert "data" in data and isinstance(data["data"], list)


def test_polymarket_market_fields() -> None:
    """Market entry has condition_id, tokens, and active flag."""
    cassette_path = CASSETTE_DIR / "clob_markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://clob.polymarket.com/markets",
            params={"next_cursor": "", "limit": 2},
        )
        data = response.json()
        market = data["data"][0]
        for field in ("condition_id", "description", "active", "tokens"):
            assert field in market, f"Missing field: {field}"
        assert isinstance(market["tokens"], list) and len(market["tokens"]) == 2

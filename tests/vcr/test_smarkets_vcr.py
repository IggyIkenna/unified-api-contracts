"""Replay VCR cassette for Smarkets markets — verifies schema shape without live network.

Cassette recorded with auth token (filtered). Auth not required for replay.
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent
    / "unified_api_contracts"
    / "unified_api_contracts_external"
    / "smarkets"
    / "mocks"
)


def test_smarkets_markets_cassette() -> None:
    """Replay VCR cassette for Smarkets /v3/markets/ endpoint."""
    cassette_path = CASSETTE_DIR / "smarkets_get_markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.smarkets.com/v3/markets/")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_smarkets_markets_list() -> None:
    """Smarkets response contains a markets list."""
    cassette_path = CASSETTE_DIR / "smarkets_get_markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.smarkets.com/v3/markets/")
        data = response.json()
        assert "markets" in data
        assert isinstance(data["markets"], list) and len(data["markets"]) > 0


def test_smarkets_market_fields() -> None:
    """Each Smarkets market has required fields."""
    cassette_path = CASSETTE_DIR / "smarkets_get_markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.smarkets.com/v3/markets/")
        data = response.json()
        market = data["markets"][0]
        for field in ("id", "name", "eventId", "marketType", "state"):
            assert field in market, f"Missing field: {field}"


def test_smarkets_market_schema() -> None:
    """Smarkets market validates against api-contracts SmarketsMarket."""
    from unified_api_contracts.unified_api_contracts_external.smarkets.schemas import SmarketsMarket

    cassette_path = CASSETTE_DIR / "smarkets_get_markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.smarkets.com/v3/markets/")
        data = response.json()
        market = SmarketsMarket.model_validate(data["markets"][0])
        assert market.id is not None
        assert market.state is not None

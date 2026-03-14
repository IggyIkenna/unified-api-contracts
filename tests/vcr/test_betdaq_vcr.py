"""Replay VCR cassette for Betdaq markets — verifies schema shape without live network.

Cassette recorded with auth token (filtered). Auth not required for replay.
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "betdaq" / "mocks"


def test_betdaq_markets_cassette() -> None:
    """Replay VCR cassette for Betdaq GetTopLevelEvents endpoint."""
    cassette_path = CASSETTE_DIR / "betdaq_get_markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.betdaq.com/v2.0/market/GetTopLevelEvents")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_betdaq_markets_list() -> None:
    """Betdaq response contains a markets list."""
    cassette_path = CASSETTE_DIR / "betdaq_get_markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.betdaq.com/v2.0/market/GetTopLevelEvents")
        data = response.json()
        assert "markets" in data
        assert isinstance(data["markets"], list) and len(data["markets"]) > 0


def test_betdaq_market_fields() -> None:
    """Each Betdaq market has required fields."""
    cassette_path = CASSETTE_DIR / "betdaq_get_markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.betdaq.com/v2.0/market/GetTopLevelEvents")
        data = response.json()
        market = data["markets"][0]
        for field in ("marketId", "marketName", "eventId", "marketType", "status"):
            assert field in market, f"Missing field: {field}"


def test_betdaq_market_schema() -> None:
    """Betdaq market validates against api-contracts BetdaqMarket."""
    from unified_api_contracts.external.betdaq.schemas import BetdaqMarket

    cassette_path = CASSETTE_DIR / "betdaq_get_markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.betdaq.com/v2.0/market/GetTopLevelEvents")
        data = response.json()
        market = BetdaqMarket.model_validate(data["markets"][0])
        assert market.marketId is not None

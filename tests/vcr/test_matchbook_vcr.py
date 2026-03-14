"""Replay VCR cassette for Matchbook markets — verifies schema shape without live network.

Cassette recorded with auth token (filtered). Auth not required for replay.
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "matchbook" / "mocks"


def test_matchbook_markets_cassette() -> None:
    """Replay VCR cassette for Matchbook events/markets endpoint."""
    cassette_path = CASSETTE_DIR / "matchbook_get_markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.matchbook.com/edge/rest/events")
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_matchbook_markets_structure() -> None:
    """Matchbook response contains a markets list."""
    cassette_path = CASSETTE_DIR / "matchbook_get_markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.matchbook.com/edge/rest/events")
        data = response.json()
        assert "markets" in data
        assert isinstance(data["markets"], list) and len(data["markets"]) > 0


def test_matchbook_market_fields() -> None:
    """Each Matchbook market has required fields."""
    cassette_path = CASSETTE_DIR / "matchbook_get_markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.matchbook.com/edge/rest/events")
        data = response.json()
        market = data["markets"][0]
        for field in ("id", "eventId", "name", "marketType", "status", "runners"):
            assert field in market, f"Missing field: {field}"


def test_matchbook_market_schema() -> None:
    """Matchbook market validates against api-contracts MatchbookMarket."""
    from unified_api_contracts.external.matchbook.schemas import MatchbookMarket

    cassette_path = CASSETTE_DIR / "matchbook_get_markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://api.matchbook.com/edge/rest/events")
        data = response.json()
        market = MatchbookMarket.model_validate(data["markets"][0])
        assert market.id is not None
        assert market.marketType is not None

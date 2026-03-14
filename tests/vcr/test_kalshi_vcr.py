"""Replay VCR cassettes for kalshi — verifies schema shape without live network."""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

from unified_api_contracts.external.kalshi.schemas import (
    KalshiMarket,
    KalshiOrderBook,
)

CASSETTE_DIR = Path(__file__).parent.parent.parent / "unified_api_contracts" / "external" / "kalshi" / "mocks"


def test_kalshi_markets_cassette() -> None:
    """Replay VCR cassette for kalshi markets list — verifies schema shape without live network."""
    cassette_path = CASSETTE_DIR / "markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://trading-api.kalshi.com/trade-api/v2/markets",
            params={"limit": "1", "status": "open"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "markets" in data and isinstance(data["markets"], list)
        assert len(data["markets"]) > 0


def test_kalshi_market_schema_valid() -> None:
    """KalshiMarket schema validates first market entry from cassette."""
    cassette_path = CASSETTE_DIR / "markets.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://trading-api.kalshi.com/trade-api/v2/markets",
            params={"limit": "1", "status": "open"},
        )
        data = response.json()
        market = data["markets"][0]
        for field in ("ticker", "event_ticker", "status", "yes_bid_dollars", "yes_ask_dollars"):
            assert field in market, f"Missing required field: {field}"
        validated = KalshiMarket.model_validate(market)
        assert validated.ticker is not None
        assert validated.status == "active"


def test_kalshi_orderbook_cassette() -> None:
    """Replay VCR cassette for kalshi order book — verifies schema shape without live network."""
    cassette_path = CASSETTE_DIR / "orderbook.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://trading-api.kalshi.com/trade-api/v2/markets/KXHIGHNY-24JAN01-T60/orderbook")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "yes_dollars" in data and "no_dollars" in data


def test_kalshi_orderbook_schema_valid() -> None:
    """KalshiOrderBook schema validates order book entry from cassette."""
    cassette_path = CASSETTE_DIR / "orderbook.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.get("https://trading-api.kalshi.com/trade-api/v2/markets/KXHIGHNY-24JAN01-T60/orderbook")
        data = response.json()
        validated = KalshiOrderBook.model_validate(data)
        assert validated.ticker == "KXHIGHNY-24JAN01-T60"
        assert validated.yes_dollars is not None and len(validated.yes_dollars) > 0
        assert validated.no_dollars is not None and len(validated.no_dollars) > 0
        # Each level is (price_str, size_str)
        first_level = validated.yes_dollars[0]
        assert len(first_level) == 2

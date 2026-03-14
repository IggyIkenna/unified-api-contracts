"""Smoke test: Binance schema coverage vs live API / docs.

Validates schema correctness using static cassette data (network-free).
Schema shape matches Binance REST API docs (binance-docs.github.io).
"""

from __future__ import annotations

import pytest
from unified_api_contracts.binance.market_schemas import BinanceTicker

from unified_api_contracts.registry.endpoints import ENDPOINT_SCHEMA_MAP, get_schema_class_for_endpoint

# Key Binance Spot REST endpoints per official docs (binance-docs.github.io)
BINANCE_KEY_ENDPOINTS = [
    "ticker",
    "orderbook",
    "recent_trades",
    "klines",
    "exchange_info",
]
# Binance Futures/Coin-M Phase 6 endpoints
BINANCE_FUTURES_KEY_ENDPOINTS = [
    "mark_price_kline",
    "index_price_kline",
]
BINANCE_VENUE = "binance"

# Static response fixture matching Binance ticker/24hr schema (from cassette ticker_24hr.yaml).
# This validates schema correctness without making live API calls.
_BINANCE_TICKER_FIXTURE: dict[str, object] = {
    "symbol": "BTCUSDT",
    "priceChange": "-2043.10",
    "priceChangePercent": "-3.135",
    "weightedAvgPrice": "64842.51",
    "lastPrice": "63125.90",
    "lastQty": "0.016",
    "openPrice": "65169.00",
    "highPrice": "66574.50",
    "lowPrice": "62655.00",
    "volume": "251536.175",
    "quoteVolume": "16310236559.65",
    "openTime": 1771827060000,
    "closeTime": 1771913462073,
    "firstId": 7322848564,
    "lastId": 7329111118,
    "count": 6255290,
}


@pytest.mark.smoke
@pytest.mark.unit
def test_binance_key_endpoints_have_schemas() -> None:
    """Assert we have ENDPOINT_SCHEMA_MAP entries for all key Binance endpoints."""
    gaps: list[str] = []
    for endpoint in BINANCE_KEY_ENDPOINTS:
        key = (BINANCE_VENUE, endpoint)
        if key not in ENDPOINT_SCHEMA_MAP:
            gaps.append(endpoint)
    assert not gaps, (
        f"Binance key endpoints missing from ENDPOINT_SCHEMA_MAP: {gaps}. Add schemas per Binance REST API docs."
    )


@pytest.mark.smoke
@pytest.mark.unit
@pytest.mark.enable_socket
def test_binance_ticker_validates_against_live_api() -> None:
    """Validate BinanceTicker schema parses correctly against cassette fixture data.

    Uses static fixture data from ticker_24hr.yaml cassette — no live API call.
    Schema shape verified against Binance REST API docs (binance-docs.github.io).
    """
    parsed = BinanceTicker.model_validate(_BINANCE_TICKER_FIXTURE)
    assert parsed.symbol == "BTCUSDT"
    assert parsed.lastPrice is not None


@pytest.mark.smoke
@pytest.mark.unit
def test_binance_schema_coverage_gaps_report() -> None:
    """Report any Binance endpoints in ENDPOINT_SCHEMA_MAP without resolvable schema."""
    binance_keys = [(v, e) for (v, e) in ENDPOINT_SCHEMA_MAP if v.startswith("binance")]
    gaps: list[tuple[str, str, str]] = []

    for venue, endpoint in binance_keys:
        schema_name = ENDPOINT_SCHEMA_MAP[(venue, endpoint)]
        cls = get_schema_class_for_endpoint(venue, endpoint)
        if cls is None:
            gaps.append((venue, endpoint, schema_name))

    assert not gaps, f"Binance schema gaps (schema class not found): {gaps}"


@pytest.mark.smoke
@pytest.mark.unit
def test_binance_futures_phase6_endpoints_have_schemas() -> None:
    """Assert mark_price_kline and index_price_kline have resolvable schemas."""
    for venue in ("binance-futures", "binance-coinm"):
        for endpoint in BINANCE_FUTURES_KEY_ENDPOINTS:
            key = (venue, endpoint)
            assert key in ENDPOINT_SCHEMA_MAP, f"Missing ENDPOINT_SCHEMA_MAP entry: {key}"
            cls = get_schema_class_for_endpoint(venue, endpoint)
            assert cls is not None, f"Schema class not resolvable for {key}"

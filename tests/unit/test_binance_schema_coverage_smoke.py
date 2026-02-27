"""Smoke test: Binance schema coverage vs live API / docs.

Fetches Binance public API (equivalent to Context7 docs verification) and asserts
we have schemas for key endpoints. Reports gaps as test failures.
"""

from __future__ import annotations

import pytest
import requests

from api_contracts.binance.schemas import BinanceTicker
from api_contracts.endpoints import ENDPOINT_SCHEMA_MAP, get_schema_class_for_endpoint

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
BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/24hr"
REQUEST_TIMEOUT = 10


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
def test_binance_ticker_validates_against_live_api() -> None:
    """Fetch Binance ticker from live API and validate with BinanceTicker schema.

    Uses live API (equivalent to Context7 docs verification). Skips if network
    unavailable (e.g. CI without outbound).
    """
    try:
        resp = requests.get(
            f"{BINANCE_TICKER_URL}?symbol=BTCUSDT",
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except (requests.RequestException, OSError) as e:
        pytest.skip(f"Binance API unreachable: {e}")

    data = resp.json()
    parsed = BinanceTicker.model_validate(data)
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

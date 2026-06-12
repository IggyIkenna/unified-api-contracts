"""Tests for the broker → routed-venue declaration (F38, Phase 6A)."""

from __future__ import annotations

from unified_api_contracts.internal.architecture_v2 import (
    BROKER_ROUTES,
    BrokerKind,
    BrokerRoute,
    VenueCategoryV2,
    broker_for_venue,
    is_broker,
    routed_venue_ids,
)


def test_ibkr_is_a_declared_broker_routing_to_tradfi_exchanges() -> None:
    assert "ibkr" in BROKER_ROUTES
    route = BROKER_ROUTES["ibkr"]
    assert isinstance(route, BrokerRoute)
    assert route.broker_id == "ibkr"
    assert route.kind == BrokerKind.ORDER_ROUTER
    # CME/ICE/CBOE are the operator-named venues; all six are the
    # VENUE_TO_EXCHANGE keys (ibkr_tradfi.py:38-46).
    assert set(route.routed_venue_ids) == {"cme", "ice", "cboe", "nasdaq", "nyse", "fx"}
    assert route.venue_categories == (VenueCategoryV2.TRADFI,)
    assert "ibkr_tradfi.py" in route.source_of_truth


def test_routed_venue_ids_are_sorted_for_determinism() -> None:
    route = BROKER_ROUTES["ibkr"]
    assert list(route.routed_venue_ids) == sorted(route.routed_venue_ids)


def test_broker_for_venue_resolves_routed_venues_case_insensitively() -> None:
    assert broker_for_venue("cme") == "ibkr"
    assert broker_for_venue("CME") == "ibkr"
    assert broker_for_venue("ice") == "ibkr"
    assert broker_for_venue("cboe") == "ibkr"
    # A non-routed venue (real market, not broker-routed) returns None.
    assert broker_for_venue("hyperliquid") is None
    assert broker_for_venue("binance") is None


def test_is_broker_flags_only_declared_broker_ids() -> None:
    # The broker id itself is a broker.
    assert is_broker("ibkr") is True
    assert is_broker("IBKR") is True
    # A routed VENUE is NOT a broker — it is the actual exchange.
    assert is_broker("cme") is False
    assert is_broker("hyperliquid") is False


def test_routed_venue_ids_aggregate_is_sorted_and_deduplicated() -> None:
    venues = routed_venue_ids()
    assert venues == tuple(sorted(set(venues)))
    assert "cme" in venues and "ice" in venues and "cboe" in venues


def test_broker_route_is_frozen() -> None:
    route = BROKER_ROUTES["ibkr"]
    import pytest

    with pytest.raises((TypeError, ValueError)):
        route.broker_id = "tradestation"  # type: ignore[misc]

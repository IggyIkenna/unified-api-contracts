"""Tests for ``get_perp_venues()`` helper.

Resolves the ``PerpVenue`` ambiguity called out in
``defi_recursive_borrow_archetypes_2026_05_10.md`` findings (line 549) by
exposing a typed set derived from ``VENUE_CAPABILITIES`` rather than a
separate enum.
"""

from __future__ import annotations

from unified_api_contracts.registry import get_perp_venues
from unified_api_contracts.registry.venue_constants import (
    ASTER,
    BINANCE_FUTURES,
    BINANCE_SPOT,
    BYBIT_FUTURES,
    DERIBIT,
    HYPERLIQUID,
    KALSHI_PERP,
    OKX_FUTURES,
    POLYMARKET_PERP,
    VENUE_CAPABILITIES,
    VenueCapability,
)


class TestGetPerpVenues:
    """``get_perp_venues()`` returns the canonical PERP_TRADE-capable set."""

    def test_returns_frozenset(self) -> None:
        result = get_perp_venues()
        assert isinstance(result, frozenset)

    def test_includes_all_known_perp_venues(self) -> None:
        perp_venues = get_perp_venues()
        for expected in (
            BINANCE_FUTURES,
            BYBIT_FUTURES,
            OKX_FUTURES,
            DERIBIT,
            HYPERLIQUID,
            ASTER,
            KALSHI_PERP,
            POLYMARKET_PERP,
        ):
            assert expected in perp_venues, f"{expected!r} missing from get_perp_venues()"

    def test_excludes_spot_only_venues(self) -> None:
        perp_venues = get_perp_venues()
        assert BINANCE_SPOT not in perp_venues

    def test_matches_venue_capabilities_filter(self) -> None:
        """Helper output equals the inline filter expression callers would write."""
        expected = frozenset(v for v, caps in VENUE_CAPABILITIES.items() if VenueCapability.PERP_TRADE in caps)
        assert get_perp_venues() == expected

    def test_is_idempotent(self) -> None:
        assert get_perp_venues() == get_perp_venues()

    def test_nonempty(self) -> None:
        assert len(get_perp_venues()) > 0

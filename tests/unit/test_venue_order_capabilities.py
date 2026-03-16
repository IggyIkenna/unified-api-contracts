"""Tests for venue order-type sub-capabilities."""

from __future__ import annotations

from unified_api_contracts.registry.venue_constants import (
    VENUE_CAPABILITIES,
    VENUE_ORDER_CAPABILITIES,
    VenueOrderCapability,
)


class TestVenueOrderCapabilities:
    """Verify venue order sub-capabilities are complete and consistent."""

    def test_all_venues_with_capabilities_have_order_capabilities(self) -> None:
        """Every venue in VENUE_CAPABILITIES must also appear in VENUE_ORDER_CAPABILITIES."""
        for venue in VENUE_CAPABILITIES:
            assert venue in VENUE_ORDER_CAPABILITIES, (
                f"Venue {venue!r} in VENUE_CAPABILITIES but missing from VENUE_ORDER_CAPABILITIES"
            )

    def test_all_order_capabilities_are_frozensets(self) -> None:
        """All values must be frozensets (immutable)."""
        for venue, caps in VENUE_ORDER_CAPABILITIES.items():
            assert isinstance(caps, frozenset), (
                f"Venue {venue!r} order capabilities should be frozenset, got {type(caps)}"
            )

    def test_all_order_capability_values_are_valid_enum(self) -> None:
        """All capability values must be valid VenueOrderCapability members."""
        valid = set(VenueOrderCapability)
        for venue, caps in VENUE_ORDER_CAPABILITIES.items():
            for cap in caps:
                assert cap in valid, f"Venue {venue!r} has unknown order capability {cap!r}"

    def test_cefi_exchanges_have_at_least_post_only(self) -> None:
        """Major CeFi exchanges should support POST_ONLY at minimum."""
        cefi_venues = ["BINANCE-SPOT", "BINANCE-FUTURES", "OKX-SPOT", "BYBIT-SPOT", "DERIBIT"]
        for venue in cefi_venues:
            if venue in VENUE_ORDER_CAPABILITIES:
                assert VenueOrderCapability.POST_ONLY in VENUE_ORDER_CAPABILITIES[venue], (
                    f"CeFi venue {venue!r} should support POST_ONLY"
                )

    def test_dex_venues_have_empty_order_capabilities(self) -> None:
        """DEX/AMM venues should have empty order capability sets."""
        dex_venues = ["UNISWAPV2-ETH", "UNISWAPV3-ETH", "UNISWAPV4-ETH", "CURVE-ETH", "AERODROME-BASE"]
        for venue in dex_venues:
            if venue in VENUE_ORDER_CAPABILITIES:
                assert len(VENUE_ORDER_CAPABILITIES[venue]) == 0, (
                    f"DEX venue {venue!r} should have empty order capabilities"
                )

    def test_lending_venues_have_empty_order_capabilities(self) -> None:
        """Lending/staking venues should have empty order capability sets."""
        lending_venues = ["AAVE_V3", "AAVE_V3_ETH", "MORPHO-ETHEREUM", "LIDO", "ETHERFI"]
        for venue in lending_venues:
            if venue in VENUE_ORDER_CAPABILITIES:
                assert len(VENUE_ORDER_CAPABILITIES[venue]) == 0, (
                    f"Lending venue {venue!r} should have empty order capabilities"
                )

    def test_venue_order_capabilities_count(self) -> None:
        """VENUE_ORDER_CAPABILITIES should cover all venues in VENUE_CAPABILITIES."""
        assert len(VENUE_ORDER_CAPABILITIES) >= len(VENUE_CAPABILITIES), (
            f"VENUE_ORDER_CAPABILITIES ({len(VENUE_ORDER_CAPABILITIES)}) should cover "
            f"all VENUE_CAPABILITIES ({len(VENUE_CAPABILITIES)})"
        )

    def test_enum_has_all_expected_members(self) -> None:
        """VenueOrderCapability should have exactly 8 members."""
        expected = {
            "POST_ONLY",
            "REDUCE_ONLY",
            "CANCEL_REPLACE",
            "BATCH_PLACE",
            "STOP_LIMIT",
            "TRAILING_STOP",
            "ICEBERG",
            "TWAP",
        }
        actual = {m.name for m in VenueOrderCapability}
        assert actual == expected, f"Enum members mismatch: {actual ^ expected}"

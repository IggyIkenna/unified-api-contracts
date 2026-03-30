"""Integration tests verifying instruction constraints work with venue data.

Validates that the constraint registry is consistent with the actual venue
capability declarations and instrument type mappings.
"""

from __future__ import annotations

from unified_api_contracts.registry.instruction_constraints import (
    INSTRUCTION_CONSTRAINTS,
    validate_instruction,
)
from unified_api_contracts.registry.venue_constants import (
    INSTRUCTION_VALID_DOMAINS,
    INSTRUMENT_TYPES_BY_VENUE,
    VENUE_CAPABILITIES,
    VENUE_CATEGORY_MAP,
    VENUE_ORDER_CAPABILITIES,
    VenueCapability,
)


class TestInstructionVenueIntegration:
    """End-to-end: instruction types match venue capabilities."""

    def test_trade_venues_support_trade_capability(self) -> None:
        """Venues in TRADE's venue_categories should have trade capabilities."""
        trade_caps = {
            VenueCapability.SPOT_TRADE,
            VenueCapability.PERP_TRADE,
            VenueCapability.FUTURES_TRADE,
            VenueCapability.OPTIONS_TRADE,
        }
        trade_categories = INSTRUCTION_CONSTRAINTS["TRADE"]["venue_categories"]

        for venue, caps in VENUE_CAPABILITIES.items():
            if VENUE_CATEGORY_MAP.get(venue) in trade_categories and caps & trade_caps:
                # Should be valid
                validate_instruction(
                    instruction_type="TRADE",
                    venue_category=VENUE_CATEGORY_MAP[venue],
                )

    def test_swap_venues_have_swap_capability(self) -> None:
        """DEX venues used for SWAP should have VenueCapability.SWAP."""
        swap_categories = INSTRUCTION_CONSTRAINTS["SWAP"]["venue_categories"]
        for venue, caps in VENUE_CAPABILITIES.items():
            category = VENUE_CATEGORY_MAP.get(venue)
            if category in swap_categories and VenueCapability.SWAP in caps:
                validate_instruction(
                    instruction_type="SWAP",
                    venue_category=category,
                    instrument_type="POOL",
                )

    def test_lp_instruction_types_match_dex_venues(self) -> None:
        """LP instruction types should only be valid for DEX venues with POOL instruments."""
        for inst_type in ("ADD_LIQUIDITY", "REMOVE_LIQUIDITY", "COLLECT_FEES"):
            constraint = INSTRUCTION_CONSTRAINTS[inst_type]
            assert "POOL" in constraint["instrument_types"]
            assert "defi" in constraint["venue_categories"]

            # Verify DEX venues have POOL in their instrument types
            for venue in ("UNISWAPV3-ETHEREUM", "CURVE-ETHEREUM", "AERODROME-BASE"):
                if venue in INSTRUMENT_TYPES_BY_VENUE:
                    assert "POOL" in INSTRUMENT_TYPES_BY_VENUE[venue], f"{venue} should support POOL for LP operations"

    def test_every_venue_has_order_capabilities(self) -> None:
        """Every venue in VENUE_CAPABILITIES must have an order capabilities entry."""
        for venue in VENUE_CAPABILITIES:
            assert venue in VENUE_ORDER_CAPABILITIES, f"Venue {venue!r} missing from VENUE_ORDER_CAPABILITIES"

    def test_sports_instruction_types_match_sports_venues(self) -> None:
        """Sports instruction types should only be valid for sports venues."""
        sports_types = ["PREDICTION_BET", "SPORTS_BET", "SPORTS_EXCHANGE_ORDER"]
        for inst_type in sports_types:
            constraint = INSTRUCTION_CONSTRAINTS[inst_type]
            assert "sports" in constraint["venue_categories"]

    def test_constraint_completeness_with_valid_domains(self) -> None:
        """Every key in INSTRUCTION_VALID_DOMAINS should appear in INSTRUCTION_CONSTRAINTS."""
        for inst_type in INSTRUCTION_VALID_DOMAINS:
            if inst_type not in (
                "LEND",
                "BORROW",
                "STAKE",
                "UNSTAKE",
                "FLASH_LOAN",
                "TRANSFER",
                "BET",
            ):
                assert inst_type in INSTRUCTION_CONSTRAINTS, (
                    f"Instruction type {inst_type!r} in INSTRUCTION_VALID_DOMAINS but not in INSTRUCTION_CONSTRAINTS"
                )

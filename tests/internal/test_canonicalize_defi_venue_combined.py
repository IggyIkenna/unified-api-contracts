"""Tests for canonicalize_defi_venue_combined — glued→canonical DeFi venue mapping.

Bug 5 (defi_coverage_capability_alignment_2026_05_22.md): instruments-service wrote
DeFi reference parquets to the glued venue path (venue=AAVEV3-ARBITRUM) while the
manifest recorded the canonical venue (AAVE_V3-ARBITRUM). The canonicalizer below is
the authoritative writer-side fix: it inserts the missing underscore that
parse_defi_venue preserves, mapping the glued combined form to the canonical combined
form using the PROTOCOL_CAPABILITIES venue_prefix set as the single source of truth.
"""

from __future__ import annotations

from unified_api_contracts.registry.capability_declarations._defi import (
    canonicalize_defi_venue_combined,
)


class TestCanonicalizeDefiVenueCombined:
    def test_aave_v3_glued_to_canonical(self) -> None:
        assert canonicalize_defi_venue_combined("AAVEV3-ARBITRUM") == "AAVE_V3-ARBITRUM"

    def test_uniswap_v3_glued_to_canonical(self) -> None:
        assert canonicalize_defi_venue_combined("UNISWAPV3-ETHEREUM") == "UNISWAP_V3-ETHEREUM"

    def test_compound_v3_glued_to_canonical(self) -> None:
        assert canonicalize_defi_venue_combined("COMPOUNDV3-BASE") == "COMPOUND_V3-BASE"

    def test_already_canonical_passthrough(self) -> None:
        # Canonical input must round-trip unchanged (idempotent).
        assert canonicalize_defi_venue_combined("AAVE_V3-ARBITRUM") == "AAVE_V3-ARBITRUM"

    def test_unknown_protocol_passthrough(self) -> None:
        # Unknown protocol with a KNOWN chain → surface honestly, never guess.
        assert canonicalize_defi_venue_combined("FAKEPROTO-ETHEREUM") == "FAKEPROTO-ETHEREUM"

    def test_non_defi_no_known_chain_passthrough(self) -> None:
        # CeFi venue: no hyphen → passthrough.
        assert canonicalize_defi_venue_combined("BINANCE") == "BINANCE"
        # Hyphenated but suffix is not a known chain → passthrough.
        assert canonicalize_defi_venue_combined("BINANCE-SPOT") == "BINANCE-SPOT"

    def test_glued_prefix_venue_stays_glued(self) -> None:
        # VELODROMEV2 / TRADER_JOEV2 are themselves glued in PROTOCOL_CAPABILITIES,
        # so glued IS canonical for them — the round-trip is a no-op.
        assert canonicalize_defi_venue_combined("VELODROMEV2-OPTIMISM") == "VELODROMEV2-OPTIMISM"

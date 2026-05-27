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

    def test_pancakeswap_v3_zksync_glued_to_canonical(self) -> None:
        # ZKSYNC is now in KNOWN_CHAINS (B5.9), so PANCAKESWAPV3-ZKSYNC parses and
        # canonicalises the protocol PANCAKESWAPV3 → PANCAKESWAP_V3.
        assert canonicalize_defi_venue_combined("PANCAKESWAPV3-ZKSYNC") == "PANCAKESWAP_V3-ZKSYNC"

    def test_lighter_zksync_parses_protocol_unchanged(self) -> None:
        # ZKSYNC is a KNOWN chain, so the chain suffix now PARSES (no longer an
        # unknown-chain passthrough). LIGHTER is a perp venue NOT in
        # PROTOCOL_CAPABILITIES → unknown-protocol passthrough → unchanged. The
        # observable result is LIGHTER-ZKSYNC either way, but the code path is now
        # known-chain/unknown-protocol rather than unknown-chain.
        assert canonicalize_defi_venue_combined("LIGHTER-ZKSYNC") == "LIGHTER-ZKSYNC"

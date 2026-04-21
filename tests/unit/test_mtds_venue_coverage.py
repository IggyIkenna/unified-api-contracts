"""Tests for MTDS per-venue expected-data_types coverage — Phase 6b.

SSOT: unified-trading-pm/codex/02-data/mtds-data-source-coverage-matrix.md

Guards the MTDS aggregator's denominator inputs:
 - CEFI venue list is deduplicated (HYPERLIQUID was duplicated pre-fix).
 - Suffixed venue keys (OKX-SPOT / OKX-FUTURES / OKX-SWAP / COINBASE-SPOT)
   return non-empty expected data_types. Aggregator cannot compute
   expected shards if any CEFI venue returns []; this test locks the fix.
"""

from __future__ import annotations

from collections import Counter

from unified_api_contracts import (
    VenueMapping,
    get_expected_data_types_for_venue,
)


class TestAllCefiVenuesDeduplicated:
    """VenueMapping.all_cefi_venues must not return duplicates."""

    def test_no_duplicates(self) -> None:
        vm = VenueMapping()
        venues = vm.all_cefi_venues
        counts = Counter(venues)
        dupes = {v: c for v, c in counts.items() if c > 1}
        assert not dupes, f"VenueMapping.all_cefi_venues returned duplicates: {dupes}"

    def test_expected_set_size(self) -> None:
        vm = VenueMapping()
        # 8 Tardis venues (BINANCE-SPOT/FUTURES, DERIBIT, BYBIT, OKX-SPOT/FUTURES/SWAP,
        # COINBASE-SPOT, UPBIT, HYPERLIQUID) + 2 CEFI on-chain CLOB (HYPERLIQUID, ASTER)
        # deduped to 11 unique.
        assert len(vm.all_cefi_venues) == 11, (
            f"expected 11 unique CEFI venues, got {len(vm.all_cefi_venues)}: {sorted(vm.all_cefi_venues)}"
        )

    def test_includes_all_suffixed_variants(self) -> None:
        vm = VenueMapping()
        venues = set(vm.all_cefi_venues)
        assert "OKX-SPOT" in venues
        assert "OKX-FUTURES" in venues
        assert "OKX-SWAP" in venues
        assert "COINBASE-SPOT" in venues
        assert "HYPERLIQUID" in venues
        assert "ASTER" in venues


class TestMtdsVenueExpectedDataTypes:
    """Every CEFI venue must have at least one expected data_type."""

    def test_no_cefi_venue_empty(self) -> None:
        vm = VenueMapping()
        empty = [v for v in set(vm.all_cefi_venues) if not get_expected_data_types_for_venue(v)]
        assert not empty, (
            f"CEFI venues with empty get_expected_data_types_for_venue(): {empty}. "
            "Aggregator cannot compute expected shards for these."
        )

    def test_no_tradfi_venue_empty(self) -> None:
        vm = VenueMapping()
        empty = [v for v in set(vm.all_databento_venues) if not get_expected_data_types_for_venue(v)]
        assert not empty, f"TRADFI venues with empty expected_data_types: {empty}"

    def test_suffixed_okx_variants_have_correct_scope(self) -> None:
        # OKX-SPOT: no derivatives
        spot = set(get_expected_data_types_for_venue("OKX-SPOT"))
        assert "trades" in spot
        assert "book_snapshot_5" in spot
        assert "derivative_ticker" not in spot
        assert "liquidations" not in spot

        # OKX-FUTURES: has derivative_ticker, no liquidations (linear futures)
        fut = set(get_expected_data_types_for_venue("OKX-FUTURES"))
        assert "derivative_ticker" in fut
        assert "trades" in fut
        assert "liquidations" not in fut

        # OKX-SWAP: full perp including liquidations
        swap = set(get_expected_data_types_for_venue("OKX-SWAP"))
        assert "derivative_ticker" in swap
        assert "liquidations" in swap
        assert "trades" in swap

    def test_coinbase_spot_has_data_types(self) -> None:
        dts = set(get_expected_data_types_for_venue("COINBASE-SPOT"))
        assert "trades" in dts
        assert "book_snapshot_5" in dts

    def test_prediction_venues_declare_trades(self) -> None:
        # prediction venues use canonical 'trades' (legacy prediction_trades
        # retired 2026-04-19). book_snapshot_5 intentionally NOT declared.
        for v in ("POLYMARKET", "KALSHI"):
            dts = set(get_expected_data_types_for_venue(v))
            assert "trades" in dts, f"{v} missing 'trades'"


class TestNormalizeDefiVenue:
    """normalize_defi_venue must resolve legacy manifest names to canonical PROTOCOL-CHAIN form."""

    def test_legacy_aave_v3_maps_to_canonical(self) -> None:
        vm = VenueMapping()
        assert vm.normalize_defi_venue("AAVE_V3") == "AAVEV3-ETHEREUM"

    def test_legacy_uniswap_variants(self) -> None:
        vm = VenueMapping()
        assert vm.normalize_defi_venue("UNISWAP_V2") == "UNISWAPV2-ETHEREUM"
        assert vm.normalize_defi_venue("UNISWAP_V3") == "UNISWAPV3-ETHEREUM"
        assert vm.normalize_defi_venue("UNISWAP_V4") == "UNISWAPV4-ETHEREUM"

    def test_legacy_single_token_protocols(self) -> None:
        vm = VenueMapping()
        for raw, expected in (
            ("CURVE", "CURVE-ETHEREUM"),
            ("BALANCER", "BALANCER-ETHEREUM"),
            ("MORPHO", "MORPHO-ETHEREUM"),
            ("FLUID", "FLUID-ETHEREUM"),
            ("LIDO", "LIDO-ETHEREUM"),
            ("ETHERFI", "ETHERFI-ETHEREUM"),
            ("ETHENA", "ETHENA-ETHEREUM"),
        ):
            assert vm.normalize_defi_venue(raw) == expected, f"{raw} → expected {expected}"

    def test_canonical_form_is_idempotent(self) -> None:
        vm = VenueMapping()
        for canonical in vm.all_defi_venues:
            assert vm.normalize_defi_venue(canonical) == canonical

    def test_unknown_venue_returned_unchanged(self) -> None:
        vm = VenueMapping()
        assert vm.normalize_defi_venue("TOTALLY_UNKNOWN_PROTOCOL") == "TOTALLY_UNKNOWN_PROTOCOL"
        assert not vm.is_defi_venue("TOTALLY_UNKNOWN_PROTOCOL")

    def test_chain_override_for_multi_chain_expansion(self) -> None:
        vm = VenueMapping()
        # When adapters start writing AAVE_V3 on Arbitrum, passing chain=ARBITRUM
        # should resolve to AAVEV3-ARBITRUM (not registered yet — returned for
        # the caller to decide whether to accept).
        assert vm.normalize_defi_venue("AAVE_V3", chain="ARBITRUM") == "AAVEV3-ARBITRUM"
        assert vm.normalize_defi_venue("UNISWAP_V3", chain="BASE") == "UNISWAPV3-BASE"

    def test_is_defi_venue_accepts_legacy(self) -> None:
        vm = VenueMapping()
        assert vm.is_defi_venue("AAVE_V3")
        assert vm.is_defi_venue("UNISWAP_V3")
        assert vm.is_defi_venue("AAVEV3-ETHEREUM")
        assert not vm.is_defi_venue("BINANCE-SPOT")


class TestMultiChainDefiExpansion:
    """Phase 7 — observed (protocol, chain) combos across DEFI sub-dim buckets.

    Multi-chain venues (AAVE_V3 on Polygon/Arbitrum/Base/Avalanche/BSC/Linea/Scroll/zkSync,
    Compound V3 on Arbitrum/Base/Optimism/Scroll, Uniswap V3 on Arbitrum/Base/Optimism/Polygon,
    etc.) were phantom-gaps in the pre-2026-04-20 registry. Every observed non-Ethereum
    (protocol, chain) combo now has a canonical ``PROTOCOL-CHAIN`` entry in
    ``all_defi_venues`` + a ``normalize_defi_venue(raw, chain=...)`` aliases entry.
    """

    def test_registry_size_matches_observed_scope(self) -> None:
        vm = VenueMapping()
        assert len(vm.all_defi_venues) >= 50, (
            f"expected >=50 canonical (protocol, chain) combos, got {len(vm.all_defi_venues)}"
        )

    def test_every_observed_combo_resolves(self) -> None:
        """Every (protocol, chain) pair seen in the live DEFI buckets resolves to a registered venue."""
        observed: list[tuple[str, str]] = [
            # AAVE V3 wide chain coverage
            ("AAVE_V3", "ETHEREUM"),
            ("AAVE_V3", "POLYGON"),
            ("AAVE_V3", "ARBITRUM"),
            ("AAVE_V3", "BASE"),
            ("AAVE_V3", "OPTIMISM"),
            ("AAVE_V3", "AVALANCHE"),
            ("AAVE_V3", "BSC"),
            ("AAVE_V3", "LINEA"),
            ("AAVE_V3", "SCROLL"),
            ("AAVE_V3", "ZKSYNC"),
            # Compound V3
            ("COMPOUND_V3", "ETHEREUM"),
            ("COMPOUND_V3", "ARBITRUM"),
            ("COMPOUND_V3", "BASE"),
            ("COMPOUND_V3", "OPTIMISM"),
            ("COMPOUND_V3", "SCROLL"),
            # Uniswap V3
            ("UNISWAP_V3", "ETHEREUM"),
            ("UNISWAP_V3", "ARBITRUM"),
            ("UNISWAP_V3", "BASE"),
            ("UNISWAP_V3", "OPTIMISM"),
            ("UNISWAP_V3", "POLYGON"),
            # Balancer
            ("BALANCER", "ETHEREUM"),
            ("BALANCER", "POLYGON"),
            ("BALANCER", "ARBITRUM"),
            ("BALANCER", "OPTIMISM"),
            ("BALANCER", "AVALANCHE"),
            ("BALANCER", "BASE"),
            # Curve
            ("CURVE", "ETHEREUM"),
            ("CURVE", "AVALANCHE"),
            ("CURVE", "OPTIMISM"),
            # DEX (chain-exclusive)
            ("AERODROME_V3", "BASE"),
            ("CAMELOT_V3", "ARBITRUM"),
            ("VELODROME_V2", "OPTIMISM"),
            ("TRADER_JOE_V2", "AVALANCHE"),
            # PancakeSwap V3
            ("PANCAKESWAP_V3", "ETHEREUM"),
            ("PANCAKESWAP_V3", "ARBITRUM"),
            ("PANCAKESWAP_V3", "BASE"),
            ("PANCAKESWAP_V3", "BSC"),
            ("PANCAKESWAP_V3", "ZKSYNC"),
            # SushiSwap V3
            ("SUSHISWAP_V3", "ETHEREUM"),
            ("SUSHISWAP_V3", "AVALANCHE"),
            ("SUSHISWAP_V3", "BASE"),
            # GMX
            ("GMX", "ARBITRUM"),
            ("GMX", "AVALANCHE"),
            # Solana
            ("KAMINO", "SOLANA"),
            ("MARINADE", "SOLANA"),
            ("ORCA", "SOLANA"),
            ("RAYDIUM", "SOLANA"),
            # Spark, Morpho expansion
            ("SPARK", "ETHEREUM"),
            ("MORPHO", "ETHEREUM"),
            ("MORPHO", "BASE"),
            ("FLUID", "ETHEREUM"),
        ]
        vm = VenueMapping()
        missing: list[tuple[str, str, str]] = []
        for protocol, chain in observed:
            canonical = vm.normalize_defi_venue(protocol, chain=chain)
            if canonical not in vm.all_defi_venues:
                missing.append((protocol, chain, canonical))
        assert not missing, (
            "Observed (protocol, chain) combos did not resolve to a registered canonical "
            f"venue — add these to all_defi_venues: {missing}"
        )

    def test_non_ethereum_chain_override(self) -> None:
        vm = VenueMapping()
        # Chain override flips the canonical suffix
        assert vm.normalize_defi_venue("AAVE_V3", chain="POLYGON") == "AAVEV3-POLYGON"
        assert vm.normalize_defi_venue("AAVE_V3", chain="ARBITRUM") == "AAVEV3-ARBITRUM"
        assert vm.normalize_defi_venue("COMPOUND_V3", chain="SCROLL") == "COMPOUNDV3-SCROLL"

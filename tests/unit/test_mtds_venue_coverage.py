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


# ---------------------------------------------------------------------------
# Phase 8 — per-instrument Tier-3 sentinel denominator tests
# ---------------------------------------------------------------------------
# SSOT: unified-trading-pm/plans/active/mtds_per_instrument_sentinels_2026_04_21.plan.md
# Registry: unified_api_contracts.registry.market_data_categories
# Accessor: get_expected_instruments_for_venue(venue, data_type, *, as_of_date, instruments_provider, cap)


from unified_api_contracts import (  # noqa: E402
    get_expected_instruments_for_venue,
    is_per_instrument_shard_data_type,
)


class TestIsPerInstrumentShardDataType:
    """Canonical frozenset of per-instrument shard data_types."""

    def test_cefi_per_instrument_dts(self) -> None:
        for dt in ("trades", "book_snapshot_5", "derivative_ticker", "options_chain", "futures_chain"):
            assert is_per_instrument_shard_data_type(dt), f"{dt} should be per-instrument"

    def test_venue_level_dts(self) -> None:
        for dt in ("liquidations", "ohlcv_1m", "ohlcv_15m", "ohlcv_24h", "tbbo", "gas_fees", "perp_funding", "odds"):
            assert not is_per_instrument_shard_data_type(dt), f"{dt} should be venue-level"

    def test_defi_per_instrument_dts(self) -> None:
        for dt in ("dex_swaps", "dex_pools", "lending_indices", "oracle_prices", "lst_rates", "rewards", "risk_params"):
            assert is_per_instrument_shard_data_type(dt), f"{dt} should be per-instrument"

    def test_prediction_per_instrument_dts(self) -> None:
        for dt in ("prediction_trades", "prediction_book_snapshot", "prediction_market_metadata"):
            assert is_per_instrument_shard_data_type(dt), f"{dt} should be per-instrument"


class TestGetExpectedInstrumentsForVenueMvpSeed:
    """Default MVP seed path (no instruments_provider injected)."""

    def test_binance_spot_trades_uses_spot_mvp_seed(self) -> None:
        result = get_expected_instruments_for_venue("BINANCE-SPOT", "trades")
        assert result, "BINANCE-SPOT trades must seed non-empty"
        assert "BTC-USDT" in result and "ETH-USDT" in result
        assert len(result) == 21, f"SPOT MVP seed should hold 21 assets, got {len(result)}"

    def test_binance_futures_derivative_ticker_uses_perp_seed(self) -> None:
        result = get_expected_instruments_for_venue("BINANCE-FUTURES", "derivative_ticker")
        assert result, "BINANCE-FUTURES derivative_ticker must seed non-empty"
        assert "BTC-PERP" in result and "ETH-PERP" in result

    def test_deribit_options_chain_uses_underlyings(self) -> None:
        result = get_expected_instruments_for_venue("DERIBIT", "options_chain")
        assert result == ["BTC", "ETH"]

    def test_venue_level_dt_returns_empty(self) -> None:
        # `liquidations` is venue-level → caller should fall back to Tier-2
        assert get_expected_instruments_for_venue("BINANCE-FUTURES", "liquidations") == []
        assert get_expected_instruments_for_venue("CME", "ohlcv_1m") == []
        assert get_expected_instruments_for_venue("CME", "tbbo") == []

    def test_unknown_venue_returns_empty(self) -> None:
        assert get_expected_instruments_for_venue("FAKEVENUE-X", "trades") == []

    def test_defi_dt_returns_empty_mvp_seed(self) -> None:
        # WAVE 8G will seed DeFi top-N pools. MVP returns empty and the
        # aggregator degrades to Tier-2.
        assert get_expected_instruments_for_venue("UNISWAPV3-ETHEREUM", "dex_swaps") == []
        assert get_expected_instruments_for_venue("AAVEV3-ETHEREUM", "lending_indices") == []


class TestGetExpectedInstrumentsForVenueInjectedProvider:
    """Runtime provider injection path — used by MTDS orchestrator."""

    def test_provider_overrides_seed(self) -> None:
        def provider(_venue: str, _data_type: str) -> list[str]:
            return ["CUSTOM-1", "CUSTOM-2", "CUSTOM-3"]

        result = get_expected_instruments_for_venue("BINANCE-SPOT", "trades", instruments_provider=provider)
        assert result == ["CUSTOM-1", "CUSTOM-2", "CUSTOM-3"]

    def test_cap_trims_provider_result(self) -> None:
        def provider(_venue: str, _data_type: str) -> list[str]:
            return [f"INST-{i}" for i in range(200)]

        result = get_expected_instruments_for_venue(
            "BINANCE-FUTURES", "derivative_ticker", instruments_provider=provider, cap=50
        )
        assert len(result) == 50
        assert result[0] == "INST-0"
        assert result[-1] == "INST-49"

    def test_cap_of_zero_returns_empty(self) -> None:
        def provider(_venue: str, _data_type: str) -> list[str]:
            return ["A", "B", "C"]

        result = get_expected_instruments_for_venue("BINANCE-SPOT", "trades", instruments_provider=provider, cap=0)
        assert result == []

    def test_cap_larger_than_list_returns_full_list(self) -> None:
        def provider(_venue: str, _data_type: str) -> list[str]:
            return ["A", "B"]

        result = get_expected_instruments_for_venue("BINANCE-SPOT", "trades", instruments_provider=provider, cap=500)
        assert result == ["A", "B"]

    def test_provider_returning_none_degrades_gracefully(self) -> None:
        def provider(_venue: str, _data_type: str) -> list[str] | None:
            return None

        result = get_expected_instruments_for_venue("BINANCE-SPOT", "trades", instruments_provider=provider)
        assert result == []

    def test_venue_level_dt_still_empty_even_with_provider(self) -> None:
        # Provider must not be consulted for venue-level dts — returning a
        # non-empty list here should still be ignored.
        def provider(_venue: str, _data_type: str) -> list[str]:
            return ["SHOULD-NOT-APPEAR"]

        result = get_expected_instruments_for_venue("BINANCE-FUTURES", "liquidations", instruments_provider=provider)
        assert result == []

    def test_mvp_seed_respects_default_cap_of_none(self) -> None:
        # No cap → full SPOT MVP list
        result = get_expected_instruments_for_venue("BINANCE-SPOT", "trades")
        assert len(result) == 21

    def test_mvp_seed_honours_cap(self) -> None:
        result = get_expected_instruments_for_venue("BINANCE-SPOT", "trades", cap=5)
        assert len(result) == 5
        assert result == [
            "BTC-USDT",
            "ETH-USDT",
            "SOL-USDT",
            "BNB-USDT",
            "XRP-USDT",
        ]

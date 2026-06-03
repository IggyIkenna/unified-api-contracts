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
        # Tier-1/2 Tardis (BINANCE-SPOT/FUTURES, DERIBIT, BYBIT, OKX-SPOT/FUTURES/SWAP,
        # COINBASE-SPOT, UPBIT) + Tier-3 (2026-05-01: BITFINEX-SPOT/FUTURES, BITGET-SPOT,
        # BITGET-FUTURES, KRAKEN-SPOT, KRAKEN-FUTURES) + on-chain CLOBs (HYPERLIQUID,
        # ASTER, PACIFICA-SOLANA, EXTENDED-STARKNET, LIGHTER-ZKSYNC). HYPERLIQUID is in
        # both Tardis-backed and CLOB sets so dedupes once. Total = 20.
        assert len(vm.all_cefi_venues) == 20, (
            f"expected 20 unique CEFI venues, got {len(vm.all_cefi_venues)}: {sorted(vm.all_cefi_venues)}"
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
        assert vm.normalize_defi_venue("AAVE_V3") == "AAVE_V3-ETHEREUM"

    def test_legacy_uniswap_variants(self) -> None:
        vm = VenueMapping()
        assert vm.normalize_defi_venue("UNISWAP_V2") == "UNISWAP_V2-ETHEREUM"
        assert vm.normalize_defi_venue("UNISWAP_V3") == "UNISWAP_V3-ETHEREUM"
        assert vm.normalize_defi_venue("UNISWAP_V4") == "UNISWAP_V4-ETHEREUM"

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
        # should resolve to AAVE_V3-ARBITRUM (not registered yet — returned for
        # the caller to decide whether to accept).
        assert vm.normalize_defi_venue("AAVE_V3", chain="ARBITRUM") == "AAVE_V3-ARBITRUM"
        assert vm.normalize_defi_venue("UNISWAP_V3", chain="BASE") == "UNISWAP_V3-BASE"

    def test_is_defi_venue_accepts_legacy(self) -> None:
        vm = VenueMapping()
        assert vm.is_defi_venue("AAVE_V3")
        assert vm.is_defi_venue("UNISWAP_V3")
        assert vm.is_defi_venue("AAVE_V3-ETHEREUM")
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
            # PANCAKESWAP_V3-ZKSYNC dropped 2026-05-06 (UAC@7cb9068) — low-quality +
            # low-volume data; 446 manifest rows purged. Do NOT re-add without
            # data-quality + liquidity validation. SSOT comment in
            # `unified_api_contracts/registry/defi_venues.py:116`.
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
        assert vm.normalize_defi_venue("AAVE_V3", chain="POLYGON") == "AAVE_V3-POLYGON"
        assert vm.normalize_defi_venue("AAVE_V3", chain="ARBITRUM") == "AAVE_V3-ARBITRUM"
        assert vm.normalize_defi_venue("COMPOUND_V3", chain="SCROLL") == "COMPOUND_V3-SCROLL"


# ---------------------------------------------------------------------------
# Phase 8 — per-instrument Tier-3 sentinel denominator tests
# ---------------------------------------------------------------------------
# SSOT: unified-trading-pm/plans/active/mtds_per_instrument_sentinels_2026_04_21.md
# Registry: unified_api_contracts.registry.market_data_categories
# Accessor: get_expected_instruments_for_venue(venue, data_type, *, as_of_date, instruments_provider, cap)


from unified_api_contracts import (
    get_expected_instruments_for_venue,
    is_per_instrument_shard_data_type,
)


class TestIsPerInstrumentShardDataType:
    """Canonical frozenset of per-instrument shard data_types."""

    def test_cefi_per_instrument_dts(self) -> None:
        for dt in ("trades", "book_snapshot_5", "derivative_ticker", "options_chain", "futures_chain"):
            assert is_per_instrument_shard_data_type(dt), f"{dt} should be per-instrument"

    def test_ohlcv_1m_is_per_instrument(self) -> None:
        # Phase 3.D.5 v2: ohlcv_1m promoted to per-instrument shard.
        # TradFiCatalogReader provides equity tickers; CeFiCatalogReader
        # provides DEX pool IDs for LIGHTER/PACIFICA.
        assert is_per_instrument_shard_data_type("ohlcv_1m")

    def test_venue_level_dts(self) -> None:
        for dt in ("liquidations", "ohlcv_15m", "ohlcv_24h", "tbbo", "gas_fees", "perp_funding", "odds"):
            assert not is_per_instrument_shard_data_type(dt), f"{dt} should be venue-level"

    def test_defi_per_instrument_dts(self) -> None:
        for dt in (
            "dex_pool_swaps",
            "dex_pool_state",
            "lending_indices",
            "oracle_prices",
            "lst_rates",
            "rewards",
            "risk_params",
        ):
            assert is_per_instrument_shard_data_type(dt), f"{dt} should be per-instrument"

    def test_retired_prediction_dts_not_per_instrument(self) -> None:
        # prediction_trades/book_snapshot/market_metadata are retired; canonical replacements
        # are 'trades', 'book_snapshot_5', and metadata fields on the instrument record.
        for dt in ("prediction_trades", "prediction_book_snapshot", "prediction_market_metadata"):
            assert not is_per_instrument_shard_data_type(dt), f"Retired type {dt} must not be per-instrument"


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

    def test_defi_dt_returns_seeded_mvp(self) -> None:
        # Wave 8G populated the DeFi seeds — top-20 UNI V3 ETH pools,
        # top-10 Aave ETH reserves.
        swaps = get_expected_instruments_for_venue("UNISWAP_V3-ETHEREUM", "dex_pool_swaps")
        assert len(swaps) == 20
        # canonical lowercase pool addresses
        for pool in swaps:
            assert pool.startswith("0x") and pool.lower() == pool
        assert len(get_expected_instruments_for_venue("AAVE_V3-ETHEREUM", "lending_indices")) == 10


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


# ---------------------------------------------------------------------------
# Wave 8G — DEFI + PREDICTION MVP seed tables
# ---------------------------------------------------------------------------
# SSOT: unified-trading-pm/codex/02-data/mtds-data-source-coverage-matrix.md § 8
# Registry: unified_api_contracts.registry.defi_prediction_instrument_seeds

from unified_api_contracts.registry.defi_prediction_instrument_seeds import (
    DEFI_MVP_SEED_INSTRUMENTS,
    PREDICTION_MVP_SEED_INSTRUMENTS,
    seed_for_venue_and_data_type,
)


class TestWave8GDefiSeeds:
    """Wave 8G DEFI seed — top-N pools / reserves / LST tokens."""

    def test_uniswapv3_ethereum_dex_pools_top20(self) -> None:
        result = get_expected_instruments_for_venue("UNISWAP_V3-ETHEREUM", "dex_pool_state")
        assert len(result) == 20
        # First 5 must match the observed 2026-04-14 TVL order.
        assert result[0] == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"  # USDC/WETH 0.05%
        assert result[1] == "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8"  # USDC/WETH 0.3%
        # All entries are lowercase 42-char ETH addresses.
        for pool in result:
            assert pool.startswith("0x") and len(pool) == 42
            assert pool.lower() == pool

    def test_uniswapv3_ethereum_dex_swaps_same_pool_set(self) -> None:
        pools = get_expected_instruments_for_venue("UNISWAP_V3-ETHEREUM", "dex_pool_state")
        swaps = get_expected_instruments_for_venue("UNISWAP_V3-ETHEREUM", "dex_pool_swaps")
        assert pools == swaps, "dex_pool_state and dex_pool_swaps share the pool universe"

    def test_aavev3_ethereum_lending_indices_top10_reserves(self) -> None:
        result = get_expected_instruments_for_venue("AAVE_V3-ETHEREUM", "lending_indices")
        assert len(result) == 10
        # Canonical liquid reserves must be present.
        for sym in ("USDC", "USDT", "DAI", "WETH", "WBTC", "AAVE", "LINK"):
            assert sym in result, f"{sym} missing from Aave top-10 seed"

    def test_aavev3_ethereum_dts_share_reserve_universe(self) -> None:
        li = get_expected_instruments_for_venue("AAVE_V3-ETHEREUM", "lending_indices")
        op = get_expected_instruments_for_venue("AAVE_V3-ETHEREUM", "oracle_prices")
        rw = get_expected_instruments_for_venue("AAVE_V3-ETHEREUM", "rewards")
        rp = get_expected_instruments_for_venue("AAVE_V3-ETHEREUM", "risk_params")
        assert li == op == rw == rp

    def test_lst_rates_per_protocol_seed(self) -> None:
        # Each LST protocol emits its own token set (rebase + wrapped).
        assert get_expected_instruments_for_venue("LIDO-ETHEREUM", "lst_rates") == ["stETH", "wstETH"]
        assert get_expected_instruments_for_venue("ETHERFI-ETHEREUM", "lst_rates") == ["eETH", "weETH"]
        assert get_expected_instruments_for_venue("ETHENA-ETHEREUM", "lst_rates") == ["USDe", "sUSDe"]

    def test_defi_venue_level_dt_still_empty(self) -> None:
        # `perp_funding` + `liquidations` + `gas_fees` stay venue-level
        # even on DEFI venues — must not trigger the seed path.
        assert get_expected_instruments_for_venue("GMX-ARBITRUM", "perp_funding") == []
        assert get_expected_instruments_for_venue("GMX-ARBITRUM", "liquidations") == []


class TestWave8GPredictionSeeds:
    """Wave 8G PREDICTION seed — top-N conditionIds."""

    def test_polymarket_trades_top10_condition_ids(self) -> None:
        result = get_expected_instruments_for_venue("POLYMARKET", "trades")
        assert len(result) == 10
        # 0x-prefixed 66-char (0x + 64 hex) conditionId hashes.
        for cid in result:
            assert cid.startswith("0x") and len(cid) == 66

    def test_kalshi_trades_empty_until_adapter_lands(self) -> None:
        # No live KALSHI bucket observed on 2026-04-20; seed is intentionally
        # empty (honest-coverage "attempted_failed" / "empty_confirmed").
        assert get_expected_instruments_for_venue("KALSHI", "trades") == []

    def test_polymarket_cap_truncates(self) -> None:
        result = get_expected_instruments_for_venue("POLYMARKET", "trades", cap=3)
        assert len(result) == 3


class TestWave8GSeedHelper:
    """Direct tests on the ``seed_for_venue_and_data_type`` helper."""

    def test_defi_map_entries(self) -> None:
        assert ("UNISWAP_V3-ETHEREUM", "dex_pool_state") in DEFI_MVP_SEED_INSTRUMENTS
        assert ("AAVE_V3-ETHEREUM", "lending_indices") in DEFI_MVP_SEED_INSTRUMENTS
        assert ("LIDO-ETHEREUM", "lst_rates") in DEFI_MVP_SEED_INSTRUMENTS

    def test_prediction_map_entries(self) -> None:
        assert ("POLYMARKET", "trades") in PREDICTION_MVP_SEED_INSTRUMENTS
        assert ("KALSHI", "trades") in PREDICTION_MVP_SEED_INSTRUMENTS

    def test_unknown_venue_dt_returns_empty_tuple(self) -> None:
        assert seed_for_venue_and_data_type("FAKE-CHAIN", "dex_pool_state") == ()
        assert seed_for_venue_and_data_type("UNISWAP_V3-ETHEREUM", "unknown_dt") == ()


class TestSeedDispatcherVenueClassification:
    """Phase 2 CeFi gap audit (2026-05-05) — confirm the seed dispatcher
    respects venue-vs-data_type compatibility and never returns expectations
    for combinations a venue physically can't serve.
    """

    def test_perp_only_venues_seed_perps_on_trades(self) -> None:
        """All -FUTURES venues are perp-dominant on Tardis (Bitfinex /
        Bitget / Kraken-derivatives publish perps under the -FUTURES
        suffix). Pre-fix they fell through to the SPOT branch and
        returned BTC-USDT seeds — the Tier-3 sentinel then expected
        spot pairs on a perp venue and every shard was a false miss.
        """
        for venue in ("OKX-FUTURES", "BITFINEX-FUTURES", "BITGET-FUTURES", "KRAKEN-FUTURES"):
            ids = get_expected_instruments_for_venue(venue, "trades")
            assert ids, f"{venue} trades must seed non-empty"
            assert "BTC-PERP" in ids, f"{venue} trades expected BTC-PERP, got {ids[:3]}"
            assert "BTC-USDT" not in ids, f"{venue} should not emit spot seeds"

    def test_spot_venues_have_empty_derivative_ticker_seed(self) -> None:
        """Spot-only venues never publish derivative_ticker. Pre-fix the
        dispatcher returned PERP seeds unconditionally, causing the
        Tier-3 sentinel to expect (e.g.) BTC-PERP rows on BINANCE-SPOT —
        rows that can never exist. Empty seed → sentinel skips Tier-3
        and degrades to Tier-2, which is correct.
        """
        for venue in (
            "BINANCE-SPOT",
            "OKX-SPOT",
            "COINBASE-SPOT",
            "UPBIT",
            "BITFINEX-SPOT",
            "BITGET-SPOT",
            "KRAKEN-SPOT",
        ):
            assert get_expected_instruments_for_venue(venue, "derivative_ticker") == [], (
                f"{venue} is spot-only; derivative_ticker must seed empty"
            )

    def test_spot_venues_keep_trades_book_seeds(self) -> None:
        """Sanity guard — the derivative_ticker fix must not regress the
        trades / book_snapshot_5 paths for spot venues."""
        for venue in ("BINANCE-SPOT", "COINBASE-SPOT", "UPBIT", "BITGET-SPOT"):
            assert get_expected_instruments_for_venue(venue, "trades"), f"{venue} trades regressed"
            assert get_expected_instruments_for_venue(venue, "book_snapshot_5"), f"{venue} book_snapshot_5 regressed"

    def test_aster_book_snapshot_5_is_empty(self) -> None:
        """ASTER's adapter only wires trades + derivative_ticker (no
        book_snapshot_5 / liquidations). Pre-fix the dispatcher emitted
        book_snapshot_5 perps for ASTER and the Tier-3 sentinel created
        14 false-miss rows per day. Capability table is the SSOT — if
        the data_type isn't declared, the seed must be empty.
        """
        # capability-declared data_types remain seeded
        assert get_expected_instruments_for_venue("ASTER", "trades")
        assert get_expected_instruments_for_venue("ASTER", "derivative_ticker")
        # not in ASTER's VENUE_DATA_TYPE_CAPABILITIES → empty
        assert get_expected_instruments_for_venue("ASTER", "book_snapshot_5") == []
        assert get_expected_instruments_for_venue("ASTER", "liquidations") == []

    def test_capability_gate_does_not_break_known_venues(self) -> None:
        """Regression guard: BINANCE-FUTURES / BYBIT / DERIBIT / OKX-SWAP
        / HYPERLIQUID all declare trades + book_snapshot_5 + derivative_
        ticker in VENUE_DATA_TYPE_CAPABILITIES, so all three should
        continue to seed perps post-fix.
        """
        for venue in ("BINANCE-FUTURES", "BYBIT", "DERIBIT", "OKX-SWAP", "HYPERLIQUID"):
            for dt in ("trades", "book_snapshot_5", "derivative_ticker"):
                ids = get_expected_instruments_for_venue(venue, dt)
                assert ids, f"{venue} {dt} regressed to empty"
                assert "BTC-PERP" in ids, f"{venue} {dt} dropped BTC-PERP"

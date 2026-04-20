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

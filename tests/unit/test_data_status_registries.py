"""Tests for the data-status registries (Phase 1).

Covers :mod:`unified_api_contracts.registry.processed_data_dependencies`
and :mod:`unified_api_contracts.registry.expected_coverage` — together
these power the four-state data-status view in deployment-ui (captured
/ missing / blocked_on_raw / out_of_scope).
"""

from __future__ import annotations

from unified_api_contracts.registry.expected_coverage import (
    EXPECTED_COVERAGE_BY_ASSET_GROUP,
    get_expected_data_types_for_venue_in_scope,
    get_expected_pairs,
    get_expected_venues_in_scope,
    is_expected,
)
from unified_api_contracts.registry.market_data_categories import (
    DATA_TYPES_BY_ASSET_GROUP,
    VENUE_DATA_TYPE_CAPABILITIES,
)
from unified_api_contracts.registry.processed_data_dependencies import (
    PROCESSED_REQUIRES_RAW,
    get_raw_source_data_types,
    is_processed_data_type,
)


class TestProcessedRequiresRaw:
    """Raw → processed dependency map (for blocked_on_raw classification)."""

    def test_arbitrage_opportunity_requires_odds(self) -> None:
        """Sports arbitrage_opportunity is purely-derived from raw odds."""
        assert is_processed_data_type("arbitrage_opportunity")
        assert get_raw_source_data_types("arbitrage_opportunity") == ["odds"]

    def test_ohlcv_higher_timeframes_accept_trades_or_passthrough_1m(self) -> None:
        """Higher-tf ohlcv shards may be derived from raw trades OR ohlcv_1m.

        TradFi Databento emits ohlcv_1m natively (passthrough); CeFi MDPS
        derives ohlcv_1m from trades. Either is a valid raw source for
        the higher timeframe shards.
        """
        for tf in ("5m", "15m", "1h", "4h", "1d", "24h"):
            key = f"ohlcv_{tf}"
            assert key in PROCESSED_REQUIRES_RAW, f"missing key: {key}"
            assert get_raw_source_data_types(key) == ["trades", "ohlcv_1m"]

    def test_ohlcv_1m_is_not_classified_as_processed(self) -> None:
        """ohlcv_1m is raw-or-derived ambiguously — both backfill and MDPS can fill.

        Classifying it as processed would penalise TradFi venues whose
        Databento feed emits ohlcv_1m natively. Treat as plain raw.
        """
        assert not is_processed_data_type("ohlcv_1m")
        assert "ohlcv_1m" not in PROCESSED_REQUIRES_RAW

    def test_book5_ohlcv_shards_are_processed_at_every_timeframe(self) -> None:
        """book5_ohlcv_*  is genuinely processed: raw is 15s book snapshots."""
        for tf in ("1m", "5m", "15m", "1h", "4h", "1d"):
            key = f"book5_ohlcv_{tf}"
            assert is_processed_data_type(key)
            assert get_raw_source_data_types(key) == ["book_snapshot_5"]

    def test_deriv_ohlcv_requires_derivative_ticker(self) -> None:
        for tf in ("1m", "5m", "15m", "1h"):
            key = f"deriv_ohlcv_{tf}"
            assert is_processed_data_type(key)
            assert get_raw_source_data_types(key) == ["derivative_ticker"]

    def test_odds_ohlcv_requires_odds(self) -> None:
        for tf in ("5m", "15m", "1h"):
            key = f"odds_ohlcv_{tf}"
            assert is_processed_data_type(key)
            assert get_raw_source_data_types(key) == ["odds"]

    def test_unknown_data_type_returns_empty_list(self) -> None:
        """Callers branch on is_processed_data_type before looking up sources."""
        assert not is_processed_data_type("not_a_data_type")
        assert get_raw_source_data_types("not_a_data_type") == []

    def test_returned_list_is_a_copy(self) -> None:
        """Mutating the returned list must not corrupt the registry."""
        sources = get_raw_source_data_types("ohlcv_5m")
        sources.append("XXX")
        assert "XXX" not in PROCESSED_REQUIRES_RAW["ohlcv_5m"]


class TestExpectedCoverageByAssetGroup:
    """Operator-intent coverage policy — denominator-scoping for data-status UI."""

    def test_all_five_asset_groups_present(self) -> None:
        assert set(EXPECTED_COVERAGE_BY_ASSET_GROUP.keys()) == {
            "cefi",
            "tradfi",
            "defi",
            "sports",
            "prediction",
        }

    def test_tradfi_excludes_us_equities_by_design(self) -> None:
        """NASDAQ + NYSE are capable but operator-omitted — render as out-of-scope."""
        tradfi = EXPECTED_COVERAGE_BY_ASSET_GROUP["tradfi"]
        assert "NASDAQ" not in tradfi
        assert "NYSE" not in tradfi
        assert "BARCHART" not in tradfi
        # And in-scope venues are present.
        assert tradfi["CME"] == ["trades", "ohlcv_1m", "tbbo"]
        assert tradfi["ICE"] == ["trades", "ohlcv_1m", "tbbo"]
        assert tradfi["CBOE"] == ["ohlcv_15m"]

    def test_sports_excludes_arbitrage_opportunity(self) -> None:
        """arbitrage_opportunity is MDPS-derived; no venue emits it."""
        for venue, dts in EXPECTED_COVERAGE_BY_ASSET_GROUP["sports"].items():
            assert "arbitrage_opportunity" not in dts, (
                f"{venue} should not declare arbitrage_opportunity (it's processed)"
            )

    def test_is_expected_in_scope_returns_true(self) -> None:
        assert is_expected("tradfi", "CME", "trades")
        assert is_expected("cefi", "BINANCE-FUTURES", "derivative_ticker")
        assert is_expected("sports", "ODDS_API", "odds")
        assert is_expected("prediction", "POLYMARKET", "trades")
        assert is_expected("defi", "AAVEV3-ETHEREUM", "lending_indices")

    def test_is_expected_out_of_scope_returns_false(self) -> None:
        # NASDAQ trades — capable but not in scope.
        assert not is_expected("tradfi", "NASDAQ", "trades")
        # PINNACLE doesn't emit raw odds (only ODDS_API does).
        assert not is_expected("sports", "PINNACLE", "odds")
        # Unknown venue / data_type / asset_group.
        assert not is_expected("cefi", "UNKNOWN", "trades")
        assert not is_expected("cefi", "BINANCE-SPOT", "options_chain")
        assert not is_expected("not_an_asset_group", "CME", "trades")

    def test_is_expected_is_case_insensitive_on_asset_group(self) -> None:
        """Asset_group keys are lowercase; check we accept upper too."""
        assert is_expected("TRADFI", "CME", "trades")
        assert is_expected("CeFi", "BINANCE-FUTURES", "trades")

    def test_get_expected_data_types_for_venue_in_scope(self) -> None:
        cme = get_expected_data_types_for_venue_in_scope("tradfi", "CME")
        assert sorted(cme) == sorted(["trades", "ohlcv_1m", "tbbo"])
        # Out of scope venue → empty.
        assert get_expected_data_types_for_venue_in_scope("tradfi", "NASDAQ") == []

    def test_get_expected_venues_in_scope(self) -> None:
        venues = get_expected_venues_in_scope("tradfi")
        assert "CME" in venues
        assert "ICE" in venues
        assert "CBOE" in venues
        assert "NASDAQ" not in venues
        assert "NYSE" not in venues

    def test_get_expected_pairs_flattens_correctly(self) -> None:
        pairs = get_expected_pairs("prediction")
        assert ("POLYMARKET", "trades") in pairs
        assert ("KALSHI", "trades") in pairs
        assert len(pairs) == 2

    def test_returned_list_is_a_copy(self) -> None:
        """Mutating returned lists must not corrupt the registry."""
        dts = get_expected_data_types_for_venue_in_scope("tradfi", "CME")
        dts.append("XXX")
        assert "XXX" not in EXPECTED_COVERAGE_BY_ASSET_GROUP["tradfi"]["CME"]


class TestRegistryConsistencyWithCapabilities:
    """Cross-check expected coverage stays consistent with declared capabilities."""

    def test_every_expected_pair_is_a_declared_capability(self) -> None:
        """If a (venue, dt) is in scope, the venue must be capable of emitting it.

        Catches typos and scope creep against retired capabilities.
        Exception: Polymarket / Kalshi `trades` is venue-emitted but not
        declared per-data-type in VENUE_DATA_TYPE_CAPABILITIES because
        the prediction trades shard rows are emergent from the
        instruments index (one shard per conditionId, see
        market_data_categories.py docstring near line 605). Skip those.
        """
        prediction_emergent = {
            ("POLYMARKET", "trades"),
            ("KALSHI", "trades"),
        }
        for asset_group, scope in EXPECTED_COVERAGE_BY_ASSET_GROUP.items():
            ag_data_types = set(DATA_TYPES_BY_ASSET_GROUP.get(asset_group, []))
            for venue, dts in scope.items():
                for dt in dts:
                    if (venue, dt) in prediction_emergent:
                        continue
                    # Either the venue declares the capability explicitly
                    # OR the data_type is in the asset_group's general set.
                    declared = VENUE_DATA_TYPE_CAPABILITIES.get(venue, {})
                    assert dt in declared or dt in ag_data_types, (
                        f"Expected ({asset_group}, {venue}, {dt}) is not a "
                        f"declared capability of {venue} or known {asset_group} data_type"
                    )

    def test_pure_derived_processed_types_never_appear_in_expected_coverage(self) -> None:
        """Pure-derived types (no venue emits them) must NEVER be in expected coverage.

        Distinguishes ``arbitrage_opportunity`` (computed by MDPS across
        bookmakers — no venue-native source) from ohlcv_* timeframes
        that ARE venue-native somewhere (CBOE emits ``ohlcv_15m`` for
        VIX; Databento emits ``ohlcv_1m`` natively). The latter
        legitimately appear in expected coverage for the venue that
        emits them as raw, even though they're MDPS-derived for other
        venues. The deployment-api resolver picks raw-vs-processed at
        the (venue, data_type) join, not at the data_type level.
        """
        pure_derived = {"arbitrage_opportunity"}
        for asset_group, scope in EXPECTED_COVERAGE_BY_ASSET_GROUP.items():
            for venue, dts in scope.items():
                for dt in dts:
                    assert dt not in pure_derived, (
                        f"Pure-derived data_type {dt} must not appear in "
                        f"EXPECTED_COVERAGE[{asset_group}][{venue}] — it is "
                        f"computed by MDPS, not emitted by any venue"
                    )

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

    def test_tradfi_us_equity_venues_ohlcv_only(self) -> None:
        """NASDAQ + NYSE OHLCV-only MVP — ohlcv_1m + ohlcv_1s (DBEQ.BASIC L0/free, operator 2026-06-21).
        BARCHART remains operator-omitted (cost-prohibitive per-symbol tick).
        """
        tradfi = EXPECTED_COVERAGE_BY_ASSET_GROUP["tradfi"]
        assert tradfi["NASDAQ"] == ["ohlcv_1m", "ohlcv_1s"]
        assert tradfi["NYSE"] == ["ohlcv_1m", "ohlcv_1s"]
        assert "BARCHART" not in tradfi
        # Futures venues: CME gains ohlcv_1s (Databento lockdown 2026-06-18 —
        # fetches both ohlcv-1s + ohlcv-1m from GLBX.MDP3).
        assert tradfi["CME"] == ["trades", "ohlcv_1s", "ohlcv_1m", "tbbo"]
        # ICE narrowed to ohlcv_24h only (2026-07-13, operator decision) — ICE
        # Databento datasets are out of the 3-dataset subscription; the only real
        # ICE instrument (Yahoo-sourced DXY index) is a daily series.
        assert tradfi["ICE"] == ["ohlcv_24h"]
        # CBOE: VX FUTURES via Databento XCBF.PITCH (CFE dataset, 2026-06-19) —
        # ohlcv_1s + ohlcv_1m only. ohlcv_15m (formerly the VIX cash INDEX via
        # Barchart/Yahoo) REMOVED 2026-07-15 — that fetch path was retired
        # 2026-06-25/26 (operator), so declaring the capability made every
        # request fall through to Databento (no 15m schema) and 100%
        # attempted_fail. Same narrowing pattern as the KRX/ICE precedents. See
        # tradfi_unreachable_databento_data_types_mbp10_ohlcv_coarse_calendar_2026_07_15.md.
        assert tradfi["CBOE"] == ["ohlcv_1s", "ohlcv_1m"]

    def test_sports_excludes_arbitrage_opportunity(self) -> None:
        """arbitrage_opportunity is MDPS-derived; no venue emits it."""
        for venue, dts in EXPECTED_COVERAGE_BY_ASSET_GROUP["sports"].items():
            assert "arbitrage_opportunity" not in dts, (
                f"{venue} should not declare arbitrage_opportunity (it's processed)"
            )

    def test_prediction_data_types_includes_non_instrument_day_grain_types(self) -> None:
        """PR-3/PR-4: prediction set must include the cluster-grain and market-grain types."""
        dts = DATA_TYPES_BY_ASSET_GROUP["prediction"]
        assert "trades" in dts
        assert "prediction_canonical_question_group" in dts, (
            "cluster-grain type missing from DATA_TYPES_BY_ASSET_GROUP[prediction]"
        )
        assert "market_lifecycle" in dts, "market_id-grain type (MTDS/YAML lowercase) missing from prediction"
        assert "MARKET_LIFECYCLE" in dts, "market_id-grain type (instruments-service uppercase) missing from prediction"

    def test_is_expected_in_scope_returns_true(self) -> None:
        assert is_expected("tradfi", "CME", "trades")
        assert is_expected("cefi", "BINANCE-FUTURES", "derivative_ticker")
        assert is_expected("sports", "ODDS_API", "ODDS")  # uppercase ODDS — canonical manifest key
        assert is_expected("sports", "PINNACLE", "trades")
        assert is_expected("prediction", "POLYMARKET", "trades")
        assert is_expected("defi", "AAVE_V3-ETHEREUM", "lending_indices")

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
        assert sorted(cme) == sorted(["trades", "ohlcv_1s", "ohlcv_1m", "tbbo"])
        # NASDAQ carries ohlcv_1m + ohlcv_1s via DBEQ.BASIC (L0/free, operator 2026-06-21).
        assert get_expected_data_types_for_venue_in_scope("tradfi", "NASDAQ") == ["ohlcv_1m", "ohlcv_1s"]

    def test_get_expected_venues_in_scope(self) -> None:
        venues = get_expected_venues_in_scope("tradfi")
        assert "CME" in venues
        assert "ICE" in venues
        assert "CBOE" in venues
        assert "NASDAQ" in venues
        assert "NYSE" in venues

    def test_get_expected_pairs_flattens_correctly(self) -> None:
        pairs = get_expected_pairs("prediction")
        assert ("POLYMARKET", "trades") in pairs
        assert ("POLYMARKET", "book_snapshot_5") in pairs  # re-added 2026-06-23 (live+batch emit it)
        assert ("POLYMARKET", "prediction_canonical_question_group") in pairs
        assert ("KALSHI", "trades") in pairs
        assert ("KALSHI", "book_snapshot_5") in pairs  # re-added 2026-06-23
        assert len(pairs) == 5

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
        that ARE venue-native somewhere (ICE emits ``ohlcv_24h`` for the
        Yahoo-sourced DXY index; Databento emits ``ohlcv_1m`` natively). The
        latter legitimately appear in expected coverage for the venue that
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


class TestOkxAndDeribitComboOptionsChainCapability:
    """Regression for cefi_deribit_combo_and_okx_bare_venue_gaps_2026_07_12.md Bugs C/D.

    Before this fix, ``VENUE_DATA_TYPE_CAPABILITIES`` had no ``options_chain``
    key for ``OKX`` and no entry at all for ``DERIBIT-COMBO`` — the MTDS
    preflight silently dropped the (only) requested data_type on every date,
    with zero rows captured for either venue despite the underlying Tardis
    routing being wired correctly.
    """

    def test_okx_declares_options_chain(self) -> None:
        assert "options_chain" in VENUE_DATA_TYPE_CAPABILITIES["OKX"]
        assert VENUE_DATA_TYPE_CAPABILITIES["OKX"]["options_chain"] == "2020-02-01"

    def test_deribit_combo_declares_options_chain(self) -> None:
        assert "DERIBIT-COMBO" in VENUE_DATA_TYPE_CAPABILITIES
        assert VENUE_DATA_TYPE_CAPABILITIES["DERIBIT-COMBO"]["options_chain"] == "2022-08-23"

    def test_deribit_combo_start_date_not_copied_from_bare_deribit(self) -> None:
        """The two venues' real Tardis coverage genuinely differs — combo/spread
        products launched years after bare Deribit options did (verified live
        via api.tardis.dev/v1/exchanges/deribit this session, not assumed).
        """
        assert (
            VENUE_DATA_TYPE_CAPABILITIES["DERIBIT-COMBO"]["options_chain"]
            != VENUE_DATA_TYPE_CAPABILITIES["DERIBIT"]["options_chain"]
        )

    def test_get_expected_data_types_for_venue_includes_options_chain(self) -> None:
        from unified_api_contracts.registry.market_data_categories import (
            get_expected_data_types_for_venue,
        )

        assert "options_chain" in get_expected_data_types_for_venue("DERIBIT-COMBO")


class TestKrxVenueDataTypeCapabilitiesRegistryGap:
    """Regression for a real registry-gap bug (2026-07-13 pipeline_e2e_check
    TRADFI diagnostic pass): KRX had NO entry at all in
    ``VENUE_DATA_TYPE_CAPABILITIES``, even though every OTHER TradFi venue
    (NASDAQ/NYSE/CME/ICE/CBOE/FX/YAHOO_FINANCE) has one. ``get_expected_data_
    types_for_venue`` falls through to ``get_valid_data_types_for_venue`` (a
    blanket cross-product of ALL 10 TradFi data_types) whenever a venue is
    absent here — directly contradicting the SAME-day narrowed
    ``expected_coverage.py`` KRX entry (``["ohlcv_24h"]``, operator decision:
    Yahoo has no reliable intraday backfill).
    """

    def test_krx_declares_ohlcv_24h_only(self) -> None:
        assert "KRX" in VENUE_DATA_TYPE_CAPABILITIES
        assert set(VENUE_DATA_TYPE_CAPABILITIES["KRX"]) == {"ohlcv_24h"}

    def test_get_expected_data_types_for_venue_krx_is_narrowed(self) -> None:
        from unified_api_contracts.registry.market_data_categories import (
            get_expected_data_types_for_venue,
        )

        assert get_expected_data_types_for_venue("KRX") == ["ohlcv_24h"]


class TestIceExpectedCoverageNarrowedToDailyDxy:
    """Regression for tradfi_ice_ohlcv_1m_no_working_fetch_path_2026_07_13.md:
    ICE's ``expected_coverage.py``/``VENUE_DATA_TYPE_CAPABILITIES`` entries
    declared ``trades``/``ohlcv_1m``/``tbbo`` expected + capable via Databento,
    but the ICE Databento datasets (IFEU.IMPACT/IFUS.IMPACT) were dropped from
    the 3-dataset subscription lockdown (operator 2026-06-18) — ZERO working
    fetch path existed for any of those data_types. The only real ICE
    instrument is the Yahoo-sourced ICE/NYBOT DXY index (``ICE:INDEX:DXY-USD``),
    a DAILY series. Operator decision (2026-07-13): narrow to ``ohlcv_24h``
    only, mirroring the same-day-precedent KRX narrowing
    (krx_intraday_ohlcv_registry_vs_adapter_mismatch_2026_07_12.md).
    """

    def test_ice_declares_ohlcv_24h_only(self) -> None:
        assert "ICE" in VENUE_DATA_TYPE_CAPABILITIES
        assert set(VENUE_DATA_TYPE_CAPABILITIES["ICE"]) == {"ohlcv_24h"}

    def test_ice_start_date_matches_yahoo_indices_dxy_genesis(self) -> None:
        """YAHOO_INDICES' DXY entry (tradfi_instrument_universe.py) genesis is
        date(2019, 1, 2) — VENUE_DATA_TYPE_CAPABILITIES must match, not the
        stale Databento-era 2019-01-01 floor."""
        assert VENUE_DATA_TYPE_CAPABILITIES["ICE"]["ohlcv_24h"] == "2019-01-02"

    def test_get_expected_data_types_for_venue_ice_is_narrowed(self) -> None:
        from unified_api_contracts.registry.market_data_categories import (
            get_expected_data_types_for_venue,
        )

        assert get_expected_data_types_for_venue("ICE") == ["ohlcv_24h"]

    def test_ice_expected_coverage_narrowed(self) -> None:
        assert EXPECTED_COVERAGE_BY_ASSET_GROUP["tradfi"]["ICE"] == ["ohlcv_24h"]

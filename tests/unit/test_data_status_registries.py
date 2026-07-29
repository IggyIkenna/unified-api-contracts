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
    MDPS_CANONICAL_TIMEFRAMES,
    MDPS_DERIVABLE_DATA_TYPES,
    PROCESSED_REQUIRES_RAW,
    get_expected_timeframes_for_venue_dt,
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
        # ohlcv_1s + ohlcv_1m. ohlcv_15m (formerly the VIX cash INDEX via
        # Barchart/Yahoo) REMOVED 2026-07-15 (retired fetch path). ohlcv_24h ADDED
        # 2026-07-15 (operator decision): US Treasury-yield tenors via Yahoo daily
        # OHLCV (routing fix market-tick-data-service@764e7170; ohlcv_24h->Yahoo,
        # VX-futures ohlcv_1s/1m stay Databento). See
        # tradfi_unreachable_databento_data_types_mbp10_ohlcv_coarse_calendar_2026_07_15.md.
        assert tradfi["CBOE"] == ["ohlcv_1s", "ohlcv_1m", "ohlcv_24h"]

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


class TestOkxOptionsChainCapability:
    """Regression for cefi_deribit_combo_and_okx_bare_venue_gaps_2026_07_12.md Bug C.

    Before this fix, ``VENUE_DATA_TYPE_CAPABILITIES`` had no ``options_chain``
    key for ``OKX`` — the MTDS preflight silently dropped the (only) requested
    data_type on every date, with zero rows captured despite the underlying
    Tardis routing being wired correctly.

    (Bug D's DERIBIT-COMBO coverage was removed from this class 2026-07-21 —
    operator decision: legacy venue deregistered, migrated to split
    venue+instrument_type. See market_data_categories.py's
    VENUES_BY_ASSET_GROUP["cefi"] comment.)
    """

    def test_okx_declares_options_chain(self) -> None:
        assert "options_chain" in VENUE_DATA_TYPE_CAPABILITIES["OKX"]
        assert VENUE_DATA_TYPE_CAPABILITIES["OKX"]["options_chain"] == "2020-02-01"


class TestKrxVenueDataTypeCapabilitiesRegistryGap:
    """Regression for a real registry-gap bug (2026-07-13 pipeline_e2e_check
    TRADFI diagnostic pass): KRX had NO entry at all in
    ``VENUE_DATA_TYPE_CAPABILITIES``, even though every OTHER TradFi venue
    (NASDAQ/NYSE/CME/ICE/CBOE/FX) has one. ``get_expected_data_
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


class TestCboeTreasuryOhlcv24hEnabled:
    """Regression: CBOE ohlcv_24h (US Treasury-yield tenors via Yahoo daily OHLCV) was
    ENABLED 2026-07-15 (operator decision) so the shipped routing fix
    (market-tick-data-service@764e7170) carries live traffic — venue_fetch.py's
    UAC-intersection no longer filters (CBOE, ohlcv_24h) out pre-routing. The Yahoo-routed
    ohlcv_24h must NOT disturb the VX-futures ohlcv_1s/ohlcv_1m Databento legs. See
    tradfi_unreachable_databento_data_types_mbp10_ohlcv_coarse_calendar_2026_07_15.md."""

    def test_cboe_declares_ohlcv_24h(self) -> None:
        assert "ohlcv_24h" in VENUE_DATA_TYPE_CAPABILITIES["CBOE"]

    def test_cboe_retains_vx_futures_databento_legs(self) -> None:
        assert "ohlcv_1s" in VENUE_DATA_TYPE_CAPABILITIES["CBOE"]
        assert "ohlcv_1m" in VENUE_DATA_TYPE_CAPABILITIES["CBOE"]

    def test_cboe_ohlcv_24h_start_matches_treasury_genesis(self) -> None:
        # Earliest treasury tenor genesis (^IRX/^FVX/^TNX/^TYX date(2000,1,3)),
        # matching US_TREASURY_YIELD_DAILY_FIRST_DATE.
        assert VENUE_DATA_TYPE_CAPABILITIES["CBOE"]["ohlcv_24h"] == "2000-01-03"

    def test_cboe_expected_coverage_includes_ohlcv_24h(self) -> None:
        assert "ohlcv_24h" in EXPECTED_COVERAGE_BY_ASSET_GROUP["tradfi"]["CBOE"]


class TestYahooFinancePhantomVenueRemoved:
    """Regression for the YAHOO_FINANCE source-as-venue MODELING ERROR
    (tradfi_unreachable_databento_data_types...2026_07_15.md +
    data_pipeline_alerts_batch_remediation_2026_07_15.md). Yahoo Finance is a data
    SOURCE, NOT a venue — real Yahoo-sourced rows land under REAL venues (DXY→ICE,
    KRW/USD→FX, treasuries→CBOE) with source=yahoo, and no fetch code ever stamps
    venue=YAHOO_FINANCE. It was removed 2026-07-15 from every venue-shaped registry
    (VENUES_BY_ASSET_GROUP/VENUE_TO_ASSET_GROUP, VENUE_DATA_TYPE_CAPABILITIES,
    expected_coverage, venue_adapter_keys, data_availability); the SOURCE modeling is
    KEPT (data_source_continuity.py / capability_declarations/_tradfi.py).

    These tests also lock in the get_expected_data_types_for_venue footgun fix: an
    un-narrowed (empty-caps) venue deliberately falls through to the FULL asset-group
    data_type cross-product. That is CORRECT for legit venues (the sports odds
    NO_ADAPTER_YET venues rely on it — MTDS produces their data). De-enumerating a
    source-as-venue is what makes that fallback return [] for it, so the phantom is
    neutralized WITHOUT a blanket guard that would break the legit venues.
    """

    def test_yahoo_finance_is_not_an_enumerated_venue(self) -> None:
        from unified_api_contracts.registry.market_data_categories import (
            VENUE_TO_ASSET_GROUP,
        )

        assert "YAHOO_FINANCE" not in VENUE_TO_ASSET_GROUP
        assert "YAHOO_FINANCE" not in VENUE_DATA_TYPE_CAPABILITIES

    def test_get_expected_data_types_for_yahoo_finance_is_empty(self) -> None:
        """The footgun is neutralized: empty caps + not-a-venue → []."""
        from unified_api_contracts.registry.market_data_categories import (
            get_expected_data_types_for_venue,
        )

        assert get_expected_data_types_for_venue("YAHOO_FINANCE") == []

    def test_legit_sports_no_adapter_venue_keeps_fallback_types(self) -> None:
        """A real NO_ADAPTER_YET venue with no caps MUST still fan out to its full
        asset-group data_types (MTDS produces its data) — proves the empty-caps
        fallback is intact and we did NOT over-correct with a blanket guard."""
        from unified_api_contracts.registry.market_data_categories import (
            get_expected_data_types_for_venue,
            get_valid_data_types_for_venue,
        )

        for venue in ("BETFAIR_EX_EU", "DRAFTKINGS", "FANDUEL"):
            expected = get_expected_data_types_for_venue(venue)
            assert expected, f"{venue} lost its empty-caps fallback types"
            assert expected == get_valid_data_types_for_venue(venue)

    def test_yahoo_finance_source_modeling_is_kept(self) -> None:
        """The SOURCE modeling is intentionally preserved: Yahoo-sourced tradfi rows
        still resolve to source='YAHOO_FINANCE' (they land under REAL venues with
        source=yahoo)."""
        from datetime import date

        from unified_api_contracts.registry.data_source_continuity import (
            get_us_treasury_yield_daily_source,
        )

        assert get_us_treasury_yield_daily_source(date(2024, 6, 1)) == "YAHOO_FINANCE"


class TestMdpsServiceScopedExpectedDataTypes:
    """MDPS timeframe-aware honest-coverage extension
    (mtds_data_status_page_parity_2026_07_21).

    ``get_expected_data_types_for_venue(venue, service="market-data-processing-service")``
    must NARROW the venue's raw-capable dt list to :data:`MDPS_DERIVABLE_DATA_TYPES`
    — the critical, all-3-reviews-converged fix. Without the narrowing, MDPS
    inherits the FULL MTDS raw vocabulary (options_chain/futures_chain/gas_fees/...)
    as "expected", producing permanent false ``missing_data_types``.
    """

    def test_mtds_default_service_unaffected(self) -> None:
        """service="" (the pre-existing MTDS call convention) is BYTE-FOR-BYTE
        unchanged — the MDPS narrowing only applies when service is explicitly
        the MDPS service string."""
        from unified_api_contracts.registry.market_data_categories import (
            get_expected_data_types_for_venue,
        )

        assert get_expected_data_types_for_venue("DERIBIT") == sorted(
            ["trades", "book_snapshot_5", "derivative_ticker", "options_chain", "futures_chain"]
        )
        assert get_expected_data_types_for_venue("DERIBIT", service="market-tick-data-service") == sorted(
            ["trades", "book_snapshot_5", "derivative_ticker", "options_chain", "futures_chain"]
        )

    def test_mdps_narrows_deribit_to_derivable_only(self) -> None:
        """DERIBIT declares 5 raw dts; MDPS only candle-derives 3 of them
        (options_chain/futures_chain have no MDPS ohlcv/candle form)."""
        from unified_api_contracts.registry.market_data_categories import (
            get_expected_data_types_for_venue,
        )

        mdps_dts = get_expected_data_types_for_venue("DERIBIT", service="market-data-processing-service")
        assert set(mdps_dts) == {"trades", "book_snapshot_5", "derivative_ticker"}
        assert "options_chain" not in mdps_dts
        assert "futures_chain" not in mdps_dts

    def test_mdps_includes_tradfi_ohlcv_1m_passthrough_source(self) -> None:
        """TradFi venues (CME) declare raw capability as ``ohlcv_1m``/``ohlcv_1s``
        (Databento passthrough), NOT ``trades``. MDPS derives 5m/15m/1h/4h/1d
        candles FROM ``ohlcv_1m`` — this must NOT narrow to empty for TradFi."""
        from unified_api_contracts.registry.market_data_categories import (
            get_expected_data_types_for_venue,
        )

        mdps_dts = get_expected_data_types_for_venue("CME", service="market-data-processing-service")
        assert "ohlcv_1m" in mdps_dts
        # ohlcv_1s has no MDPS passthrough-raw declaration today (only trades /
        # ohlcv_1m do) — narrowed out.
        assert "ohlcv_1s" not in mdps_dts

    def test_mdps_krx_yahoo_daily_only_venue_is_empty(self) -> None:
        """KRX's only raw capability is ``ohlcv_24h`` (Yahoo daily) — not a
        candle-derivable source — so MDPS has NOTHING expected for KRX."""
        from unified_api_contracts.registry.market_data_categories import (
            get_expected_data_types_for_venue,
        )

        assert get_expected_data_types_for_venue("KRX", service="market-data-processing-service") == []

    def test_mdps_derivable_data_types_matches_processed_prefix_plus_passthrough(self) -> None:
        assert "trades" in MDPS_DERIVABLE_DATA_TYPES
        assert "ohlcv_1m" in MDPS_DERIVABLE_DATA_TYPES
        assert "liquidations" in MDPS_DERIVABLE_DATA_TYPES
        assert "gas_fees" not in MDPS_DERIVABLE_DATA_TYPES
        assert "perp_funding" not in MDPS_DERIVABLE_DATA_TYPES


class TestMdpsCanonicalTimeframes:
    """MDPS_CANONICAL_TIMEFRAMES + get_expected_timeframes_for_venue_dt."""

    def test_canonical_timeframes_uses_1d_not_24h(self) -> None:
        """The forward-write canonical form is "1d" (matching the MDPS writer's
        real ``_normalise_timeframe`` output) -- NOT the legacy "24h" token."""
        assert "1d" in MDPS_CANONICAL_TIMEFRAMES
        assert "24h" not in MDPS_CANONICAL_TIMEFRAMES

    def test_canonical_timeframes_content(self) -> None:
        assert MDPS_CANONICAL_TIMEFRAMES == ("15s", "1m", "5m", "15m", "1h", "4h", "1d")

    def test_get_expected_timeframes_for_venue_dt_is_flat_default(self) -> None:
        """DEFAULT resolution of the per-(venue, dt) timeframe-divergence open
        question: uniformly the flat canonical list regardless of venue/dt,
        today -- the args are accepted so a future override doesn't need a
        signature change."""
        assert get_expected_timeframes_for_venue_dt("BINANCE-FUTURES", "trades") == list(MDPS_CANONICAL_TIMEFRAMES)
        assert get_expected_timeframes_for_venue_dt("CME", "ohlcv_1m") == list(MDPS_CANONICAL_TIMEFRAMES)


class TestGetExpectedDataTypesForVenueForBatch:
    """Regression for lighter_zksync_trades_generic_tardis_path_bypasses_no_batch_source_2026_07_29.md:
    the generic MTDS batch-fetch loop (venue_fetch.py::_process_venue) resolved its
    per-venue data_type list via ``get_expected_data_types_for_venue`` without ever
    consulting ``VENUE_DATA_TYPE_NO_BATCH_SOURCE`` -- so it kept attempting (and
    failing) a real Tardis fetch for LIGHTER-ZKSYNC trades forever, a combo declared
    to have no batch source at all. ``for_batch=True`` closes that gap; default
    ``False`` must stay byte-identical to every other (coverage-display) caller.
    """

    def test_default_still_includes_no_batch_source_combo(self) -> None:
        from unified_api_contracts.registry.market_data_categories import (
            get_expected_data_types_for_venue,
        )

        dts = get_expected_data_types_for_venue("LIGHTER-ZKSYNC")
        assert "trades" in dts, "default (for_batch=False) must not change for existing callers"

    def test_for_batch_excludes_no_batch_source_combo(self) -> None:
        from unified_api_contracts.registry.market_data_categories import (
            get_expected_data_types_for_venue,
        )

        dts = get_expected_data_types_for_venue("LIGHTER-ZKSYNC", for_batch=True)
        assert "trades" not in dts
        assert "book_snapshot_5" not in dts

    def test_for_batch_keeps_batch_sourced_combo(self) -> None:
        from unified_api_contracts.registry.market_data_categories import (
            get_expected_data_types_for_venue,
        )

        dts = get_expected_data_types_for_venue("LIGHTER-ZKSYNC", for_batch=True)
        assert "derivative_ticker" in dts, "LIGHTER-ZKSYNC derivative_ticker IS Tardis-batch-sourced"

    def test_for_batch_is_a_noop_for_venues_with_no_carve_out(self) -> None:
        from unified_api_contracts.registry.market_data_categories import (
            get_expected_data_types_for_venue,
        )

        without = get_expected_data_types_for_venue("BINANCE-FUTURES")
        with_batch = get_expected_data_types_for_venue("BINANCE-FUTURES", for_batch=True)
        assert without == with_batch

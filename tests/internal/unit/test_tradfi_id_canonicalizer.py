"""Unit tests for the shared TradFi raw-id canonicalization primitive.

Covers ``canonicalize_raw_tradfi_id`` on the exact real raw shapes measured
live against the tradfi catalogue/manifest
(``tradfi_consolidated_closeout_2026_07_18.md`` Phase B) — CME short-form
options, CME dated futures, GCS-safe underscore-encoded options, CBOE OPRA
options, CBOE VX futures, CBOE user-defined combo strategies, and the ICE
qualifier banned-char quarantine case — plus the venue-authority invariant
(the `venue` argument, never the id string, decides the output venue) and
``assert_tradfi_derivative_ids_canonical`` (the Phase-B/D verify gate).
"""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.reference.tradfi_id_canonicalizer import (
    TARGET_TRADFI_DERIVATIVE_ID_RE,
    assert_tradfi_derivative_ids_canonical,
    canonicalize_raw_tradfi_id,
)


class TestCanonicalizeRawTradfiIdHappyPath:
    def test_cme_short_option_prefixed_e1af0(self) -> None:
        result = canonicalize_raw_tradfi_id("CME:OPTION:E1AF0 C1600", venue="CME", instrument_type="OPTION")
        assert result.status == "OK"
        assert result.canonical_id is not None
        assert result.canonical_id.startswith("CME:OPTION:SP500-USD@LIN-")
        assert result.canonical_id.endswith("-1600-C")
        assert result.derived_instrument_type == "OPTION"
        assert result.derived_underlying_human == "SP500"
        assert TARGET_TRADFI_DERIVATIVE_ID_RE.match(result.canonical_id)

    def test_cme_dated_future_gcm7_gold(self) -> None:
        result = canonicalize_raw_tradfi_id("CME:FUTURE:GCM7", venue="CME", instrument_type="FUTURE")
        assert result.status == "OK"
        assert result.canonical_id is not None
        assert result.canonical_id.startswith("CME:FUTURE:GOLD-USD@LIN-")
        assert result.derived_underlying_human == "GOLD"
        assert TARGET_TRADFI_DERIVATIVE_ID_RE.match(result.canonical_id)

    def test_underscore_encoded_weekly_option_put(self) -> None:
        result = canonicalize_raw_tradfi_id("EW1H0_P2785", venue="CME", instrument_type="future")
        assert result.status == "OK"
        assert result.canonical_id is not None
        assert result.derived_instrument_type == "OPTION"
        assert result.canonical_id.endswith("-2785-P")
        assert TARGET_TRADFI_DERIVATIVE_ID_RE.match(result.canonical_id)

    def test_cboe_opra_prefixed_spx_option(self) -> None:
        result = canonicalize_raw_tradfi_id("O:SPX260618C00200000", venue="CBOE", instrument_type="OPTION")
        assert result.status == "OK"
        assert result.canonical_id == "CBOE:OPTION:SPX-USD@LIN-20260618-200-C"

    def test_cboe_vx_future(self) -> None:
        result = canonicalize_raw_tradfi_id("CBOE:FUTURE:VX/F1", venue="CBOE", instrument_type="FUTURE")
        assert result.status in ("OK", "QUARANTINE_CONTINUOUS")
        if result.status == "OK":
            assert result.canonical_id is not None
            assert result.canonical_id.startswith("CBOE:FUTURE:VIX-USD@LIN-")
            assert TARGET_TRADFI_DERIVATIVE_ID_RE.match(result.canonical_id)

    def test_dash_before_strike_event_daily_option(self) -> None:
        result = canonicalize_raw_tradfi_id("ECBTCN609-C52500", venue="CME", instrument_type="OPTION")
        assert result.status == "OK"
        assert result.canonical_id is not None
        assert result.canonical_id.endswith("-52500-C")
        assert TARGET_TRADFI_DERIVATIVE_ID_RE.match(result.canonical_id)


class TestCanonicalizeRawTradfiIdQuarantine:
    def test_cboe_user_defined_strategy_underscore_encoded(self) -> None:
        result = canonicalize_raw_tradfi_id("UD_1V__VT_0319838460", venue="CBOE", instrument_type="COMBO")
        assert result.status == "QUARANTINE_COMBO"
        assert result.canonical_id is None
        assert result.derived_instrument_type == "COMBO"

    def test_cboe_user_defined_strategy_colon_form(self) -> None:
        result = canonicalize_raw_tradfi_id("UD:1V: GN 0113805462", venue="CBOE", instrument_type="COMBO")
        assert result.status == "QUARANTINE_COMBO"
        assert result.canonical_id is None

    def test_ice_exclamation_qualifier_now_canonicalizes(self) -> None:
        """ICE ``!`` qualifier (e.g. ``BRN FMH0020!``) — the ``!`` survives
        _normalize_body + classification (ICE_FUTURE_RE accepts ``[!_][A-Z0-9]*``),
        so the underlying comes out as ``"BRN!"``.  Option A strips the ``!``
        suffix before EXCHANGE_CODE_TO_NAME lookup, resolving ``BRN`` → ``BRENT``
        and building the clean canonical id (operator ruling 2026-07-28)."""
        result = canonicalize_raw_tradfi_id("BRN FMH0020!", venue="ICE", instrument_type="FUTURE")
        assert result.status == "OK"
        assert result.canonical_id == "ICE:FUTURE:BRENT-USD@LIN-20200320"
        assert result.derived_instrument_type == "FUTURE"
        assert result.derived_underlying_human == "BRENT"
        assert TARGET_TRADFI_DERIVATIVE_ID_RE.match(result.canonical_id)

    def test_ice_underscore_md1_qualifier_now_canonicalizes(self) -> None:
        """ICE ``_MD1`` qualifier (e.g. ``BRN FMH0020_MD1``) — the pre-strip
        before _normalize_body removes the ``_MD1`` suffix while the body still
        matches the ICE shape, so the classifier sees a clean ``BRN FMH0020``
        and canonicalization succeeds (Option A, operator ruling 2026-07-28)."""
        result = canonicalize_raw_tradfi_id("BRN FMH0020_MD1", venue="ICE", instrument_type="FUTURE")
        assert result.status == "OK"
        assert result.canonical_id == "ICE:FUTURE:BRENT-USD@LIN-20200320"
        assert result.derived_instrument_type == "FUTURE"
        assert result.derived_underlying_human == "BRENT"
        assert TARGET_TRADFI_DERIVATIVE_ID_RE.match(result.canonical_id)

    def test_ice_underscore_z_qualifier_now_canonicalizes(self) -> None:
        """ICE ``_Z`` qualifier (closing-auction variant)."""
        result = canonicalize_raw_tradfi_id("BRN FMH0020_Z", venue="ICE", instrument_type="FUTURE")
        assert result.status == "OK"
        assert result.canonical_id == "ICE:FUTURE:BRENT-USD@LIN-20200320"
        assert result.derived_underlying_human == "BRENT"

    def test_ice_underscore_p_qualifier_now_canonicalizes(self) -> None:
        """ICE ``_P`` qualifier (pending/posting variant)."""
        result = canonicalize_raw_tradfi_id("BRN FMH0020_P", venue="ICE", instrument_type="FUTURE")
        assert result.status == "OK"
        assert result.canonical_id == "ICE:FUTURE:BRENT-USD@LIN-20200320"

    def test_ice_underscore_mm1_qualifier_now_canonicalizes(self) -> None:
        """ICE ``_MM1`` qualifier (market-maker variant)."""
        result = canonicalize_raw_tradfi_id("BRN FMH0020_MM1", venue="ICE", instrument_type="FUTURE")
        assert result.status == "OK"
        assert result.canonical_id == "ICE:FUTURE:BRENT-USD@LIN-20200320"

    def test_ice_gasoil_with_qualifier_now_canonicalizes(self) -> None:
        """ICE Gasoil (``G`` → ``GASOIL``) with ``!`` qualifier — proves the
        fix generalises across ICE product roots, not just BRN."""
        result = canonicalize_raw_tradfi_id("G FMN0024!", venue="ICE", instrument_type="FUTURE")
        assert result.status == "OK"
        assert result.canonical_id == "ICE:FUTURE:GASOIL-USD@LIN-20240719"
        assert result.derived_underlying_human == "GASOIL"
        assert TARGET_TRADFI_DERIVATIVE_ID_RE.match(result.canonical_id)

    def test_ice_wti_with_qualifier_now_canonicalizes(self) -> None:
        """ICE WTI (``T`` → ``WTI``) with ``_Z`` qualifier."""
        result = canonicalize_raw_tradfi_id("T FMZ0025_Z", venue="ICE", instrument_type="FUTURE")
        assert result.status == "OK"
        assert result.canonical_id == "ICE:FUTURE:WTI-USD@LIN-20251219"
        assert result.derived_underlying_human == "WTI"

    def test_bare_ice_symbol_with_venue_argument_unparseable(self) -> None:
        # ``BRN_Z FMH0020`` — qualifier on the ROOT before FM, not after the
        # FM<month>00<year> pattern.  The pre-strip regex only matches
        # ``FM..._<qualifier>`` at end-of-body, so this shape stays unparseable.
        result = canonicalize_raw_tradfi_id("BRN_Z FMH0020", venue="ICE", instrument_type="FUTURE")
        assert result.status == "QUARANTINE_UNPARSEABLE"
        assert result.canonical_id is None

    def test_bare_ice_symbol_never_mints_cme(self) -> None:
        # Regression: venue must come from the `venue` argument only — a bare
        # ICE raw symbol (no VENUE:TYPE: prefix at all in the id string, and
        # no "CME" substring anywhere) must never mint a CME: canonical id.
        # `BRN FMH0020` (clean, no qualifier) is the one ICE shape that
        # classifies AND builds cleanly, so it actually exercises the
        # positive assertion (starts with ICE:) rather than just "not CME:".
        result = canonicalize_raw_tradfi_id("BRN FMH0020", venue="ICE", instrument_type="FUTURE")
        assert result.status == "OK"
        assert result.canonical_id is not None
        assert result.canonical_id.startswith("ICE:")
        assert not result.canonical_id.startswith("CME:")
        assert result.canonical_id == "ICE:FUTURE:BRENT-USD@LIN-20200320"

    def test_null_raw(self) -> None:
        result = canonicalize_raw_tradfi_id("", venue="CME", instrument_type="FUTURE")
        assert result.status == "NULL_OR_EMPTY"
        assert result.canonical_id is None

    def test_whitespace_only_raw(self) -> None:
        result = canonicalize_raw_tradfi_id("   ", venue="CME", instrument_type="FUTURE")
        assert result.status == "NULL_OR_EMPTY"

    def test_unparseable_garbage(self) -> None:
        result = canonicalize_raw_tradfi_id("###not-a-symbol###", venue="CME", instrument_type="FUTURE")
        assert result.status == "QUARANTINE_UNPARSEABLE"
        assert result.canonical_id is None


class TestCanonicalizeRawTradfiIdAlreadyCanonical:
    def test_already_canonical_future_passthrough(self) -> None:
        already = "CME:FUTURE:SP500-USD@LIN-20300621"
        result = canonicalize_raw_tradfi_id(already, venue="CME", instrument_type="FUTURE")
        assert result.status == "ALREADY_CANONICAL"
        assert result.canonical_id == already

    def test_already_canonical_option_passthrough(self) -> None:
        already = "CME:OPTION:SP500-USD@LIN-20251017-5000-C"
        result = canonicalize_raw_tradfi_id(already, venue="CME", instrument_type="OPTION")
        assert result.status == "ALREADY_CANONICAL"
        assert result.canonical_id == already

    def test_already_canonical_requires_venue_agreement(self) -> None:
        # An id that LOOKS canonical for CME but is being re-verified under a
        # different venue argument must NOT be trusted as already-canonical
        # for that other venue.
        already = "CME:FUTURE:SP500-USD@LIN-20300621"
        result = canonicalize_raw_tradfi_id(already, venue="ICE", instrument_type="FUTURE")
        assert result.status != "ALREADY_CANONICAL"


class TestCanonicalizeRawTradfiIdNeverTrustsInstrumentTypeColumn:
    def test_mislabeled_instrument_type_column_ignored(self) -> None:
        # ~400k live manifest rows carry a mislabeled instrument_type (options
        # stamped FUTURE). The classifier-derived type must win regardless of
        # what the (wrong) column says.
        result = canonicalize_raw_tradfi_id("CME:OPTION:E1AF0 C1600", venue="CME", instrument_type="FUTURE")
        assert result.derived_instrument_type == "OPTION"


class TestCanonicalizeRawTradfiIdCashTypes:
    """Coverage for the Phase-B cash-type ``-USD`` extension
    (``tradfi_consolidated_closeout_2026_07_18.md`` Phase B follow-up (B)):
    EQUITY/CURRENCY/ETF/BOND/COMMODITY/INDEX rows return ``OK`` with the
    explicit ``-USD`` quote built via ``build_instrument_id`` (which now
    appends it, ``unified-api-contracts@33e3f369``) — never quarantined.
    """

    def test_prefixed_equity_gets_usd_suffix(self) -> None:
        result = canonicalize_raw_tradfi_id("NASDAQ:EQUITY:AAPL", venue="NASDAQ", instrument_type="EQUITY")
        assert result.status == "OK"
        assert result.canonical_id == "NASDAQ:EQUITY:AAPL-USD"
        assert result.derived_instrument_type == "EQUITY"
        assert result.derived_underlying_human == "AAPL"

    def test_prefixed_currency_gets_usd_suffix(self) -> None:
        # CURRENCY is the case the classifier would get WRONG (a bare "KRW"
        # ticker default-classifies as EQUITY, see classify_databento_symbol
        # step 6) — proves the embedded VENUE:TYPE: prefix wins over any
        # classifier guess (the cash path never calls the classifier).
        result = canonicalize_raw_tradfi_id("FX:CURRENCY:KRW", venue="FX", instrument_type="CURRENCY")
        assert result.status == "OK"
        assert result.canonical_id == "FX:CURRENCY:KRW-USD"
        assert result.derived_instrument_type == "CURRENCY"

    def test_bare_raw_ticker_uses_stored_column_for_cash_type(self) -> None:
        # No embedded VENUE:TYPE: prefix at all (a raw manifest ticker row,
        # e.g. "ASTS") — falls back to the caller-supplied stored
        # instrument_type column to recognise the cash type.
        result = canonicalize_raw_tradfi_id("ASTS", venue="NASDAQ", instrument_type="EQUITY")
        assert result.status == "OK"
        assert result.canonical_id == "NASDAQ:EQUITY:ASTS-USD"

    def test_cash_already_canonical_with_usd_suffix_is_passthrough(self) -> None:
        already = "NASDAQ:EQUITY:AAPL-USD"
        result = canonicalize_raw_tradfi_id(already, venue="NASDAQ", instrument_type="EQUITY")
        assert result.status == "ALREADY_CANONICAL"
        assert result.canonical_id == already

    def test_cash_never_double_appends_usd(self) -> None:
        # A bare-ticker raw id that already happens to carry a -USD suffix
        # (e.g. a partially-migrated row) must not become "...-USD-USD".
        result = canonicalize_raw_tradfi_id("AAPL-USD", venue="NASDAQ", instrument_type="EQUITY")
        assert result.status == "OK"
        assert result.canonical_id == "NASDAQ:EQUITY:AAPL-USD"

    @pytest.mark.parametrize(
        ("cash_type", "symbol"),
        [("ETF", "IBIT"), ("BOND", "US10Y"), ("COMMODITY", "XAU"), ("INDEX", "SPX")],
    )
    def test_every_cash_type_gets_usd_suffix(self, cash_type: str, symbol: str) -> None:
        result = canonicalize_raw_tradfi_id(symbol, venue="CBOE", instrument_type=cash_type)
        assert result.status == "OK"
        assert result.canonical_id == f"CBOE:{cash_type}:{symbol}-USD"
        assert result.derived_instrument_type == cash_type

    def test_cds_excluded_from_cash_quote_suffix_falls_through(self) -> None:
        # CDS is intentionally excluded from the -USD convention
        # (canonical_id_builder._TRADFI_CASH_QUOTE_SUFFIXED_TYPES — no
        # base/quote dimension) so it must NOT be caught by the cash
        # short-circuit; it falls through to the unrelated FUTURE/OPTION/
        # COMBO path and quarantines rather than silently minting a
        # wrong-shaped id.
        result = canonicalize_raw_tradfi_id("ITRAXX_EUR", venue="ICE", instrument_type="CDS")
        assert result.status == "QUARANTINE_UNPARSEABLE"
        assert result.canonical_id is None

    def test_massive_index_ticker_strips_i_prefix(self) -> None:
        # Massive/Polygon.io index tickers carry an "I:" vendor prefix (e.g. a real
        # live catalogue row raw_symbol="I:VIX") — must NOT leak into the symbol
        # segment as "CBOE:INDEX:I:VIX-USD"; same convention already stripped by
        # external.massive.normalize.normalize_massive_index.
        result = canonicalize_raw_tradfi_id("I:VIX", venue="CBOE", instrument_type="INDEX")
        assert result.status == "OK"
        assert result.canonical_id == "CBOE:INDEX:VIX-USD"

    def test_prefix_stripped_empty_body_is_null_or_empty(self) -> None:
        result = canonicalize_raw_tradfi_id("NASDAQ:EQUITY:", venue="NASDAQ", instrument_type="EQUITY")
        assert result.status == "NULL_OR_EMPTY"
        assert result.canonical_id is None


class TestCanonicalizeRawTradfiIdComboRestampSignal:
    """Coverage for the Phase-B combo re-stamp contract
    (``tradfi_consolidated_closeout_2026_07_18.md`` Phase B follow-up (A)): a
    ``QUARANTINE_COMBO`` row's raw id is intentionally left UNCHANGED
    (``canonical_id`` is ``None`` — combo-ID canonicalization itself is the
    separate ``canonical_id_p1_tradfi_combo_leg_canonicalization_2026_07_08.md``
    track), but ``derived_instrument_type`` is always the UPPERCASE ``"COMBO"``
    enum value so a migration script can re-stamp the row's WRONG stored
    ``instrument_type`` (a mislabeled ``future``/``FUTURE``) without touching
    the id.
    """

    def test_cboe_combo_mislabeled_future_signals_combo_restamp(self) -> None:
        # Real live shape: a CBOE UD_ combo persisted with a stale stored
        # instrument_type=FUTURE (the ~400k-mislabel class) — the primitive
        # must derive COMBO regardless of the (wrong) stored column.
        result = canonicalize_raw_tradfi_id("UD_1V__VT_0319838460", venue="CBOE", instrument_type="FUTURE")
        assert result.status == "QUARANTINE_COMBO"
        assert result.canonical_id is None  # id intentionally left unchanged
        assert result.derived_instrument_type == "COMBO"  # migration re-stamp signal

    def test_cboe_combo_mislabeled_lowercase_future_signals_combo_restamp(self) -> None:
        # Same, but the live manifest's mixed-case mislabel variant.
        result = canonicalize_raw_tradfi_id("UD:1V: GN 0113805462", venue="CBOE", instrument_type="future")
        assert result.status == "QUARANTINE_COMBO"
        assert result.canonical_id is None
        assert result.derived_instrument_type == "COMBO"


class TestAssertTradfiDerivativeIdsCanonical:
    def test_all_canonical(self) -> None:
        ids = [
            "CME:FUTURE:SP500-USD@LIN-20300621",
            "CME:OPTION:SP500-USD@LIN-20251017-5000-C",
            "CBOE:FUTURE:VIX-USD@LIN-20260722",
        ]
        types = ["FUTURE", "OPTION", "FUTURE"]
        checked, canonical, violations = assert_tradfi_derivative_ids_canonical(ids, types)
        assert checked == 3
        assert canonical == 3
        assert violations == []

    def test_flags_whitespace_and_shape_and_bare_lin(self) -> None:
        ids = [
            "CME:OPTION:E3AN6 C7960",  # raw whitespace-carrying id
            "CBOE:FUTURE:VX/F1",  # raw shape, residual slash
            "BINANCE_FUTURES:PERPETUAL:BTC-USDT@LIN",  # not FUTURE/OPTION — skipped
            "CME:FUTURE:SP500@LIN-20300621",  # bare @LIN missing -USD
        ]
        types = ["OPTION", "FUTURE", "PERPETUAL", "FUTURE"]
        checked, canonical, violations = assert_tradfi_derivative_ids_canonical(ids, types)
        # The PERPETUAL row is not FUTURE/OPTION by id-embedded type -> excluded from `checked`.
        assert checked == 3
        assert canonical == 0
        assert len(violations) == 3

    def test_non_derivative_rows_excluded_from_checked(self) -> None:
        ids = ["CME:EQUITY:AAPL-USD", "BINANCE:SPOT_PAIR:BTCUSDT"]
        types = ["EQUITY", "SPOT_PAIR"]
        checked, canonical, violations = assert_tradfi_derivative_ids_canonical(ids, types)
        assert checked == 0
        assert canonical == 0
        assert violations == []

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            assert_tradfi_derivative_ids_canonical(["CME:FUTURE:SP500-USD@LIN-20300621"], [])

    def test_violations_sample_bounded(self) -> None:
        ids = [f"CME:FUTURE:BAD ID {i}" for i in range(75)]
        types = ["FUTURE"] * 75
        checked, canonical, violations = assert_tradfi_derivative_ids_canonical(ids, types)
        assert checked == 75
        assert canonical == 0
        assert len(violations) == 50

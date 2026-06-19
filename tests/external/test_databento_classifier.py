"""Tests for ``unified_api_contracts.external.databento.databento_classifier``.

Phase 1.7 of ``data_canonicalisation_mvp_2026_04_17`` — verifies:

* continuous futures roots (``ES``, ``NQ``, ``CL``) classify as
  ``FUTURE`` with ``is_continuous=True`` so MTDS can skip fetching them;
* dated futures (``ESM6``) yield ``FUTURE`` with correct underlying and
  third-Friday expiry;
* CME short-form options (``E2AJ6 C6190``) yield ``OPTION`` with the
  futures root (``ES``), strike, and call/put flag;
* equity tickers (``AAPL``) yield ``EQUITY`` by default;
* index tickers (``SPX``) yield ``INDEX``;
* asset-class hint resolves ``SPY`` → ``ETF`` when hinted, ``EQUITY``
  without;
* unparseable input raises ``ValueError`` — no silent defaults.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal

import pytest

from unified_api_contracts import ComboStrategyType, InstrumentType, MultiLegInstrument
from unified_api_contracts.external.databento import (
    DatabentoClassification,
    classify_databento_symbol,
)

# ---------------------------------------------------------------------------
# Continuous futures
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("root", ["ES", "NQ", "CL", "GC"])
def test_continuous_root_codes_flagged_continuous(root: str) -> None:
    cls = classify_databento_symbol(root)
    assert isinstance(cls, DatabentoClassification)
    assert cls.instrument_type is InstrumentType.FUTURE
    assert cls.underlying == root
    assert cls.is_continuous is True
    assert cls.expiry_date is None
    assert cls.strike is None
    assert cls.option_right is None


# ---------------------------------------------------------------------------
# Dated futures
# ---------------------------------------------------------------------------


def test_dated_future_esm6_classifies_with_third_friday_expiry() -> None:
    cls = classify_databento_symbol("ESM6")
    assert cls.instrument_type is InstrumentType.FUTURE
    assert cls.underlying == "ES"
    assert cls.is_continuous is False
    # M = June, year token "6" → 2026, third Friday = 2026-06-19.
    assert cls.expiry_date == _dt.date(2026, 6, 19)
    assert cls.strike is None
    assert cls.option_right is None


def test_dated_future_two_digit_year_classifies() -> None:
    cls = classify_databento_symbol("NQZ24")
    assert cls.instrument_type is InstrumentType.FUTURE
    assert cls.underlying == "NQ"
    assert cls.expiry_date is not None
    assert cls.expiry_date.year == 2024
    assert cls.expiry_date.month == 12


# ---------------------------------------------------------------------------
# Cboe VX (VIX) futures — XCBF.PITCH slash-delimited parent symbology
# ---------------------------------------------------------------------------


def test_vx_future_outright_classifies_with_vix_settlement_expiry() -> None:
    # VX/M6 = VIX June-2026. VX settles 30d before the NEXT month's third Friday
    # (July 2026 third Friday = 2026-07-17; minus 30d = 2026-06-17).
    cls = classify_databento_symbol("VX/M6")
    assert cls.instrument_type is InstrumentType.FUTURE
    assert cls.underlying == "VX"
    assert cls.is_continuous is False
    assert cls.expiry_date == _dt.date(2026, 6, 17)
    assert cls.strike is None
    assert cls.option_right is None


def test_vx_future_december_rolls_year_for_expiry() -> None:
    # VX/Z6 = VIX Dec-2026. Next month is Jan-2027 (third Friday 2027-01-15);
    # minus 30d = 2026-12-16.
    cls = classify_databento_symbol("VX/Z6")
    assert cls.instrument_type is InstrumentType.FUTURE
    assert cls.underlying == "VX"
    assert cls.expiry_date == _dt.date(2026, 12, 16)


def test_vx_calendar_spread_is_not_classifiable() -> None:
    # Calendar-spread legs carry the ``:1:S``/``:1:B`` qualifier — not outright
    # contracts; classification must reject them (the OHLCV adapter then drops them).
    import pytest

    with pytest.raises(ValueError):
        classify_databento_symbol("VX/N6:1:S - VX/Q6:1:B")


# ---------------------------------------------------------------------------
# CME short-form options
# ---------------------------------------------------------------------------


def test_cme_short_option_classifies_strike_and_right() -> None:
    cls = classify_databento_symbol("E2AJ6 C6190")
    assert cls.instrument_type is InstrumentType.OPTION
    assert cls.underlying == "ES"  # E2-prefix derives the ES future underlying
    assert cls.option_right == "C"
    assert cls.strike == Decimal("6190")
    # April 2026, third Friday = 2026-04-17.
    assert cls.expiry_date == _dt.date(2026, 4, 17)
    assert cls.is_continuous is False
    assert cls.root_cluster == "E2A"


@pytest.mark.parametrize(
    ("symbol", "expected_cluster"),
    [
        ("ESM4 P5800", "ES"),  # quarterly
        ("EWJ6 C6000", "EW"),  # weekly Friday
        ("EW1J6 C6100", "EW1"),  # weekly Monday
        ("EW2J4 C5400", "EW2"),  # weekly Wednesday
        ("EW4J6 C5900", "EW4"),  # weekly Tuesday
        ("E1AN4 C5090", "E1A"),  # daily Monday (0DTE)
        ("E5AJ6 C6200", "E5A"),  # daily Friday
        ("EOMG5 C5100", "EOM"),  # end-of-month
    ],
)
def test_cme_short_option_root_cluster_taxonomy(symbol: str, expected_cluster: str) -> None:
    cls = classify_databento_symbol(symbol)
    assert cls.instrument_type is InstrumentType.OPTION
    assert cls.root_cluster == expected_cluster


def test_cme_short_option_put_with_decimal_strike() -> None:
    cls = classify_databento_symbol("NGF5 P3.50")
    assert cls.instrument_type is InstrumentType.OPTION
    assert cls.option_right == "P"
    assert cls.strike == Decimal("3.50")


# ---------------------------------------------------------------------------
# Equities / ETFs / indices
# ---------------------------------------------------------------------------


def test_equity_ticker_classifies_default() -> None:
    cls = classify_databento_symbol("AAPL")
    assert cls.instrument_type is InstrumentType.EQUITY
    assert cls.underlying == "AAPL"
    assert cls.is_continuous is False
    assert cls.expiry_date is None


def test_etf_hint_yields_etf_type() -> None:
    cls = classify_databento_symbol("SPY", asset_class_hint="etf")
    assert cls.instrument_type is InstrumentType.ETF
    assert cls.underlying == "SPY"


def test_etf_without_hint_defaults_to_equity() -> None:
    cls = classify_databento_symbol("SPY")
    # Documented default — without a hint, we can't distinguish.
    assert cls.instrument_type is InstrumentType.EQUITY


def test_known_index_ticker_classifies_index() -> None:
    cls = classify_databento_symbol("SPX")
    assert cls.instrument_type is InstrumentType.INDEX
    assert cls.underlying == "SPX"


# ---------------------------------------------------------------------------
# CME FX futures (Family 1 — ``6AM4``-style)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("symbol", "expected_root", "expected_expiry"),
    [
        ("6AM4", "6A", _dt.date(2024, 6, 19)),  # AUD Jun-2024
        ("6BH5", "6B", _dt.date(2025, 3, 19)),  # GBP Mar-2025
        ("6CZ4", "6C", _dt.date(2024, 12, 18)),  # CAD Dec-2024
        ("6EU4", "6E", _dt.date(2024, 9, 18)),  # EUR Sep-2024
        ("6JM5", "6J", _dt.date(2025, 6, 18)),  # JPY Jun-2025
        ("6SZ6", "6S", _dt.date(2026, 12, 16)),  # CHF Dec-2026
    ],
)
def test_cme_fx_future_classifies_with_third_wednesday_expiry(
    symbol: str,
    expected_root: str,
    expected_expiry: _dt.date,
) -> None:
    cls = classify_databento_symbol(symbol)
    assert cls.instrument_type is InstrumentType.FUTURE
    assert cls.underlying == expected_root
    assert cls.is_continuous is False
    assert cls.expiry_date == expected_expiry
    assert cls.strike is None
    assert cls.option_right is None
    assert cls.leg_symbols is None


# ---------------------------------------------------------------------------
# Calendar spreads / combos (Family 2 — ``LEG1-LEG2``)
# ---------------------------------------------------------------------------


def test_calendar_spread_6ah5_6am4_classifies_combo() -> None:
    cls = classify_databento_symbol("6AH5-6AM4")
    assert cls.instrument_type is InstrumentType.COMBO
    # Shared root (``6A``) normalised to the human-readable AUDUSD.
    assert cls.underlying == "AUDUSD"
    assert cls.is_continuous is False
    # Near-leg expiry = earliest of the two legs.
    # 6AH5 → 2025-03-19, 6AM4 → 2024-06-19 → min = 2024-06-19.
    assert cls.expiry_date == _dt.date(2024, 6, 19)
    assert cls.strike is None
    assert cls.option_right is None
    assert cls.leg_symbols == ("6AH5", "6AM4")
    assert cls.combo_strategy is ComboStrategyType.CALENDAR
    assert isinstance(cls.multileg, MultiLegInstrument)
    assert len(cls.multileg.legs) == 2
    assert cls.expiries == (_dt.date(2024, 6, 19), _dt.date(2025, 3, 19))


def test_calendar_spread_esm4_esu4_classifies_combo() -> None:
    cls = classify_databento_symbol("ESM4-ESU4")
    assert cls.instrument_type is InstrumentType.COMBO
    # ES normalises to the readable SP500.
    assert cls.underlying == "SP500"
    assert cls.leg_symbols == ("ESM4", "ESU4")
    assert cls.combo_strategy is ComboStrategyType.CALENDAR
    # ESM4 → 2024-06-21 (third Friday), ESU4 → 2024-09-20, min = June.
    assert cls.expiry_date == _dt.date(2024, 6, 21)


def test_three_leg_butterfly_from_dashes() -> None:
    # ESH5-ESM5-ESU5 — 3 legs same underlying → inferred BUTTERFLY.
    cls = classify_databento_symbol("ESH5-ESM5-ESU5")
    assert cls.instrument_type is InstrumentType.COMBO
    assert cls.underlying == "SP500"
    assert cls.leg_symbols == ("ESH5", "ESM5", "ESU5")
    assert cls.combo_strategy is ComboStrategyType.BUTTERFLY
    assert len(cls.expiries) == 3


def test_four_leg_iron_condor_from_dashes() -> None:
    cls = classify_databento_symbol("ESH5-ESM5-ESU5-ESZ5")
    assert cls.instrument_type is InstrumentType.COMBO
    assert cls.underlying == "SP500"
    assert len(cls.leg_symbols or ()) == 4
    assert cls.combo_strategy is ComboStrategyType.IRON_CONDOR


def test_prefix_butterfly_expands_legs() -> None:
    # ``ES:BF U4-V4-X4`` — prefix + shared-root shorthand.
    cls = classify_databento_symbol("ES:BF U4-V4-X4")
    assert cls.instrument_type is InstrumentType.COMBO
    assert cls.underlying == "SP500"
    assert cls.combo_strategy is ComboStrategyType.BUTTERFLY
    assert cls.leg_symbols == ("ESU4", "ESV4", "ESX4")
    assert len(cls.expiries) == 3


def test_prefix_iron_condor_expands_legs() -> None:
    cls = classify_databento_symbol("ES:IC U4-V4-X4-Z4")
    assert cls.instrument_type is InstrumentType.COMBO
    assert cls.combo_strategy is ComboStrategyType.IRON_CONDOR
    assert cls.leg_symbols == ("ESU4", "ESV4", "ESX4", "ESZ4")


def test_prefix_calendar_expands_legs() -> None:
    cls = classify_databento_symbol("ES:CL U4-V4")
    assert cls.instrument_type is InstrumentType.COMBO
    assert cls.combo_strategy is ComboStrategyType.CALENDAR
    assert cls.leg_symbols == ("ESU4", "ESV4")


def test_prefix_unknown_treated_as_custom() -> None:
    # Unknown combo prefixes are classified as CUSTOM (Databento adds new prefixes over time).
    cls = classify_databento_symbol("ES:XX U4-V4")
    assert cls.combo_strategy is ComboStrategyType.CUSTOM


def test_calendar_spread_with_invalid_leg_raises() -> None:
    # Second leg has an invalid shape — must fail loud.
    with pytest.raises(ValueError):
        classify_databento_symbol("6AH5-GARBAGE123!")


# ---------------------------------------------------------------------------
# Unparseable → ValueError (no silent fallback)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "1234567890ABCDEF",  # unrecognised shape
        "ES Q!",  # garbage
    ],
)
def test_unparseable_symbol_raises_value_error(bad: str) -> None:
    with pytest.raises(ValueError):
        classify_databento_symbol(bad)


# ---------------------------------------------------------------------------
# OSI-packed equity options (OPRA)
# ---------------------------------------------------------------------------


def test_osi_packed_equity_option_classifies() -> None:
    # ``AAPL  240119C00150000`` → AAPL Jan-19-2024 Call $150.00.
    cls = classify_databento_symbol("AAPL  240119C00150000")
    assert cls.instrument_type is InstrumentType.OPTION
    assert cls.underlying == "AAPL"
    assert cls.expiry_date == _dt.date(2024, 1, 19)
    assert cls.strike == Decimal("150.000")
    assert cls.option_right == "C"
    assert cls.is_continuous is False


def test_osi_packed_equity_option_put_compact() -> None:
    # Compact (no padding) form also accepted.
    cls = classify_databento_symbol("TSLA241220P00250000")
    assert cls.instrument_type is InstrumentType.OPTION
    assert cls.underlying == "TSLA"
    assert cls.expiry_date == _dt.date(2024, 12, 20)
    assert cls.strike == Decimal("250.000")
    assert cls.option_right == "P"


# ---------------------------------------------------------------------------
# CME event-contract daily options (binary settlement)
# ---------------------------------------------------------------------------


def test_cme_event_daily_option_classifies() -> None:
    # ``ECBTCJ615 P74000`` → root ECBTC, Apr-2026, day 15, put, strike 74000.
    cls = classify_databento_symbol("ECBTCJ615 P74000")
    assert cls.instrument_type is InstrumentType.OPTION
    assert cls.underlying == "ECBTC"
    assert cls.expiry_date == _dt.date(2026, 4, 15)
    assert cls.option_right == "P"
    assert cls.strike == Decimal("74000")


# ---------------------------------------------------------------------------
# ICE commodity futures (``BRN FMH0020``-style)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("symbol", "expected_root"),
    [
        ("BRN FMH0020", "BRN"),  # Brent Mar-2020
        ("G FMN0024", "G"),  # Gasoil Jul-2024
        ("CC FMN0024", "CC"),  # Cocoa Jul-2024
    ],
)
def test_ice_commodity_future_classifies(symbol: str, expected_root: str) -> None:
    cls = classify_databento_symbol(symbol)
    assert cls.instrument_type is InstrumentType.FUTURE
    assert cls.underlying == expected_root
    assert cls.is_continuous is False
    assert cls.expiry_date is not None


def test_ice_future_qualifier_preserved_in_underlying() -> None:
    cls = classify_databento_symbol("BRN FMH0020!")
    assert cls.instrument_type is InstrumentType.FUTURE
    assert cls.underlying == "BRN!"


# ---------------------------------------------------------------------------
# CME/ICE continuous-contract prefix futures + combos
# ---------------------------------------------------------------------------


def test_bare_continuous_prefix_future_flagged_continuous() -> None:
    cls = classify_databento_symbol("CL:C1")
    assert cls.instrument_type is InstrumentType.FUTURE
    assert cls.underlying == "CL"
    assert cls.is_continuous is True


def test_continuous_prefix_combo_classifies_spread() -> None:
    cls = classify_databento_symbol("CL:C1 HO-CL H0")
    assert cls.instrument_type is InstrumentType.COMBO
    assert cls.underlying == "CL"
    assert cls.combo_strategy is ComboStrategyType.SPREAD
    assert isinstance(cls.multileg, MultiLegInstrument)


# ---------------------------------------------------------------------------
# CBOE user-defined strategies (opaque combos)
# ---------------------------------------------------------------------------


def test_cboe_user_defined_strategy_classifies_custom_combo() -> None:
    cls = classify_databento_symbol("UD:1V: GN 0113805462")
    assert cls.instrument_type is InstrumentType.COMBO
    assert cls.underlying == "GN"
    assert cls.combo_strategy is ComboStrategyType.CUSTOM
    assert cls.leg_symbols == ("0113805462",)
    assert isinstance(cls.multileg, MultiLegInstrument)


def test_cboe_user_defined_strategy_root_qualified() -> None:
    cls = classify_databento_symbol("UD:ZN: TL 0219823765")
    assert cls.instrument_type is InstrumentType.COMBO
    assert cls.combo_strategy is ComboStrategyType.CUSTOM


# ---------------------------------------------------------------------------
# Combo-strategy inference branches (vertical / diagonal / multi-underlying)
# ---------------------------------------------------------------------------


def test_vertical_option_spread_same_expiry_different_strike() -> None:
    # Two OSI options, same underlying + expiry, different strikes → VERTICAL.
    cls = classify_databento_symbol("AAPL240119C00150000-AAPL240119C00160000")
    assert cls.instrument_type is InstrumentType.COMBO
    assert cls.combo_strategy is ComboStrategyType.VERTICAL


def test_diagonal_option_spread_different_expiry() -> None:
    # Two OSI options, same underlying, different expiry → DIAGONAL.
    cls = classify_databento_symbol("AAPL240119C00150000-AAPL240216C00150000")
    assert cls.instrument_type is InstrumentType.COMBO
    assert cls.combo_strategy is ComboStrategyType.DIAGONAL


def test_multi_underlying_combo_joins_roots() -> None:
    # Two futures, different underlyings → joined, normalised underlying string.
    cls = classify_databento_symbol("ESM4-NQM4")
    assert cls.instrument_type is InstrumentType.COMBO
    assert "-" in cls.underlying  # SP500-NASDAQ100 form
    assert cls.combo_strategy is ComboStrategyType.SPREAD


def test_index_hint_yields_index_type() -> None:
    cls = classify_databento_symbol("DAX", asset_class_hint="index")
    assert cls.instrument_type is InstrumentType.INDEX
    assert cls.underlying == "DAX"

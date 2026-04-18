"""Unit tests for the centralised canonical instrument ID builder.

Covers:
- Happy-path formatting for every ``InstrumentType`` variant.
- Required-kwarg validation for OPTION, FUTURE, POOL.
- Venue upper-casing (free-form venue string).
- DeFi ``VENUE-CHAIN`` composition.
- Full enum coverage via union of ``SUPPORTED_INSTRUMENT_TYPES`` and ``UNSUPPORTED_BY_DESIGN``.
- Top-level ``unified_api_contracts.build_instrument_id`` re-export.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal

import pytest

from unified_api_contracts import ComboStrategyType
from unified_api_contracts import build_combo_id as top_level_build_combo_id
from unified_api_contracts import build_instrument_id as top_level_build_instrument_id
from unified_api_contracts._instrument_enums import InstrumentType
from unified_api_contracts.internal.reference.canonical_id_builder import (
    SUPPORTED_INSTRUMENT_TYPES,
    UNSUPPORTED_BY_DESIGN,
    build_combo_id,
    build_instrument_id,
)

# ---------------------------------------------------------------------------
# Happy-path — one test per InstrumentType
# ---------------------------------------------------------------------------


class TestCefiHappyPath:
    def test_spot_pair(self) -> None:
        assert build_instrument_id("binance", InstrumentType.SPOT_PAIR, "BTCUSDT") == "BINANCE:SPOT_PAIR:BTCUSDT"

    def test_perpetual(self) -> None:
        assert (
            build_instrument_id("binance_futures", InstrumentType.PERPETUAL, "BTCUSDT")
            == "BINANCE_FUTURES:PERPETUAL:BTCUSDT"
        )

    def test_future_dated(self) -> None:
        assert (
            build_instrument_id(
                "bybit",
                InstrumentType.FUTURE,
                "BTC",
                expiry_date=_dt.date(2026, 6, 26),
            )
            == "BYBIT:FUTURE:BTC-20260626"
        )

    def test_option_call(self) -> None:
        assert (
            build_instrument_id(
                "deribit",
                InstrumentType.OPTION,
                "BTC",
                expiry_date=_dt.date(2026, 3, 28),
                strike=Decimal("65000"),
                option_right="C",
            )
            == "DERIBIT:OPTION:BTC-20260328-65000-C"
        )

    def test_option_put_fractional_strike(self) -> None:
        # Fractional strikes should preserve precision, no exponent form.
        assert (
            build_instrument_id(
                "deribit",
                InstrumentType.OPTION,
                "ETH",
                expiry_date=_dt.date(2026, 4, 26),
                strike=Decimal("2500.5"),
                option_right="P",
            )
            == "DERIBIT:OPTION:ETH-20260426-2500.5-P"
        )


class TestTradfiHappyPath:
    def test_future(self) -> None:
        assert (
            build_instrument_id(
                "cme",
                InstrumentType.FUTURE,
                "ES",
                expiry_date=_dt.date(2026, 6, 20),
            )
            == "CME:FUTURE:ES-20260620"
        )

    def test_option_on_future(self) -> None:
        assert (
            build_instrument_id(
                "cme",
                InstrumentType.OPTION,
                "ES",
                expiry_date=_dt.date(2026, 4, 17),
                strike=Decimal("6190"),
                option_right="C",
            )
            == "CME:OPTION:ES-20260417-6190-C"
        )

    def test_equity(self) -> None:
        assert build_instrument_id("nasdaq", InstrumentType.EQUITY, "AAPL") == "NASDAQ:EQUITY:AAPL"

    def test_index(self) -> None:
        assert build_instrument_id("cboe", InstrumentType.INDEX, "SPX") == "CBOE:INDEX:SPX"

    def test_etf(self) -> None:
        assert build_instrument_id("arca", InstrumentType.ETF, "SPY") == "ARCA:ETF:SPY"

    def test_commodity(self) -> None:
        assert build_instrument_id("nymex", InstrumentType.COMMODITY, "CL") == "NYMEX:COMMODITY:CL"

    def test_currency(self) -> None:
        assert build_instrument_id("ibkr", InstrumentType.CURRENCY, "EURUSD") == "IBKR:CURRENCY:EURUSD"

    def test_bond(self) -> None:
        assert build_instrument_id("cbot", InstrumentType.BOND, "UST10Y") == "CBOT:BOND:UST10Y"

    def test_cds(self) -> None:
        assert build_instrument_id("ice", InstrumentType.CDS, "ITRAXX_EUR") == "ICE:CDS:ITRAXX_EUR"


class TestDefiHappyPath:
    def test_pool(self) -> None:
        assert (
            build_instrument_id(
                "uniswap_v3",
                InstrumentType.POOL,
                "USDC-WETH-500",
                chain="ethereum",
            )
            == "UNISWAP_V3-ETHEREUM:POOL:USDC-WETH-500"
        )

    def test_a_token(self) -> None:
        assert (
            build_instrument_id(
                "aave_v3",
                InstrumentType.A_TOKEN,
                "aUSDC",
                chain="ethereum",
            )
            == "AAVE_V3-ETHEREUM:A_TOKEN:aUSDC"
        )

    def test_debt_token(self) -> None:
        assert (
            build_instrument_id(
                "aave_v3",
                InstrumentType.DEBT_TOKEN,
                "variableDebtUSDC",
                chain="ethereum",
            )
            == "AAVE_V3-ETHEREUM:DEBT_TOKEN:variableDebtUSDC"
        )

    def test_lending(self) -> None:
        assert (
            build_instrument_id(
                "aave_v3",
                InstrumentType.LENDING,
                "USDC",
                chain="ethereum",
            )
            == "AAVE_V3-ETHEREUM:LENDING:USDC"
        )

    def test_lst(self) -> None:
        assert (
            build_instrument_id(
                "lido",
                InstrumentType.LST,
                "stETH",
                chain="ethereum",
            )
            == "LIDO-ETHEREUM:LST:stETH"
        )

    def test_staking(self) -> None:
        assert (
            build_instrument_id(
                "lido",
                InstrumentType.STAKING,
                "ETH",
                chain="ethereum",
            )
            == "LIDO-ETHEREUM:STAKING:ETH"
        )

    def test_yield_bearing(self) -> None:
        assert (
            build_instrument_id(
                "ethena",
                InstrumentType.YIELD_BEARING,
                "sUSDe",
                chain="ethereum",
            )
            == "ETHENA-ETHEREUM:YIELD_BEARING:sUSDe"
        )

    def test_spot_asset(self) -> None:
        # Free-standing ERC-20 held outside a protocol.
        assert (
            build_instrument_id(
                "erc20",
                InstrumentType.SPOT_ASSET,
                "USDC",
                chain="ethereum",
            )
            == "ERC20-ETHEREUM:SPOT_ASSET:USDC"
        )


class TestMultiLegAndSportsHappyPath:
    def test_combo(self) -> None:
        assert (
            build_instrument_id("deribit", InstrumentType.COMBO, "BTC_CAL_20260328_20260926")
            == "DERIBIT:COMBO:BTC_CAL_20260328_20260926"
        )

    def test_prediction_market(self) -> None:
        inner = "PRED:SPORTS:abc123def456"
        assert (
            build_instrument_id("polymarket", InstrumentType.PREDICTION_MARKET, inner)
            == f"POLYMARKET:PREDICTION_MARKET:{inner}"
        )

    def test_exchange_odds(self) -> None:
        inner = "FOOTBALL:BETFAIR_EX_UK:MATCH_ODDS:ENG_PREMIER_LEAGUE:2025-26:ARSENAL-CHELSEA::HOME"
        assert build_instrument_id("betfair", InstrumentType.EXCHANGE_ODDS, inner) == f"BETFAIR:EXCHANGE_ODDS:{inner}"

    def test_fixed_odds(self) -> None:
        inner = "FOOTBALL:PINNACLE:MATCH_ODDS:ENG_PREMIER_LEAGUE:2025-26:ARSENAL-CHELSEA::HOME"
        assert build_instrument_id("pinnacle", InstrumentType.FIXED_ODDS, inner) == f"PINNACLE:FIXED_ODDS:{inner}"

    def test_prop(self) -> None:
        inner = "PROP:ANYTIME_SCORER:SAKA_B"
        assert build_instrument_id("sharpapi", InstrumentType.PROP, inner) == f"SHARPAPI:PROP:{inner}"


# ---------------------------------------------------------------------------
# Missing-kwarg validation
# ---------------------------------------------------------------------------


class TestMissingKwargs:
    def test_option_missing_expiry(self) -> None:
        with pytest.raises(ValueError, match="OPTION requires"):
            build_instrument_id(
                "deribit",
                InstrumentType.OPTION,
                "BTC",
                strike=Decimal("65000"),
                option_right="C",
            )

    def test_option_missing_strike(self) -> None:
        with pytest.raises(ValueError, match="OPTION requires"):
            build_instrument_id(
                "deribit",
                InstrumentType.OPTION,
                "BTC",
                expiry_date=_dt.date(2026, 3, 28),
                option_right="C",
            )

    def test_option_missing_right(self) -> None:
        with pytest.raises(ValueError, match="OPTION requires"):
            build_instrument_id(
                "deribit",
                InstrumentType.OPTION,
                "BTC",
                expiry_date=_dt.date(2026, 3, 28),
                strike=Decimal("65000"),
            )

    def test_option_invalid_right(self) -> None:
        with pytest.raises(ValueError, match="option_right must be"):
            # Mis-cased right should fail strictly — no coercion.
            build_instrument_id(
                "deribit",
                InstrumentType.OPTION,
                "BTC",
                expiry_date=_dt.date(2026, 3, 28),
                strike=Decimal("65000"),
                option_right="c",  # pyright: ignore[reportArgumentType]
            )

    def test_future_missing_expiry(self) -> None:
        with pytest.raises(ValueError, match="FUTURE requires expiry_date"):
            build_instrument_id("cme", InstrumentType.FUTURE, "ES")

    def test_pool_missing_symbol(self) -> None:
        with pytest.raises(ValueError, match="POOL requires"):
            build_instrument_id(
                "uniswap_v3",
                InstrumentType.POOL,
                "",
                chain="ethereum",
            )

    def test_empty_venue(self) -> None:
        with pytest.raises(ValueError, match="venue must be a non-empty"):
            build_instrument_id("", InstrumentType.SPOT_PAIR, "BTCUSDT")


# ---------------------------------------------------------------------------
# Venue / chain normalisation
# ---------------------------------------------------------------------------


class TestVenueNormalisation:
    def test_unknown_venue_upper_cased(self) -> None:
        # Venue is free-form — any non-empty string works, but must be upper-cased.
        assert (
            build_instrument_id("new_venue_123", InstrumentType.SPOT_PAIR, "BTCUSDT")
            == "NEW_VENUE_123:SPOT_PAIR:BTCUSDT"
        )

    def test_mixed_case_venue_is_normalised(self) -> None:
        assert build_instrument_id("Binance", InstrumentType.SPOT_PAIR, "btcusdt") == "BINANCE:SPOT_PAIR:BTCUSDT"

    def test_defi_venue_chain_composition(self) -> None:
        result = build_instrument_id(
            "aave_v3",
            InstrumentType.LENDING,
            "USDC",
            chain="arbitrum",
        )
        assert result == "AAVE_V3-ARBITRUM:LENDING:USDC"

    def test_defi_chain_is_uppercased(self) -> None:
        result = build_instrument_id(
            "uniswap_v3",
            InstrumentType.POOL,
            "USDC-WETH-500",
            chain="Polygon",
        )
        assert result == "UNISWAP_V3-POLYGON:POOL:USDC-WETH-500"


# ---------------------------------------------------------------------------
# Coverage — every enum variant is either supported or explicitly opted out.
# ---------------------------------------------------------------------------


class TestCoverage:
    def test_every_instrument_type_is_classified(self) -> None:
        all_types: frozenset[InstrumentType] = frozenset(InstrumentType)
        classified = SUPPORTED_INSTRUMENT_TYPES | UNSUPPORTED_BY_DESIGN
        missing = all_types - classified
        assert not missing, (
            f"InstrumentType values not handled by builder: {sorted(t.value for t in missing)}. "
            "Add to SUPPORTED_INSTRUMENT_TYPES (and dispatch) or to UNSUPPORTED_BY_DESIGN."
        )

    def test_supported_and_unsupported_are_disjoint(self) -> None:
        overlap = SUPPORTED_INSTRUMENT_TYPES & UNSUPPORTED_BY_DESIGN
        assert not overlap, (
            f"InstrumentType values must not be both supported and unsupported: {sorted(t.value for t in overlap)}"
        )

    def test_supported_set_matches_enum_today(self) -> None:
        # Today every enum value is supported — UNSUPPORTED_BY_DESIGN is empty.
        # If this ever fails, update SUPPORTED_INSTRUMENT_TYPES or
        # UNSUPPORTED_BY_DESIGN with an explicit justification.
        assert frozenset(InstrumentType) == SUPPORTED_INSTRUMENT_TYPES
        assert frozenset() == UNSUPPORTED_BY_DESIGN


# ---------------------------------------------------------------------------
# Public re-export
# ---------------------------------------------------------------------------


class TestBuildComboId:
    def test_butterfly_three_strikes(self) -> None:
        assert (
            build_combo_id(
                "CME",
                "SP500",
                ComboStrategyType.BUTTERFLY,
                anchor_expiry=_dt.date(2024, 6, 21),
                strikes=[Decimal(5500), Decimal(5600), Decimal(5700)],
            )
            == "CME:COMBO:SP500-BUTTERFLY-20240621-5500-5600-5700"
        )

    def test_iron_condor_four_strikes(self) -> None:
        assert (
            build_combo_id(
                "CME",
                "SP500",
                ComboStrategyType.IRON_CONDOR,
                anchor_expiry=_dt.date(2024, 6, 21),
                strikes=[Decimal(5400), Decimal(5500), Decimal(5600), Decimal(5700)],
            )
            == "CME:COMBO:SP500-IRON_CONDOR-20240621-5400-5500-5600-5700"
        )

    def test_calendar_two_expiries(self) -> None:
        assert (
            build_combo_id(
                "CME",
                "SP500",
                ComboStrategyType.CALENDAR,
                expiries=[_dt.date(2024, 6, 21), _dt.date(2024, 9, 20)],
            )
            == "CME:COMBO:SP500-CALENDAR-20240621-20240920"
        )

    def test_calendar_spread_two_expiries(self) -> None:
        assert (
            build_combo_id(
                "CME",
                "SP500",
                ComboStrategyType.CALENDAR_SPREAD,
                expiries=[_dt.date(2024, 6, 21), _dt.date(2024, 9, 20)],
            )
            == "CME:COMBO:SP500-CALENDAR_SPREAD-20240621-20240920"
        )

    def test_straddle_single_strike(self) -> None:
        assert (
            build_combo_id(
                "CME",
                "SP500",
                ComboStrategyType.STRADDLE,
                anchor_expiry=_dt.date(2024, 6, 21),
                strikes=[Decimal(5600)],
            )
            == "CME:COMBO:SP500-STRADDLE-20240621-5600"
        )

    def test_butterfly_without_expiry_raises(self) -> None:
        with pytest.raises(ValueError, match="requires anchor_expiry"):
            build_combo_id(
                "CME",
                "SP500",
                ComboStrategyType.BUTTERFLY,
                strikes=[Decimal(5500), Decimal(5600), Decimal(5700)],
            )

    def test_butterfly_without_strikes_raises(self) -> None:
        with pytest.raises(ValueError, match="requires at least one strike"):
            build_combo_id(
                "CME",
                "SP500",
                ComboStrategyType.BUTTERFLY,
                anchor_expiry=_dt.date(2024, 6, 21),
            )

    def test_calendar_single_expiry_raises(self) -> None:
        with pytest.raises(ValueError, match="requires at least two expiries"):
            build_combo_id(
                "CME",
                "SP500",
                ComboStrategyType.CALENDAR,
                expiries=[_dt.date(2024, 6, 21)],
            )

    def test_empty_underlying_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty underlying"):
            build_combo_id(
                "CME",
                "",
                ComboStrategyType.BUTTERFLY,
                anchor_expiry=_dt.date(2024, 6, 21),
                strikes=[Decimal(5600)],
            )

    def test_custom_strategy_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"does not accept ComboStrategyType\.CUSTOM"):
            build_combo_id(
                "CME",
                "SP500",
                ComboStrategyType.CUSTOM,
                anchor_expiry=_dt.date(2024, 6, 21),
                strikes=[Decimal(5600)],
            )


class TestTopLevelReExport:
    def test_top_level_alias_is_same_callable(self) -> None:
        assert top_level_build_instrument_id is build_instrument_id

    def test_top_level_build_combo_id_is_same_callable(self) -> None:
        assert top_level_build_combo_id is build_combo_id

"""Unit tests for the centralised canonical instrument ID builder.

Covers:
- Happy-path formatting for every ``InstrumentType`` variant.
- Required-kwarg validation for OPTION, FUTURE, POOL.
- Venue upper-casing (free-form venue string).
- DeFi ``VENUE-CHAIN`` composition.
- Full enum coverage via union of ``SUPPORTED_INSTRUMENT_TYPES`` and ``UNSUPPORTED_BY_DESIGN``.
- Top-level ``unified_api_contracts.build_instrument_id`` re-export.
- ``passthrough=True`` raw exchange-native id wrapping.
- ``build_leg`` — shared InstrumentLeg construction for multi-leg combos.
- ``build_canonical_instrument_id`` — the one-entry-point dispatcher for
  every asset group (CeFi/DeFi/TradFi/Prediction/Sports).
- A CCXT-vs-Tardis compatibility table proving the shared builder reproduces
  the real, already-shipped per-venue ids from
  ``canonical_id_p0_ccxt_live_batch_divergence_2026_07_08.md`` without the
  CCXT adapter itself needing to call this module.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal

import pytest

from unified_api_contracts import AssetGroup, ComboStrategyType
from unified_api_contracts import build_combo_id as top_level_build_combo_id
from unified_api_contracts import build_instrument_id as top_level_build_instrument_id
from unified_api_contracts._instrument_enums import InstrumentType
from unified_api_contracts.internal import InstrumentLeg
from unified_api_contracts.internal.reference.canonical_id_builder import (
    SUPPORTED_INSTRUMENT_TYPES,
    UNSUPPORTED_BY_DESIGN,
    build_canonical_instrument_id,
    build_combo_id,
    build_instrument_id,
    build_leg,
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
        # INDEX carries the canonical -USD base-quote suffix (matches the
        # data-write key, symbology GCS key and source-resolver keys).
        assert build_instrument_id("cboe", InstrumentType.INDEX, "SPX") == "CBOE:INDEX:SPX-USD"

    def test_index_explicit_quote(self) -> None:
        assert build_instrument_id("cboe", InstrumentType.INDEX, "US10Y", quote_asset="USD") == "CBOE:INDEX:US10Y-USD"

    def test_etf(self) -> None:
        # Non-index cash types keep the plain VENUE:TYPE:SYMBOL form (no -USD).
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
        assert build_instrument_id("opticodds", InstrumentType.PROP, inner) == f"OPTICODDS:PROP:{inner}"


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
# v6 settlement-dimension disambiguation (quote_asset + margin_type kwargs)
# ---------------------------------------------------------------------------


class TestV6SettlementDimensions:
    """Phase 2c — quote_asset + margin_type embed in OPTION / FUTURE canonical IDs."""

    def test_option_inverse_deribit(self) -> None:
        result = build_instrument_id(
            "deribit",
            InstrumentType.OPTION,
            "BTC",
            expiry_date=_dt.date(2026, 12, 26),
            strike=Decimal("100000"),
            option_right="C",
            quote_asset="USD",
            margin_type="inverse",
        )
        assert result == "DERIBIT:OPTION:BTC-USD-inverse-20261226-100000-C"

    def test_option_linear_deribit(self) -> None:
        result = build_instrument_id(
            "deribit",
            InstrumentType.OPTION,
            "BTC",
            expiry_date=_dt.date(2026, 12, 26),
            strike=Decimal("100000"),
            option_right="C",
            quote_asset="USDC",
            margin_type="linear",
        )
        assert result == "DERIBIT:OPTION:BTC-USDC-linear-20261226-100000-C"

    def test_future_inverse(self) -> None:
        result = build_instrument_id(
            "deribit",
            InstrumentType.FUTURE,
            "BTC",
            expiry_date=_dt.date(2026, 12, 26),
            quote_asset="USD",
            margin_type="inverse",
        )
        assert result == "DERIBIT:FUTURE:BTC-USD-inverse-20261226"

    def test_future_linear(self) -> None:
        result = build_instrument_id(
            "binance_futures",
            InstrumentType.FUTURE,
            "BTC",
            expiry_date=_dt.date(2026, 6, 26),
            quote_asset="USDT",
            margin_type="linear",
        )
        assert result == "BINANCE_FUTURES:FUTURE:BTC-USDT-linear-20260626"

    def test_option_no_settlement_dims_unchanged(self) -> None:
        # Legacy callers omitting the new kwargs get the pre-v6 format.
        result = build_instrument_id(
            "deribit",
            InstrumentType.OPTION,
            "BTC",
            expiry_date=_dt.date(2026, 3, 28),
            strike=Decimal("65000"),
            option_right="C",
        )
        assert result == "DERIBIT:OPTION:BTC-20260328-65000-C"

    def test_future_no_settlement_dims_unchanged(self) -> None:
        result = build_instrument_id(
            "cme",
            InstrumentType.FUTURE,
            "ES",
            expiry_date=_dt.date(2026, 6, 20),
        )
        assert result == "CME:FUTURE:ES-20260620"

    def test_only_quote_without_margin_uses_legacy_format(self) -> None:
        # Both must be non-empty for the v6 segment to appear.
        result = build_instrument_id(
            "deribit",
            InstrumentType.OPTION,
            "BTC",
            expiry_date=_dt.date(2026, 3, 28),
            strike=Decimal("65000"),
            option_right="C",
            quote_asset="USD",
        )
        assert result == "DERIBIT:OPTION:BTC-20260328-65000-C"

    def test_only_margin_without_quote_uses_legacy_format(self) -> None:
        result = build_instrument_id(
            "deribit",
            InstrumentType.OPTION,
            "BTC",
            expiry_date=_dt.date(2026, 3, 28),
            strike=Decimal("65000"),
            option_right="C",
            margin_type="inverse",
        )
        assert result == "DERIBIT:OPTION:BTC-20260328-65000-C"

    def test_option_put_with_settlement_dims(self) -> None:
        result = build_instrument_id(
            "deribit",
            InstrumentType.OPTION,
            "ETH",
            expiry_date=_dt.date(2026, 6, 26),
            strike=Decimal("3000"),
            option_right="P",
            quote_asset="USD",
            margin_type="inverse",
        )
        assert result == "DERIBIT:OPTION:ETH-USD-inverse-20260626-3000-P"


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


# ---------------------------------------------------------------------------
# passthrough=True — raw exchange-native id wrapping
# ---------------------------------------------------------------------------


class TestPassthrough:
    def test_option_passthrough_matches_tardis_convention(self) -> None:
        # Deribit's real raw instrument_name already encodes expiry/strike/right —
        # passthrough wraps it verbatim instead of reconstructing from parts.
        assert (
            build_instrument_id("deribit", InstrumentType.OPTION, "BTC-9JUL26-56000-C", passthrough=True)
            == "DERIBIT:OPTION:BTC-9JUL26-56000-C"
        )

    def test_future_passthrough_no_expiry_required(self) -> None:
        # No expiry_date/strike/option_right needed — passthrough bypasses
        # the structured-reconstruction requirement entirely.
        assert (
            build_instrument_id("bybit", InstrumentType.FUTURE, "BTCUSDT-10JUL26", passthrough=True)
            == "BYBIT:FUTURE:BTCUSDT-10JUL26"
        )

    def test_passthrough_upper_cases_cefi_symbol(self) -> None:
        assert (
            build_instrument_id("binance", InstrumentType.SPOT_PAIR, "btcusdt", passthrough=True)
            == "BINANCE:SPOT_PAIR:BTCUSDT"
        )

    def test_passthrough_preserves_defi_symbol_case(self) -> None:
        # DeFi token symbols stay case-sensitive even under passthrough.
        assert (
            build_instrument_id("aave_v3", InstrumentType.A_TOKEN, "aUSDC", chain="ethereum", passthrough=True)
            == "AAVE_V3-ETHEREUM:A_TOKEN:aUSDC"
        )

    def test_passthrough_empty_symbol_raises(self) -> None:
        with pytest.raises(ValueError, match="passthrough=True requires"):
            build_instrument_id("deribit", InstrumentType.OPTION, "", passthrough=True)


# ---------------------------------------------------------------------------
# build_leg — shared InstrumentLeg construction
# ---------------------------------------------------------------------------


class TestBuildLeg:
    def test_cme_calendar_leg_passthrough(self) -> None:
        leg = build_leg("CME", InstrumentType.FUTURE, "ESM6", side="BUY", passthrough=True)
        assert leg == InstrumentLeg(instrument_key="CME:FUTURE:ESM6", side="BUY", ratio=1)

    def test_deribit_combo_leg_passthrough_with_ratio(self) -> None:
        leg = build_leg(
            "DERIBIT",
            InstrumentType.OPTION,
            "BTC-25DEC26-70000-C",
            side="SELL",
            ratio=2,
            passthrough=True,
        )
        assert leg == InstrumentLeg(instrument_key="DERIBIT:OPTION:BTC-25DEC26-70000-C", side="SELL", ratio=2)

    def test_structured_option_leg(self) -> None:
        leg = build_leg(
            "deribit",
            InstrumentType.OPTION,
            "BTC",
            side="BUY",
            expiry_date=_dt.date(2026, 3, 28),
            strike=Decimal("65000"),
            option_right="C",
        )
        assert leg == InstrumentLeg(instrument_key="DERIBIT:OPTION:BTC-20260328-65000-C", side="BUY", ratio=1)

    def test_leg_default_ratio_is_one(self) -> None:
        leg = build_leg("CME", InstrumentType.FUTURE, "CLZ26", side="SELL", passthrough=True)
        assert leg.ratio == 1


# ---------------------------------------------------------------------------
# build_canonical_instrument_id — one entry point, every asset group
# ---------------------------------------------------------------------------


class TestBuildCanonicalInstrumentId:
    def test_cefi_delegates_to_build_instrument_id(self) -> None:
        assert (
            build_canonical_instrument_id(AssetGroup.CEFI, "bybit", InstrumentType.PERPETUAL, "BTCUSDT")
            == "BYBIT:PERPETUAL:BTCUSDT"
        )

    def test_cefi_accepts_lowercase_string_asset_group(self) -> None:
        # Free-form string is accepted, not just the AssetGroup enum member.
        assert (
            build_canonical_instrument_id("cefi", "bybit", InstrumentType.PERPETUAL, "BTCUSDT")
            == "BYBIT:PERPETUAL:BTCUSDT"
        )

    def test_defi_delegates_with_chain(self) -> None:
        assert (
            build_canonical_instrument_id(AssetGroup.DEFI, "aave_v3", InstrumentType.LENDING, "USDC", chain="arbitrum")
            == "AAVE_V3-ARBITRUM:LENDING:USDC"
        )

    def test_tradfi_delegates_with_expiry(self) -> None:
        assert (
            build_canonical_instrument_id(
                AssetGroup.TRADFI,
                "cme",
                InstrumentType.FUTURE,
                "ES",
                expiry_date=_dt.date(2026, 6, 20),
            )
            == "CME:FUTURE:ES-20260620"
        )

    def test_prediction_delegates_to_build_instrument_id(self) -> None:
        inner = "PRED:SPORTS:abc123def456"
        assert (
            build_canonical_instrument_id(AssetGroup.PREDICTION, "polymarket", InstrumentType.PREDICTION_MARKET, inner)
            == f"POLYMARKET:PREDICTION_MARKET:{inner}"
        )

    def test_sports_dispatches_to_fixture_builder_not_venue_type_symbol(self) -> None:
        result = build_canonical_instrument_id(
            AssetGroup.SPORTS,
            league="ENG_PREMIER_LEAGUE",
            home_team="ARSENAL",
            away_team="CHELSEA",
            fixture_date="2026-03-22",
        )
        assert result == "ENG_PREMIER_LEAGUE:ARSENAL_v_CHELSEA:20260322"
        # Structurally NOT VENUE:TYPE:SYMBOL — only 2 colons, not the
        # 3-colon-minimum shape every other asset group produces.
        assert result.count(":") == 2

    def test_sports_with_fixture_time(self) -> None:
        result = build_canonical_instrument_id(
            "sports",
            league="ENG_PREMIER_LEAGUE",
            home_team="ARSENAL",
            away_team="CHELSEA",
            fixture_date="2026-03-22",
            fixture_time="15:00",
        )
        assert result == "ENG_PREMIER_LEAGUE:ARSENAL_v_CHELSEA:20260322_1500"

    def test_sports_missing_required_fields_raises(self) -> None:
        with pytest.raises(ValueError, match="asset_group=sports requires"):
            build_canonical_instrument_id(AssetGroup.SPORTS, league="ENG_PREMIER_LEAGUE")

    def test_non_sports_missing_instrument_type_raises(self) -> None:
        with pytest.raises(ValueError, match="requires instrument_type"):
            build_canonical_instrument_id(AssetGroup.CEFI, "bybit", None, "BTCUSDT")

    def test_invalid_asset_group_string_raises(self) -> None:
        with pytest.raises(ValueError):
            build_canonical_instrument_id("not_a_real_asset_group", "bybit", InstrumentType.PERPETUAL, "BTCUSDT")

    def test_passthrough_forwarded(self) -> None:
        result = build_canonical_instrument_id(
            AssetGroup.CEFI,
            "deribit",
            InstrumentType.OPTION,
            "BTC-9JUL26-56000-C",
            passthrough=True,
        )
        assert result == "DERIBIT:OPTION:BTC-9JUL26-56000-C"


# ---------------------------------------------------------------------------
# CCXT-vs-Tardis compatibility table — proves the shared builder reproduces
# the real, already-shipped per-venue ids from the CCXT live/batch fix
# (canonical_id_p0_ccxt_live_batch_divergence_2026_07_08.md) WITHOUT the CCXT
# adapter itself needing to route through this module. Values below are the
# real "NEW ccxt instrument_key" / "REAL Tardis instrument_key" column from
# that plan's per-venue verification table (all 13 venues converged there).
# ---------------------------------------------------------------------------


class TestCcxtTardisCompatibility:
    @pytest.mark.parametrize(
        ("venue", "instrument_type", "symbol", "expected"),
        [
            ("binance-spot", InstrumentType.SPOT_PAIR, "BTC-USDT", "BINANCE-SPOT:SPOT_PAIR:BTC-USDT"),
            ("binance-futures", InstrumentType.PERPETUAL, "BTC-USDT", "BINANCE-FUTURES:PERPETUAL:BTC-USDT"),
            ("bybit", InstrumentType.PERPETUAL, "0G-USDT", "BYBIT:PERPETUAL:0G-USDT"),
            ("bybit-spot", InstrumentType.SPOT_PAIR, "BTC-USDT", "BYBIT-SPOT:SPOT_PAIR:BTC-USDT"),
            ("okx-spot", InstrumentType.SPOT_PAIR, "BTC-USD", "OKX-SPOT:SPOT_PAIR:BTC-USD"),
            ("okx-swap", InstrumentType.PERPETUAL, "BTC-USD", "OKX-SWAP:PERPETUAL:BTC-USD"),
            ("coinbase-spot", InstrumentType.SPOT_PAIR, "BTC-USD", "COINBASE-SPOT:SPOT_PAIR:BTC-USD"),
            ("upbit", InstrumentType.SPOT_PAIR, "WAXP-KRW", "UPBIT:SPOT_PAIR:WAXP-KRW"),
            ("kraken-spot", InstrumentType.SPOT_PAIR, "0G-USD", "KRAKEN-SPOT:SPOT_PAIR:0G-USD"),
            ("kraken-futures", InstrumentType.PERPETUAL, "BTC-USD", "KRAKEN-FUTURES:PERPETUAL:BTC-USD"),
        ],
    )
    def test_cefi_simple_shapes_match_shipped_ccxt_fix(
        self, venue: str, instrument_type: InstrumentType, symbol: str, expected: str
    ) -> None:
        # Structured base-quote construction — no passthrough needed for
        # SPOT_PAIR/PERPETUAL since the shipped CCXT fix reconstructs these
        # from ccxt's own base/quote fields (same shape build_instrument_id
        # already produces).
        assert build_instrument_id(venue, instrument_type, symbol) == expected

    @pytest.mark.parametrize(
        ("venue", "instrument_type", "raw_symbol", "expected"),
        [
            ("bybit", InstrumentType.FUTURE, "BTCUSDT-10JUL26", "BYBIT:FUTURE:BTCUSDT-10JUL26"),
            ("okx-futures", InstrumentType.FUTURE, "BTC-USD-260710", "OKX-FUTURES:FUTURE:BTC-USD-260710"),
            ("deribit", InstrumentType.OPTION, "BTC-9JUL26-56000-C", "DERIBIT:OPTION:BTC-9JUL26-56000-C"),
        ],
    )
    def test_dated_derivative_passthrough_matches_shipped_ccxt_fix(
        self, venue: str, instrument_type: InstrumentType, raw_symbol: str, expected: str
    ) -> None:
        # Dated FUTURE/OPTION: the shipped CCXT fix passes through ccxt's raw
        # exchange-native market id verbatim (matching Tardis), exactly what
        # passthrough=True does here — this is the gap noted in that plan's
        # Progress Log as the reason it did NOT route through this module at
        # the time ("would reconstruct FUTURE/OPTION ids from
        # expiry/strike/right rather than passing through the raw
        # exchange-native id like Tardis does").
        assert build_instrument_id(venue, instrument_type, raw_symbol, passthrough=True) == expected

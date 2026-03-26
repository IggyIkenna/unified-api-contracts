"""Tests for InstrumentGenerator — realistic instrument definitions for mock/test."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime

import pytest

from unified_api_contracts import CanonicalInstrument, InstrumentType, OptionType
from unified_api_contracts.internal.testing.instrument_generator import InstrumentGenerator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REF_DATE = date(2025, 1, 15)
SEED = 42
KEY_PATTERN = re.compile(r"^[A-Z0-9_-]+:[A-Z_]+:.+$")


@pytest.fixture
def gen() -> InstrumentGenerator:
    return InstrumentGenerator(seed=SEED)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_valid_instruments(instruments: list[CanonicalInstrument]) -> None:
    """Assert all instruments are valid CanonicalInstrument records with compliant keys."""
    assert len(instruments) > 0
    for inst in instruments:
        assert isinstance(inst, CanonicalInstrument)
        # instrument_key format: VENUE:TYPE:SYMBOL
        assert KEY_PATTERN.match(inst.instrument_key), f"Bad key format: {inst.instrument_key}"
        parts = inst.instrument_key.split(":")
        assert len(parts) == 3, f"Key must have 3 colon-separated parts: {inst.instrument_key}"
        assert inst.venue, "venue must be set"
        assert inst.symbol, "symbol must be set"
        assert inst.timestamp is not None


# ---------------------------------------------------------------------------
# CeFi Spot
# ---------------------------------------------------------------------------


class TestCefiSpot:
    def test_returns_valid_instruments(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_spot(REF_DATE)
        _assert_valid_instruments(instruments)

    def test_expected_venues(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_spot(REF_DATE)
        venues = {i.venue for i in instruments}
        assert "BINANCE-SPOT" in venues
        assert "COINBASE" in venues
        assert "BYBIT" in venues
        assert "OKX" in venues
        assert "UPBIT" in venues

    def test_instrument_type_is_spot(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_spot(REF_DATE)
        for inst in instruments:
            assert inst.instrument_type == InstrumentType.SPOT_PAIR

    def test_has_base_and_quote(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_spot(REF_DATE)
        for inst in instruments:
            assert inst.base_asset is not None
            assert inst.quote_asset is not None

    def test_available_from_set(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_spot(REF_DATE)
        for inst in instruments:
            assert inst.available_from_datetime is not None
            assert inst.available_to_datetime is None

    def test_count(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_spot(REF_DATE)
        assert len(instruments) == 7


# ---------------------------------------------------------------------------
# CeFi Perpetuals
# ---------------------------------------------------------------------------


class TestCefiPerpetuals:
    def test_returns_valid_instruments(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_perpetuals(REF_DATE)
        _assert_valid_instruments(instruments)

    def test_expected_venues(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_perpetuals(REF_DATE)
        venues = {i.venue for i in instruments}
        expected = {"BINANCE-FUTURES", "DERIBIT", "HYPERLIQUID", "OKX", "BYBIT", "ASTER"}
        assert venues == expected

    def test_instrument_type_is_perpetual(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_perpetuals(REF_DATE)
        for inst in instruments:
            assert inst.instrument_type == InstrumentType.PERPETUAL

    def test_has_leverage_fields(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_perpetuals(REF_DATE)
        for inst in instruments:
            assert inst.max_leverage is not None
            assert inst.initial_margin_rate is not None
            assert inst.maintenance_margin_rate is not None

    def test_count(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_perpetuals(REF_DATE)
        assert len(instruments) == 6


# ---------------------------------------------------------------------------
# CeFi Futures
# ---------------------------------------------------------------------------


class TestCefiFutures:
    def test_returns_valid_instruments(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_futures(REF_DATE)
        _assert_valid_instruments(instruments)

    def test_deribit_and_cme(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_futures(REF_DATE)
        venues = {i.venue for i in instruments}
        assert "DERIBIT" in venues
        assert "CME" in venues

    def test_expiry_dates_in_future(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_futures(REF_DATE)
        ref_dt = datetime(REF_DATE.year, REF_DATE.month, REF_DATE.day, tzinfo=UTC)
        for inst in instruments:
            assert inst.expiry is not None
            assert inst.expiry > ref_dt

    def test_deribit_naming(self, gen: InstrumentGenerator) -> None:
        """Deribit futures should use BTC-DDMMMYY format."""
        instruments = gen.generate_cefi_futures(REF_DATE)
        deribit = [i for i in instruments if i.venue == "DERIBIT"]
        assert len(deribit) >= 2
        for inst in deribit:
            # e.g. BTC-28MAR25
            assert re.match(r"^BTC-\d{1,2}[A-Z]{3}\d{2}$", inst.symbol), inst.symbol

    def test_cme_naming(self, gen: InstrumentGenerator) -> None:
        """CME futures should use ES{MONTH_CODE}{YY} format."""
        instruments = gen.generate_cefi_futures(REF_DATE)
        cme = [i for i in instruments if i.venue == "CME"]
        assert len(cme) >= 2
        for inst in cme:
            # e.g. ESH25, ESM25
            assert re.match(r"^ES[HMUZ]\d{2}$", inst.symbol), inst.symbol

    def test_expiries_are_quarterly(self, gen: InstrumentGenerator) -> None:
        """All expiry months should be Mar/Jun/Sep/Dec."""
        instruments = gen.generate_cefi_futures(REF_DATE)
        for inst in instruments:
            assert inst.expiry is not None
            assert inst.expiry.month in {3, 6, 9, 12}

    def test_available_from_before_expiry(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_futures(REF_DATE)
        for inst in instruments:
            assert inst.available_from_datetime is not None
            assert inst.expiry is not None
            assert inst.available_from_datetime < inst.expiry

    def test_instrument_type_is_future(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_cefi_futures(REF_DATE)
        for inst in instruments:
            assert inst.instrument_type == InstrumentType.FUTURE


# ---------------------------------------------------------------------------
# Options Chain
# ---------------------------------------------------------------------------


class TestOptionsChain:
    def test_returns_valid_instruments(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_options_chain(REF_DATE)
        _assert_valid_instruments(instruments)

    def test_reasonable_count(self, gen: InstrumentGenerator) -> None:
        """Options chain should produce 200-2000 instruments."""
        instruments = gen.generate_options_chain(REF_DATE)
        assert 200 <= len(instruments) <= 2000

    def test_both_calls_and_puts(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_options_chain(REF_DATE)
        calls = [i for i in instruments if i.option_type == OptionType.CALL]
        puts = [i for i in instruments if i.option_type == OptionType.PUT]
        assert len(calls) > 0
        assert len(puts) > 0
        # Equal number of calls and puts
        assert len(calls) == len(puts)

    def test_expiries_in_order(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_options_chain(REF_DATE)
        expiries = sorted({i.expiry for i in instruments if i.expiry is not None})
        assert len(expiries) >= 4  # At least weeklies
        # All expiries should be after ref_date
        ref_dt = datetime(REF_DATE.year, REF_DATE.month, REF_DATE.day, tzinfo=UTC)
        for exp in expiries:
            assert exp > ref_dt

    def test_strike_range(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_options_chain(REF_DATE)
        strikes = sorted({i.strike for i in instruments if i.strike is not None})
        assert len(strikes) >= 20
        # Strikes should be at $500 intervals
        for i in range(1, len(strikes)):
            assert strikes[i] - strikes[i - 1] == 500.0

    def test_deribit_naming(self, gen: InstrumentGenerator) -> None:
        """Options should use BTC-DDMMMYY-STRIKE-C|P format."""
        instruments = gen.generate_options_chain(REF_DATE)
        for inst in instruments[:10]:
            assert re.match(r"^BTC-\d{1,2}[A-Z]{3}\d{2}-\d+-[CP]$", inst.symbol), inst.symbol

    def test_option_fields_set(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_options_chain(REF_DATE)
        for inst in instruments:
            assert inst.strike is not None
            assert inst.option_type is not None
            assert inst.expiry is not None
            assert inst.underlying == "BTC"
            assert inst.instrument_type == InstrumentType.OPTION


# ---------------------------------------------------------------------------
# TradFi
# ---------------------------------------------------------------------------


class TestTradfi:
    def test_returns_valid_instruments(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_tradfi(REF_DATE)
        _assert_valid_instruments(instruments)

    def test_expected_venues(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_tradfi(REF_DATE)
        venues = {i.venue for i in instruments}
        assert "NASDAQ" in venues
        assert "NYSE" in venues
        assert "CME" in venues
        assert "CBOE" in venues
        assert "ICE" in venues

    def test_has_trading_hours(self, gen: InstrumentGenerator) -> None:
        """Non-futures TradFi instruments should have trading hours."""
        instruments = gen.generate_tradfi(REF_DATE)
        non_futures = [i for i in instruments if i.instrument_type != InstrumentType.FUTURE]
        for inst in non_futures:
            assert inst.trading_hours_open is not None
            assert inst.trading_hours_close is not None

    def test_has_holiday_calendar(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_tradfi(REF_DATE)
        non_futures = [i for i in instruments if i.instrument_type != InstrumentType.FUTURE]
        for inst in non_futures:
            assert inst.holiday_calendar is not None

    def test_instrument_types(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_tradfi(REF_DATE)
        types = {i.instrument_type for i in instruments}
        assert InstrumentType.EQUITY in types
        assert InstrumentType.ETF in types
        assert InstrumentType.INDEX in types
        assert InstrumentType.FUTURE in types


# ---------------------------------------------------------------------------
# ICE Futures
# ---------------------------------------------------------------------------


class TestIceFutures:
    def test_ice_instruments_present(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_tradfi(REF_DATE)
        ice = [i for i in instruments if i.venue == "ICE"]
        assert len(ice) >= 4  # at least 2 roots x 2 expiries (3 expiries x 2 = 6)

    def test_ice_instrument_type_is_future(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_tradfi(REF_DATE)
        ice = [i for i in instruments if i.venue == "ICE"]
        for inst in ice:
            assert inst.instrument_type == InstrumentType.FUTURE

    def test_ice_naming_convention(self, gen: InstrumentGenerator) -> None:
        """ICE futures should use ZB/ZN + month code + YY format."""
        instruments = gen.generate_tradfi(REF_DATE)
        ice = [i for i in instruments if i.venue == "ICE"]
        for inst in ice:
            # e.g. ZBH25, ZNM25, ZBU25
            assert re.match(r"^Z[BN][HMUZ]\d{2}$", inst.symbol), inst.symbol

    def test_ice_has_both_roots(self, gen: InstrumentGenerator) -> None:
        """ICE should include both ZB (Treasury Bond) and ZN (T-Note) roots."""
        instruments = gen.generate_tradfi(REF_DATE)
        ice = [i for i in instruments if i.venue == "ICE"]
        roots = {inst.symbol[:2] for inst in ice}
        assert "ZB" in roots
        assert "ZN" in roots

    def test_ice_expiries_are_quarterly(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_tradfi(REF_DATE)
        ice = [i for i in instruments if i.venue == "ICE"]
        for inst in ice:
            assert inst.expiry is not None
            assert inst.expiry.month in {3, 6, 9, 12}

    def test_ice_expiries_in_future(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_tradfi(REF_DATE)
        ice = [i for i in instruments if i.venue == "ICE"]
        ref_dt = datetime(REF_DATE.year, REF_DATE.month, REF_DATE.day, tzinfo=UTC)
        for inst in ice:
            assert inst.expiry is not None
            assert inst.expiry > ref_dt

    def test_ice_contract_size(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_tradfi(REF_DATE)
        ice = [i for i in instruments if i.venue == "ICE"]
        for inst in ice:
            assert inst.contract_size is not None
            assert inst.contract_size == 1000.0

    def test_ice_tick_size(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_tradfi(REF_DATE)
        ice = [i for i in instruments if i.venue == "ICE"]
        zb = [i for i in ice if i.symbol.startswith("ZB")]
        zn = [i for i in ice if i.symbol.startswith("ZN")]
        for inst in zb:
            assert inst.tick_size == 0.03125  # 1/32
        for inst in zn:
            assert inst.tick_size == 0.015625  # 1/64

    def test_ice_asset_class(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_tradfi(REF_DATE)
        ice = [i for i in instruments if i.venue == "ICE"]
        for inst in ice:
            assert inst.asset_class == "tradfi_futures"

    def test_ice_available_from_before_expiry(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_tradfi(REF_DATE)
        ice = [i for i in instruments if i.venue == "ICE"]
        for inst in ice:
            assert inst.available_from_datetime is not None
            assert inst.expiry is not None
            assert inst.available_from_datetime < inst.expiry


# ---------------------------------------------------------------------------
# DeFi
# ---------------------------------------------------------------------------


class TestDefi:
    def test_returns_valid_instruments(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_defi(REF_DATE)
        _assert_valid_instruments(instruments)

    def test_wrapped_tokens_used(self, gen: InstrumentGenerator) -> None:
        """Aave instruments should use WETH, not ETH."""
        instruments = gen.generate_defi(REF_DATE)
        aave_a_tokens = [
            i for i in instruments if i.venue == "AAVE_V3_ETH" and i.instrument_type == InstrumentType.A_TOKEN
        ]
        eth_underlying = [i for i in aave_a_tokens if i.base_asset == "WETH"]
        assert len(eth_underlying) >= 1, "Aave aTokens should use WETH not ETH"

    def test_pool_addresses_present(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_defi(REF_DATE)
        for inst in instruments:
            assert inst.pool_address is not None
            assert inst.pool_address.startswith("0x")
            assert len(inst.pool_address) == 42  # 0x + 40 hex chars

    def test_ltv_set_for_aave(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_defi(REF_DATE)
        aave_a_tokens = [
            i for i in instruments if i.venue == "AAVE_V3_ETH" and i.instrument_type == InstrumentType.A_TOKEN
        ]
        assert len(aave_a_tokens) == 3
        for inst in aave_a_tokens:
            assert inst.ltv is not None
            assert 0 < inst.ltv < 1
            assert inst.liquidation_threshold is not None
            assert inst.liquidation_threshold > inst.ltv

    def test_uniswap_v3_fee_tier(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_defi(REF_DATE)
        uni_v3 = [i for i in instruments if i.venue == "UNISWAPV3-ETH"]
        assert len(uni_v3) == 1
        assert uni_v3[0].pool_fee_tier == "3000"

    def test_aave_debt_tokens(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_defi(REF_DATE)
        debt = [i for i in instruments if i.instrument_type == InstrumentType.DEBT_TOKEN]
        assert len(debt) == 3
        debt_syms = {i.symbol for i in debt}
        assert "variableDebtWETH" in debt_syms
        assert "variableDebtUSDC" in debt_syms
        assert "variableDebtUSDT" in debt_syms

    def test_lst_instruments(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_defi(REF_DATE)
        lst = [i for i in instruments if i.instrument_type == InstrumentType.LST]
        lst_syms = {i.symbol for i in lst}
        assert "stETH" in lst_syms
        assert "wstETH" in lst_syms
        assert "eETH" in lst_syms
        assert "weETH" in lst_syms

    def test_venues_present(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_defi(REF_DATE)
        venues = {i.venue for i in instruments}
        expected = {
            "AAVE_V3_ETH",
            "COMPOUND_V3_ETH",
            "UNISWAPV3-ETH",
            "UNISWAPV2-ETH",
            "UNISWAPV4-ETH",
            "LIDO",
            "ETHERFI",
            "MORPHO-ETHEREUM",
            "CURVE-ETH",
            "ETHENA",
            "EULER-ETH",
        }
        assert venues == expected

    def test_count(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_defi(REF_DATE)
        assert len(instruments) == 19

    def test_curve_3pool(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_defi(REF_DATE)
        curve = [i for i in instruments if i.venue == "CURVE-ETH"]
        assert len(curve) == 1
        assert curve[0].instrument_type == InstrumentType.POOL
        assert curve[0].symbol == "3pool"
        assert curve[0].pool_address is not None
        assert curve[0].pool_fee_tier is None  # Curve uses dynamic fees

    def test_ethena_instruments(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_defi(REF_DATE)
        ethena = [i for i in instruments if i.venue == "ETHENA"]
        assert len(ethena) == 2
        syms = {i.symbol for i in ethena}
        assert "USDe" in syms
        assert "sUSDe" in syms
        for inst in ethena:
            assert inst.instrument_type == InstrumentType.YIELD_BEARING
            assert inst.base_asset == "USDe"
        # sUSDe should have underlying set to USDe
        susde = next(i for i in ethena if i.symbol == "sUSDe")
        assert susde.underlying == "USDe"

    def test_euler_lending_vault(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_defi(REF_DATE)
        euler = [i for i in instruments if i.venue == "EULER-ETH"]
        assert len(euler) == 1
        assert euler[0].instrument_type == InstrumentType.POOL
        assert euler[0].symbol == "eUSDC"
        assert euler[0].base_asset == "USDC"
        assert euler[0].pool_address is not None


# ---------------------------------------------------------------------------
# Sports
# ---------------------------------------------------------------------------


class TestSports:
    def test_returns_valid_instruments(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_sports(REF_DATE)
        _assert_valid_instruments(instruments)

    def test_expected_venues(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_sports(REF_DATE)
        venues = {i.venue for i in instruments}
        assert "POLYMARKET" in venues
        assert "BETFAIR" in venues
        assert "PINNACLE" in venues

    def test_instrument_types(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_sports(REF_DATE)
        types = {i.instrument_type for i in instruments}
        assert InstrumentType.PREDICTION_MARKET in types
        assert InstrumentType.EXCHANGE_ODDS in types
        assert InstrumentType.FIXED_ODDS in types

    def test_polymarket_has_real_condition_ids(self, gen: InstrumentGenerator) -> None:
        """Polymarket instruments use real condition_ids from VCR cassettes."""
        instruments = gen.generate_sports(REF_DATE)
        poly = [i for i in instruments if i.venue == "POLYMARKET"]
        assert len(poly) == 2
        for inst in poly:
            assert inst.pool_id is not None
            assert inst.pool_id.startswith("0x")
            # Real condition_ids are 0x + 64 hex chars
            assert len(inst.pool_id) == 66

        # Verify specific real condition_ids from gamma_events_cassette.json
        condition_ids = {inst.pool_id for inst in poly}
        assert "0x064d33e3f5703792aafa92bfb0ee10e08f461b1b34c02c1f02671892ede1609a" in condition_ids
        assert "0x8e0c65676f129764a604fcf618b4f92c34e5dfd2ce4a4cbf7a6bcdfa942241af" in condition_ids

    def test_polymarket_nba_market(self, gen: InstrumentGenerator) -> None:
        """NBA spread market uses real DAL-MEM data."""
        instruments = gen.generate_sports(REF_DATE)
        nba = [i for i in instruments if "DAL-MEM" in i.symbol]
        assert len(nba) == 1
        assert nba[0].symbol == "NBA-DAL-MEM-SPREAD-5.5"
        assert nba[0].asset_class == "prediction"
        assert nba[0].available_to_datetime is not None

    def test_polymarket_nfl_market(self, gen: InstrumentGenerator) -> None:
        """NFL spread market uses real ATL-CAR data."""
        instruments = gen.generate_sports(REF_DATE)
        nfl = [i for i in instruments if "ATL-CAR" in i.symbol]
        assert len(nfl) == 1
        assert nfl[0].symbol == "NFL-ATL-CAR-SPREAD-3.5"
        assert nfl[0].asset_class == "prediction"

    def test_count(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_sports(REF_DATE)
        assert len(instruments) == 4


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_seed_same_instruments(self) -> None:
        gen1 = InstrumentGenerator(seed=42)
        gen2 = InstrumentGenerator(seed=42)
        d = REF_DATE

        inst1 = gen1.generate_all(d)
        inst2 = gen2.generate_all(d)

        assert len(inst1) == len(inst2)
        for a, b in zip(inst1, inst2, strict=True):
            assert a.instrument_key == b.instrument_key
            assert a.symbol == b.symbol

    def test_different_seed_different_addresses(self) -> None:
        gen1 = InstrumentGenerator(seed=42)
        gen2 = InstrumentGenerator(seed=99)
        d = REF_DATE

        defi1 = gen1.generate_defi(d)
        defi2 = gen2.generate_defi(d)

        # Pool addresses should differ with different seeds
        addrs1 = {i.pool_address for i in defi1 if i.pool_address}
        addrs2 = {i.pool_address for i in defi2 if i.pool_address}
        assert addrs1 != addrs2

    def test_deterministic_defi_addresses(self) -> None:
        gen1 = InstrumentGenerator(seed=42)
        gen2 = InstrumentGenerator(seed=42)
        d = REF_DATE

        defi1 = gen1.generate_defi(d)
        defi2 = gen2.generate_defi(d)

        for a, b in zip(defi1, defi2, strict=True):
            assert a.pool_address == b.pool_address


# ---------------------------------------------------------------------------
# generate_all
# ---------------------------------------------------------------------------


class TestGenerateAll:
    def test_returns_valid_instruments(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_all(REF_DATE)
        _assert_valid_instruments(instruments)

    def test_includes_all_categories(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_all(REF_DATE)
        types = {i.instrument_type for i in instruments}
        assert InstrumentType.SPOT_PAIR in types
        assert InstrumentType.PERPETUAL in types
        assert InstrumentType.FUTURE in types
        assert InstrumentType.OPTION in types
        assert InstrumentType.A_TOKEN in types
        assert InstrumentType.POOL in types
        assert InstrumentType.LST in types

    def test_without_options_chain(self, gen: InstrumentGenerator) -> None:
        with_opts = gen.generate_all(REF_DATE, include_options_chain=True)
        without_opts = gen.generate_all(REF_DATE, include_options_chain=False)
        assert len(with_opts) > len(without_opts)
        # Without options, should have no OPTION type
        types_without = {i.instrument_type for i in without_opts}
        assert InstrumentType.OPTION not in types_without

    def test_unique_keys(self, gen: InstrumentGenerator) -> None:
        """All instrument_key values should be unique."""
        instruments = gen.generate_all(REF_DATE)
        keys = [i.instrument_key for i in instruments]
        assert len(keys) == len(set(keys)), "Duplicate instrument_key found"

    def test_all_instruments_are_canonical(self, gen: InstrumentGenerator) -> None:
        instruments = gen.generate_all(REF_DATE)
        for inst in instruments:
            assert isinstance(inst, CanonicalInstrument)

    def test_key_format_compliance(self, gen: InstrumentGenerator) -> None:
        """All keys must be VENUE:INSTRUMENT_TYPE:SYMBOL."""
        instruments = gen.generate_all(REF_DATE)
        for inst in instruments:
            parts = inst.instrument_key.split(":")
            assert len(parts) == 3, f"Bad key: {inst.instrument_key}"
            venue_part, type_part, symbol_part = parts
            assert len(venue_part) > 0
            assert len(type_part) > 0
            assert len(symbol_part) > 0

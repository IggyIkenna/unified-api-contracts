"""Tests to close coverage gaps — domain infrastructure modules.

Covers:
- unified_api_contracts.internal/domain/instruments/__init__.py (SchemaDefinition + helpers)
- unified_api_contracts.internal/domain/market_data_processing/adapter_models.py
  (CandleOutput, InstrumentInfo, InstrumentMetadata)
- unified_api_contracts.internal/domain/market_data_processing/candle_schema.py (MarketState, DataType)
- unified_api_contracts.internal/domain/ml_inference_service/cascade_prediction.py (dataclasses)
- unified_api_contracts.internal/domain/ml_inference_service/__init__.py (re-exports)
- unified_api_contracts.internal/reference/instrument_key.py (InstrumentKey, parse_for_tardis)
- unified_api_contracts.internal/reference/instrument_definition.py (short-month option branch)
- unified_api_contracts.internal/ml.py (HyperparameterConfig.to_dict, from_dict)
- unified_api_contracts.internal/domain/market_tick_data/sports.py
- unified_api_contracts.internal/connectivity/websocket_lifecycle.py

Split from test_coverage_gaps.py to stay under the 900-line QG limit.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pandas as pd
import polars as pl
import pytest

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# domain/instruments/__init__.py
# ---------------------------------------------------------------------------


class TestInstrumentsDomain:
    def test_instruments_schema_name(self) -> None:
        from unified_api_contracts.internal.domain.instruments import INSTRUMENTS_SCHEMA

        assert INSTRUMENTS_SCHEMA.name == "instruments"
        col_names = [c.name for c in INSTRUMENTS_SCHEMA.columns]
        assert "instrument_key" in col_names
        assert "venue" in col_names

    def test_get_instruments_schema(self) -> None:
        from unified_api_contracts.internal.domain.instruments import (
            INSTRUMENTS_SCHEMA,
            get_instruments_schema,
        )

        assert get_instruments_schema() is INSTRUMENTS_SCHEMA

    def test_get_required_columns(self) -> None:
        from unified_api_contracts.internal.domain.instruments import get_required_columns

        required = get_required_columns()
        assert "instrument_key" in required
        assert "venue" in required
        assert "available_from_datetime" in required

    def test_get_optional_columns(self) -> None:
        from unified_api_contracts.internal.domain.instruments import get_optional_columns

        optional = get_optional_columns()
        assert "tardis_exchange" in optional
        assert "base_asset" in optional

    def test_get_column_info_found(self) -> None:
        from unified_api_contracts.internal.domain.instruments import get_column_info

        info = get_column_info("instrument_key")
        assert info is not None
        assert info["name"] == "instrument_key"
        assert info["type"] == "string"

    def test_get_column_info_not_found(self) -> None:
        from unified_api_contracts.internal.domain.instruments import get_column_info

        info = get_column_info("nonexistent_column")
        assert info is None

    def test_validate_schema_compliance_all_required_present(self) -> None:
        from unified_api_contracts.internal.domain.instruments import (
            get_required_columns,
            validate_schema_compliance,
        )

        required = get_required_columns()
        ok, missing = validate_schema_compliance(required)
        assert ok is True
        assert missing == []

    def test_validate_schema_compliance_missing_required(self) -> None:
        from unified_api_contracts.internal.domain.instruments import validate_schema_compliance

        ok, missing = validate_schema_compliance(["venue"])
        assert ok is False
        assert len(missing) > 0
        assert "instrument_key" in missing or len(missing) > 0

    def test_get_schema_summary(self) -> None:
        from unified_api_contracts.internal.domain.instruments import get_schema_summary

        summary = get_schema_summary()
        assert isinstance(summary["total_fields"], int)
        assert summary["total_fields"] > 0
        assert "required_column_names" in summary
        assert "metadata" in summary

    def test_instruments_parquet_schema(self) -> None:
        from unified_api_contracts.internal.domain.instruments import INSTRUMENTS_PARQUET_SCHEMA

        assert len(INSTRUMENTS_PARQUET_SCHEMA) > 10
        names = [str(c["name"]) for c in INSTRUMENTS_PARQUET_SCHEMA]
        assert "instrument_key" in names

    def test_schema_metadata(self) -> None:
        from unified_api_contracts.internal.domain.instruments import SCHEMA_METADATA

        assert "version" in SCHEMA_METADATA
        assert SCHEMA_METADATA["storage_format"] == "Parquet"

    def test_nullable_override_tradfi(self) -> None:
        from unified_api_contracts.internal.domain.instruments import INSTRUMENTS_SCHEMA

        # databento_symbol: nullable=True but TRADFI override = False
        result = INSTRUMENTS_SCHEMA.is_nullable("databento_symbol", {"asset_group": "TRADFI"})
        assert result is False
        result2 = INSTRUMENTS_SCHEMA.is_nullable("databento_symbol", {"asset_group": "CEFI"})
        assert result2 is True

    def test_all_exports(self) -> None:
        import unified_api_contracts.internal.domain.instruments as m
        from unified_api_contracts.internal.domain.instruments import __all__

        for name in __all__:
            assert hasattr(m, name)


# ---------------------------------------------------------------------------
# domain/market_data_processing/adapter_models.py
# ---------------------------------------------------------------------------


class TestAdapterModels:
    def test_instrument_info_properties(self) -> None:
        from unified_api_contracts.internal.domain.market_data_processing.adapter_models import (
            InstrumentInfo,
        )

        info = InstrumentInfo(
            instrument_id="BINANCE:SPOT:BTCUSDT",
            venue="BINANCE",
            symbol="BTCUSDT",
        )
        assert info.instrument_id == "BINANCE:SPOT:BTCUSDT"
        assert info.venue == "BINANCE"
        assert info.symbol == "BTCUSDT"

    def test_instrument_metadata_properties_present(self) -> None:
        from unified_api_contracts.internal.domain.market_data_processing.adapter_models import (
            InstrumentMetadata,
        )

        meta = InstrumentMetadata(
            trading_hours_open="09:30",
            trading_hours_close="16:00",
            holiday_calendar=["2024-12-25", "2025-01-01"],
        )
        assert meta.trading_hours_open == "09:30"
        assert meta.trading_hours_close == "16:00"
        assert meta.holiday_calendar == ["2024-12-25", "2025-01-01"]

    def test_instrument_metadata_properties_absent(self) -> None:
        from unified_api_contracts.internal.domain.market_data_processing.adapter_models import (
            InstrumentMetadata,
        )

        meta = InstrumentMetadata()
        assert meta.trading_hours_open is None
        assert meta.trading_hours_close is None
        assert meta.holiday_calendar is None

    def test_instrument_metadata_holiday_not_a_list(self) -> None:
        from unified_api_contracts.internal.domain.market_data_processing.adapter_models import (
            InstrumentMetadata,
        )

        # When holiday_calendar is set to a non-list value, returns None
        meta = InstrumentMetadata(holiday_calendar="not-a-list")
        assert meta.holiday_calendar is None

    def test_candle_output_empty(self) -> None:
        from unified_api_contracts.internal.domain.market_data_processing.adapter_models import (
            CandleOutput,
        )

        co = CandleOutput()
        df = co.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_candle_output_with_arrays(self) -> None:
        from unified_api_contracts.internal.domain.market_data_processing.adapter_models import (
            CandleOutput,
        )

        ts = [1_000_000_000, 2_000_000_000]
        co = CandleOutput(
            timestamp=ts,
            venue=["BINANCE", "BINANCE"],
            symbol=["BTCUSDT", "BTCUSDT"],
            instrument_id=["BINANCE:SPOT:BTCUSDT", "BINANCE:SPOT:BTCUSDT"],
            open=[50000.0, 50100.0],
            high=[50200.0, 50300.0],
            low=[49900.0, 50000.0],
            close=[50100.0, 50200.0],
            volume=[100.0, 120.0],
        )
        df = co.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert "timestamp" in df.columns
        assert "open" in df.columns
        assert len(df) == 2

    def test_candle_output_to_polars_empty(self) -> None:
        from unified_api_contracts.internal.domain.market_data_processing.adapter_models import (
            CandleOutput,
        )

        co = CandleOutput()
        df = co.to_polars()
        assert isinstance(df, pl.DataFrame)
        assert df.is_empty()

    def test_candle_output_to_polars_with_arrays(self) -> None:
        from unified_api_contracts.internal.domain.market_data_processing.adapter_models import (
            CandleOutput,
        )

        ts = [1_000_000_000, 2_000_000_000]
        co = CandleOutput(
            timestamp=ts,
            venue=["BINANCE", "BINANCE"],
            symbol=["BTCUSDT", "BTCUSDT"],
            instrument_id=["BINANCE:SPOT:BTCUSDT", "BINANCE:SPOT:BTCUSDT"],
            open=[50000.0, 50100.0],
            high=[50200.0, 50300.0],
            low=[49900.0, 50000.0],
            close=[50100.0, 50200.0],
            volume=[100.0, 120.0],
        )
        df = co.to_polars()
        assert isinstance(df, pl.DataFrame)
        assert "timestamp" in df.columns
        assert "open" in df.columns
        assert df.height == 2

    def test_all_exports(self) -> None:
        import unified_api_contracts.internal.domain.market_data_processing.adapter_models as m

        for name in m.__all__:
            assert hasattr(m, name)


# ---------------------------------------------------------------------------
# domain/market_data_processing/candle_schema.py
# ---------------------------------------------------------------------------


class TestCandleSchema:
    def test_market_state_values(self) -> None:
        from unified_api_contracts.internal.domain.market_data_processing.candle_schema import (
            MarketState,
        )

        assert MarketState.NORMAL == "normal"
        assert MarketState.HALTED == "halted"
        assert MarketState.AUCTION == "auction"
        assert MarketState.PRE_MARKET == "pre_market"
        assert MarketState.POST_MARKET == "post_market"
        assert MarketState.CLOSED == "closed"

    def test_data_type_values(self) -> None:
        from unified_api_contracts.internal.domain.market_data_processing.candle_schema import DataType

        assert DataType.TRADES == "trades"
        assert DataType.BOOK_SNAPSHOT_5 == "book_snapshot_5"
        assert DataType.DERIVATIVE_TICKER == "derivative_ticker"
        assert DataType.LIQUIDATIONS == "liquidations"
        assert DataType.SPORTS_ARBITRAGE == "sports_arbitrage"
        assert DataType.SPORTS_ODDS_SNAPSHOT == "sports_odds_snapshot"
        assert DataType.SPORTS_ODDS_MOVEMENT == "sports_odds_movement"

    def test_data_type_str_enum(self) -> None:
        from unified_api_contracts.internal.domain.market_data_processing.candle_schema import DataType

        # StrEnum means string comparison works
        assert DataType.TRADES == "trades"

    def test_solana_basis_mvp_data_types(self) -> None:
        """plans/active/solana_basis_trading_mvp_2026_06_01.md — Phase 1+2 scope.

        Asserts that the closed-set DataType enum declares the seven new types
        required by the Solana basis-trading MVP (Drift V2 perp ground-truth
        types + Solana spot-DEX time-series state types). These are referenced
        by ``DriftV2HistoricalIngester`` (MTDS) + the Phase-2 Orca / Raydium /
        Phoenix / Jupiter ingesters; flipping any of these to a different
        string is a wire-format break.
        """
        from unified_api_contracts.internal.domain.market_data_processing.candle_schema import DataType

        # Drift V2 perp ground-truth (Phase 1)
        assert DataType.PERP_TRADES == "perp_trades"
        assert DataType.PERP_MARK_ORACLE == "perp_mark_oracle"
        assert DataType.PERP_OPEN_INTEREST == "perp_open_interest"
        # Spot DEX time-series state (Phase 2)
        assert DataType.DEX_POOL_STATE == "dex_pool_state"
        assert DataType.DEX_ORDERBOOK == "dex_orderbook"
        assert DataType.DEX_QUOTE == "dex_quote"
        assert DataType.DEX_TRADES == "dex_trades"
        # Sanity: pre-existing perp_funding remains unchanged
        assert DataType.PERP_FUNDING == "perp_funding"
        # Sanity: pre-existing dex_pools snapshot type is distinct from
        # the new dex_pool_state time-series type
        assert DataType.DEX_POOLS == "dex_pools"
        assert DataType.DEX_POOLS != DataType.DEX_POOL_STATE

    def test_all_exports(self) -> None:
        import unified_api_contracts.internal.domain.market_data_processing.candle_schema as m

        for name in m.__all__:
            assert hasattr(m, name)


# ---------------------------------------------------------------------------
# domain/ml_inference_service/cascade_prediction.py
# ---------------------------------------------------------------------------


class TestCascadePrediction:
    def test_prediction_snapshot(self) -> None:
        from unified_api_contracts.internal.domain.ml_inference_service.cascade_prediction import (
            PredictionSnapshot,
        )

        snap = PredictionSnapshot(
            instrument_id="BTC-USDT",
            timeframe="1h",
            direction=1,
            confidence=0.75,
            model_id="lgbm_v1",
            predicted_at=datetime.now(UTC),
        )
        assert snap.direction == 1
        assert snap.confidence == 0.75

    def test_cascade_config(self) -> None:
        from unified_api_contracts.internal.domain.ml_inference_service.cascade_prediction import (
            CascadeConfig,
        )

        cfg = CascadeConfig(
            profile_name="momentum_cascade",
            trigger_timeframe="1h",
            context_timeframes=["1d", "4h"],
            entry_timeframes=["15m", "5m"],
            confidence_threshold=0.65,
            require_context_alignment=True,
        )
        assert cfg.profile_name == "momentum_cascade"
        assert cfg.confidence_threshold == 0.65

    def test_cascade_config_defaults(self) -> None:
        from unified_api_contracts.internal.domain.ml_inference_service.cascade_prediction import (
            CascadeConfig,
        )

        cfg = CascadeConfig(
            profile_name="simple",
            trigger_timeframe="1h",
            context_timeframes=["1d"],
            entry_timeframes=["5m"],
        )
        assert cfg.confidence_threshold == 0.6
        assert cfg.require_context_alignment is True

    def test_cascade_prediction_event(self) -> None:
        from unified_api_contracts.internal.domain.ml_inference_service.cascade_prediction import (
            CascadePredictionEvent,
            PredictionSnapshot,
        )

        snap = PredictionSnapshot(
            instrument_id="BTC-USDT",
            timeframe="1d",
            direction=1,
            confidence=0.8,
            model_id="lgbm_v1",
            predicted_at=datetime.now(UTC),
        )
        evt = CascadePredictionEvent(
            instrument_id="BTC-USDT",
            profile_name="momentum_cascade",
            trigger_timeframe="1h",
            trigger_direction=1,
            trigger_confidence=0.72,
            context={"1d": snap},
            cascade_confidence_score=0.78,
            cascade_aligned=True,
            recommended_entry_timeframes=["15m", "5m"],
        )
        assert evt.cascade_aligned is True
        assert evt.cascade_confidence_score == 0.78
        # published_at auto-populated
        assert isinstance(evt.published_at, datetime)

    def test_cascade_prediction_event_explicit_published_at(self) -> None:
        from unified_api_contracts.internal.domain.ml_inference_service.cascade_prediction import (
            CascadePredictionEvent,
            PredictionSnapshot,
        )

        snap = PredictionSnapshot(
            instrument_id="BTC-USDT",
            timeframe="1d",
            direction=-1,
            confidence=0.7,
            model_id="m1",
            predicted_at=datetime.now(UTC),
        )
        ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        evt = CascadePredictionEvent(
            instrument_id="BTC-USDT",
            profile_name="p",
            trigger_timeframe="1h",
            trigger_direction=-1,
            trigger_confidence=0.65,
            context={"1d": snap},
            cascade_confidence_score=0.68,
            cascade_aligned=False,
            recommended_entry_timeframes=["5m"],
            published_at=ts,
        )
        assert evt.published_at == ts


# ---------------------------------------------------------------------------
# domain/ml_inference_service/__init__.py
# ---------------------------------------------------------------------------


class TestMlInferenceServiceInit:
    def test_re_exports_importable(self) -> None:
        from unified_api_contracts.internal.domain.ml_inference_service import (
            CascadeConfig,
            CascadePredictionEvent,
            PredictionSnapshot,
        )

        assert CascadeConfig is not None
        assert CascadePredictionEvent is not None
        assert PredictionSnapshot is not None


# ---------------------------------------------------------------------------
# reference/instrument_key.py
# ---------------------------------------------------------------------------


class TestInstrumentKey:
    def test_from_string_three_parts(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        key = InstrumentKey.from_string("BINANCE-FUTURES:PERPETUAL:BTC-USDT")
        assert key.venue == "BINANCE-FUTURES"
        assert key.instrument_type == "PERPETUAL"
        assert key.symbol == "BTC-USDT"
        assert key.expiry is None
        assert key.option_type is None

    def test_from_string_with_expiry(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        key = InstrumentKey.from_string("DERIBIT:FUTURE:ETH-USDC:250328")
        assert key.expiry == "250328"
        assert key.option_type is None

    def test_from_string_with_expiry_and_option_type(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        key = InstrumentKey.from_string("DERIBIT:OPTION:ETH-USDC:250328:C")
        assert key.expiry == "250328"
        assert key.option_type == "C"

    def test_from_string_invalid_raises(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        with pytest.raises(ValueError, match="Invalid instrument key format"):
            InstrumentKey.from_string("BINANCE")

    def test_str_three_parts(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        key = InstrumentKey(venue="BINANCE-FUTURES", instrument_type="PERPETUAL", symbol="BTC-USDT")
        assert str(key) == "BINANCE-FUTURES:PERPETUAL:BTC-USDT"

    def test_str_with_expiry(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        key = InstrumentKey(venue="DERIBIT", instrument_type="FUTURE", symbol="ETH-USDC", expiry="250328")
        assert str(key) == "DERIBIT:FUTURE:ETH-USDC:250328"

    def test_str_with_expiry_and_option_type(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        key = InstrumentKey(
            venue="DERIBIT",
            instrument_type="OPTION",
            symbol="ETH-USDC",
            expiry="250328",
            option_type="C",
        )
        assert str(key) == "DERIBIT:OPTION:ETH-USDC:250328:C"

    def test_parse_for_tardis_binance_futures(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        result = InstrumentKey.parse_for_tardis("BINANCE-FUTURES:PERPETUAL:BTC-USDT")
        assert result["venue"] == "BINANCE-FUTURES"
        assert result["tardis_exchange"] == "binance-futures"
        assert result["tardis_symbol"] == "btcusdt"

    def test_parse_for_tardis_binance_spot(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        result = InstrumentKey.parse_for_tardis("BINANCE-SPOT:SPOT:BTC-USDT")
        assert result["tardis_exchange"] == "binance"
        assert result["tardis_symbol"] == "btcusdt"

    def test_parse_for_tardis_deribit(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        result = InstrumentKey.parse_for_tardis("DERIBIT:OPTION:BTC-USD-250328-50000-C")
        assert result["tardis_exchange"] == "deribit"
        # deribit: symbol.lower()
        assert result["tardis_symbol"] == "btc-usd-250328-50000-c"

    def test_parse_for_tardis_upbit(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        result = InstrumentKey.parse_for_tardis("UPBIT:SPOT:KRW-BTC")
        assert result["tardis_exchange"] == "upbit"
        assert result["tardis_symbol"] == "BTC-KRW"

    def test_parse_for_tardis_coinbase(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        result = InstrumentKey.parse_for_tardis("COINBASE:SPOT:BTC-USD")
        assert result["tardis_exchange"] == "coinbase"
        assert result["tardis_symbol"] == "BTC-USD"

    def test_parse_for_tardis_unknown_venue(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        result = InstrumentKey.parse_for_tardis("OKX:SPOT:BTC-USDT")
        assert result["tardis_exchange"] == "okex"

    def test_parse_for_tardis_completely_unknown_venue(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        result = InstrumentKey.parse_for_tardis("MYEXCHANGE:SPOT:BTC-USD")
        # Falls back to venue.lower()
        assert result["tardis_exchange"] == "myexchange"
        # default branch: symbol.lower()
        assert result["tardis_symbol"] == "btc-usd"

    def test_parse_for_tardis_invalid_raises(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        with pytest.raises(ValueError, match="Invalid instrument key format"):
            InstrumentKey.parse_for_tardis("BINANCE")

    def test_upbit_symbol_not_two_parts(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        # Symbol with only 1 part — fallback keeps original
        result = InstrumentKey.parse_for_tardis("UPBIT:SPOT:BTC")
        assert result["tardis_exchange"] == "upbit"
        assert result["tardis_symbol"] == "BTC"

    def test_bybit_venue(self) -> None:
        from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

        result = InstrumentKey.parse_for_tardis("BYBIT:PERPETUAL:BTC-USDT")
        assert result["tardis_exchange"] == "bybit"


# ---------------------------------------------------------------------------
# reference/instrument_definition.py — lines 224-226 (_OPTION_SHORT_RE branch)
# ---------------------------------------------------------------------------


class TestInstrumentDefinitionShortMonth:
    def test_option_short_month_format_call(self) -> None:
        """_OPTION_SHORT_RE branch: date in short-month format (e.g. 27MAR25)."""
        from unified_api_contracts.internal.reference.instrument_definition import InstrumentDefinition

        inst = InstrumentDefinition(
            instrument_key="deribit:option:ETH-USD-27MAR25-3500-C",
            venue="deribit",
            instrument_type="OPTION",
            symbol="ETH-USD-27MAR25-3500-C",
            available_from_datetime="2025-01-01T00:00:00Z",
        )
        # _OPTION_LONG_RE won't match (no 6-digit date), _OPTION_SHORT_RE will
        assert inst.strike == "3500"
        assert inst.option_type == "CALL"

    def test_option_short_month_format_put(self) -> None:
        """_OPTION_SHORT_RE branch with PUT."""
        from unified_api_contracts.internal.reference.instrument_definition import InstrumentDefinition

        inst = InstrumentDefinition(
            instrument_key="deribit:option:BTC-USD-28JUN25-60000-P",
            venue="deribit",
            instrument_type="OPTION",
            symbol="BTC-USD-28JUN25-60000-P",
            available_from_datetime="2025-01-01T00:00:00Z",
        )
        assert inst.strike == "60000"
        assert inst.option_type == "PUT"


# ---------------------------------------------------------------------------
# ml.py — lines 60, 65-66 (HyperparameterConfig.to_dict, from_dict)
# ---------------------------------------------------------------------------


class TestMlHyperparameterConfig:
    def test_to_dict(self) -> None:
        from unified_api_contracts.internal.ml import HyperparameterConfig

        cfg = HyperparameterConfig(num_leaves=64, learning_rate=0.1)
        d = cfg.to_dict()
        assert d["num_leaves"] == 64
        assert d["learning_rate"] == 0.1

    def test_from_dict_known_keys(self) -> None:
        from unified_api_contracts.internal.ml import HyperparameterConfig

        cfg = HyperparameterConfig.from_dict({"num_leaves": 128, "learning_rate": 0.05})
        assert cfg.num_leaves == 128

    def test_from_dict_unknown_keys_ignored(self) -> None:
        from unified_api_contracts.internal.ml import HyperparameterConfig

        cfg = HyperparameterConfig.from_dict({"num_leaves": 64, "unknown_param": "ignore_me"})
        assert cfg.num_leaves == 64

    def test_from_dict_none_values_excluded(self) -> None:
        from unified_api_contracts.internal.ml import HyperparameterConfig

        cfg = HyperparameterConfig.from_dict({"num_leaves": None, "learning_rate": 0.1})
        # None values are excluded; num_leaves falls back to default
        assert cfg.num_leaves == 31


# ---------------------------------------------------------------------------
# domain/market_tick_data/sports.py — missing lines 67-69, 75, 81, 106, 112, 118
# ---------------------------------------------------------------------------


class TestMarketTickDataSports:
    def _make_tick(self) -> object:
        from unified_api_contracts import OddsType, OutcomeType
        from unified_api_contracts.internal.domain.market_tick_data.sports import SportsOddsTick

        return SportsOddsTick(
            timestamp_utc=datetime.now(UTC),
            bookmaker_key="betfair",
            fixture_key="PL_2024_f1",
            market_type=OddsType.H2H,
            outcome=OutcomeType.HOME,
            odds_value=Decimal("2.10"),
        )

    def test_sports_odds_tick_basic(self) -> None:
        tick = self._make_tick()
        assert tick.bookmaker_key == "betfair"  # type: ignore[union-attr]
        assert tick.fixture_key == "PL_2024_f1"  # type: ignore[union-attr]

    def test_sports_odds_tick_implied_probability_nonzero(self) -> None:
        """Hits computed_field implied_probability branch: odds_value > 0."""
        tick = self._make_tick()
        prob = tick.implied_probability  # type: ignore[union-attr]
        assert Decimal("0") < prob < Decimal("1")

    def test_sports_odds_tick_implied_probability_zero_odds(self) -> None:
        """Hits computed_field implied_probability branch: odds_value == 0."""
        from unified_api_contracts import OddsType, OutcomeType
        from unified_api_contracts.internal.domain.market_tick_data.sports import SportsOddsTick

        tick = SportsOddsTick(
            timestamp_utc=datetime.now(UTC),
            bookmaker_key="betfair",
            fixture_key="PL_2024_f2",
            market_type=OddsType.H2H,
            outcome=OutcomeType.DRAW,
            odds_value=Decimal("0"),
        )
        assert tick.implied_probability == Decimal("0")

    def test_sports_odds_tick_ts_event_ns(self) -> None:
        """Hits computed_field ts_event_ns."""
        tick = self._make_tick()
        ns = tick.ts_event_ns  # type: ignore[union-attr]
        assert isinstance(ns, int)
        assert ns > 0

    def test_sports_odds_tick_instrument_key(self) -> None:
        """Hits computed_field instrument_key."""
        tick = self._make_tick()
        ik = tick.instrument_key  # type: ignore[union-attr]
        assert "betfair" in ik
        assert "PL_2024_f1" in ik

    def test_sports_odds_tick_with_volume(self) -> None:
        from unified_api_contracts import OddsType, OutcomeType
        from unified_api_contracts.internal.domain.market_tick_data.sports import SportsOddsTick

        tick = SportsOddsTick(
            timestamp_utc=datetime.now(UTC),
            bookmaker_key="betfair",
            fixture_key="PL_2024_f3",
            market_type=OddsType.H2H,
            outcome=OutcomeType.AWAY,
            odds_value=Decimal("3.50"),
            volume=Decimal("1000.00"),
            source="betfair-exchange",
        )
        assert tick.volume == Decimal("1000.00")
        assert tick.source == "betfair-exchange"

    def test_sports_book_update_computed_fields(self) -> None:
        """Hits SportsBookUpdate.ts_event_ns, bookmaker_count, outcome_count."""
        from unified_api_contracts import OddsType, OutcomeType
        from unified_api_contracts.internal.domain.market_tick_data.sports import (
            SportsBookUpdate,
            SportsOddsTick,
        )

        ts = datetime.now(UTC)
        tick_home = SportsOddsTick(
            timestamp_utc=ts,
            bookmaker_key="betfair",
            fixture_key="f4",
            market_type=OddsType.H2H,
            outcome=OutcomeType.HOME,
            odds_value=Decimal("2.00"),
        )
        tick_away = SportsOddsTick(
            timestamp_utc=ts,
            bookmaker_key="pinnacle",
            fixture_key="f4",
            market_type=OddsType.H2H,
            outcome=OutcomeType.AWAY,
            odds_value=Decimal("3.50"),
        )
        update = SportsBookUpdate(
            timestamp_utc=ts,
            fixture_key="f4",
            market_type=OddsType.H2H,
            ticks=(tick_home, tick_away),
        )
        assert update.ts_event_ns > 0
        assert update.bookmaker_count == 2
        assert update.outcome_count == 2


# ---------------------------------------------------------------------------
# connectivity/websocket_lifecycle.py — line 14 (_utc_now helper)
# ---------------------------------------------------------------------------


class TestWebSocketLifecycle:
    def test_connect_event_triggers_utc_now(self) -> None:
        """_utc_now is called by default_factory on model instantiation."""
        from unified_api_contracts.internal.connectivity.websocket_lifecycle import (
            WebSocketConnectEvent,
        )

        evt = WebSocketConnectEvent(
            venue="BINANCE-FUTURES",
            endpoint_url="wss://stream.binance.com",
            connection_id="conn-001",
        )
        assert evt.venue == "BINANCE-FUTURES"
        assert evt.timestamp.tzinfo is not None  # UTC-aware

    def test_disconnect_event(self) -> None:
        from unified_api_contracts.internal.connectivity.websocket_lifecycle import (
            WebSocketDisconnectEvent,
        )

        evt = WebSocketDisconnectEvent(
            venue="DERIBIT",
            connection_id="conn-002",
            reason="server_close",
            was_clean=True,
        )
        assert evt.was_clean is True
        assert evt.timestamp.tzinfo is not None

    def test_reconnect_event(self) -> None:
        from unified_api_contracts.internal.connectivity.websocket_lifecycle import (
            WebSocketReconnectEvent,
        )

        evt = WebSocketReconnectEvent(
            venue="DERIBIT",
            connection_id="conn-003",
            attempt_number=2,
            delay_seconds=5.0,
        )
        assert evt.attempt_number == 2
        assert evt.delay_seconds == 5.0

    def test_error_event(self) -> None:
        from unified_api_contracts.internal.connectivity.websocket_lifecycle import WebSocketErrorEvent

        evt = WebSocketErrorEvent(
            venue="OKX",
            connection_id="conn-004",
            error_code="1006",
            error_message="Abnormal closure",
        )
        assert evt.error_code == "1006"
        assert evt.error_message == "Abnormal closure"

    def test_ping_event(self) -> None:
        from unified_api_contracts.internal.connectivity.websocket_lifecycle import WebSocketPingEvent

        evt = WebSocketPingEvent(
            venue="BINANCE-FUTURES",
            connection_id="conn-005",
            ping_id="ping-42",
        )
        assert evt.ping_id == "ping-42"

    def test_pong_event(self) -> None:
        from unified_api_contracts.internal.connectivity.websocket_lifecycle import WebSocketPongEvent

        evt = WebSocketPongEvent(
            venue="BINANCE-FUTURES",
            connection_id="conn-006",
            ping_id="ping-42",
            latency_ms=3.5,
        )
        assert evt.latency_ms == 3.5

    def test_subscribe_ack_event(self) -> None:
        from unified_api_contracts.internal.connectivity.websocket_lifecycle import (
            WebSocketSubscribeAckEvent,
        )

        evt = WebSocketSubscribeAckEvent(
            venue="BINANCE-FUTURES",
            connection_id="conn-007",
            channel="trades:BTCUSDT",
            subscribed=True,
        )
        assert evt.subscribed is True
        assert evt.error_message is None

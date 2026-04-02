"""Tests to close coverage gaps — features and execution service domain modules.

Covers:
- unified_api_contracts.internal/domain/execution_service/sports.py
  (SportsBetResult, SportsVenueScore, SportsVenueSelection)
- unified_api_contracts.internal/domain/features_calendar/__init__.py
  (SchemaDefinition constants, get_schema_for_category)
- unified_api_contracts.internal/domain/features_cross_instrument/__init__.py (re-exports)
- unified_api_contracts.internal/domain/features_delta_one/__init__.py
  (FEATURES_SCHEMA, validate_feature_columns_not_null)
- unified_api_contracts.internal/domain/features_liquidity/__init__.py (Pydantic models)
- unified_api_contracts.internal/domain/features_multi_timeframe/__init__.py (re-exports)
- unified_api_contracts.internal/domain/features_onchain/__init__.py (re-exports)
- unified_api_contracts.internal/domain/features_volatility/__init__.py (SchemaDefinition constants)

Split from test_coverage_gaps.py to stay under the 900-line QG limit.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# domain/execution_service/sports.py
# ---------------------------------------------------------------------------


class TestExecutionServiceSports:
    def test_sports_bet_result_success(self) -> None:
        from unified_api_contracts import BetStatus
        from unified_api_contracts.internal.domain.execution_service.sports import SportsBetResult

        result = SportsBetResult(
            execution_id="e1",
            order_id="o1",
            bet_id="b1",
            status=BetStatus.PLACED,
            bookmaker_key="betfair",
            executed_at_utc=datetime.now(UTC),
            filled_odds=Decimal("1.95"),
            filled_stake=Decimal("100.00"),
        )
        assert result.is_success is True
        assert result.is_failed is False
        assert result.schema_version == "1.0.0"

    def test_sports_bet_result_failure(self) -> None:
        from unified_api_contracts import BetStatus
        from unified_api_contracts.internal.domain.execution_service.sports import SportsBetResult

        result = SportsBetResult(
            execution_id="e2",
            order_id="o2",
            status=BetStatus.REJECTED,
            bookmaker_key="betfair",
            executed_at_utc=datetime.now(UTC),
            error_message="Insufficient funds",
        )
        assert result.is_success is False
        assert result.is_failed is True
        assert result.bet_id is None
        assert result.error_message == "Insufficient funds"

    def test_sports_bet_result_matched(self) -> None:
        from unified_api_contracts import BetStatus
        from unified_api_contracts.internal.domain.execution_service.sports import SportsBetResult

        result = SportsBetResult(
            execution_id="e3",
            order_id="o3",
            status=BetStatus.MATCHED,
            bookmaker_key="betfair",
            executed_at_utc=datetime.now(UTC),
        )
        assert result.is_success is True

    def test_sports_bet_result_partially_matched(self) -> None:
        from unified_api_contracts import BetStatus
        from unified_api_contracts.internal.domain.execution_service.sports import SportsBetResult

        result = SportsBetResult(
            execution_id="e4",
            order_id="o4",
            status=BetStatus.PARTIALLY_MATCHED,
            bookmaker_key="betfair",
            executed_at_utc=datetime.now(UTC),
        )
        assert result.is_success is True

    def test_sports_bet_result_settled_win(self) -> None:
        from unified_api_contracts import BetStatus
        from unified_api_contracts.internal.domain.execution_service.sports import SportsBetResult

        result = SportsBetResult(
            execution_id="e5",
            order_id="o5",
            status=BetStatus.SETTLED_WIN,
            bookmaker_key="betfair",
            executed_at_utc=datetime.now(UTC),
        )
        assert result.is_success is True

    def test_sports_venue_score(self) -> None:
        from unified_api_contracts.internal.domain.execution_service.sports import SportsVenueScore

        score = SportsVenueScore(
            bookmaker_key="betfair",
            margin_score=0.9,
            liquidity_score=0.8,
            latency_score=0.7,
            total_score=0.85,
            expected_margin_pct=2.5,
            is_exchange=True,
        )
        assert score.bookmaker_key == "betfair"
        assert score.is_exchange is True

    def test_sports_venue_selection(self) -> None:
        from unified_api_contracts.internal.domain.execution_service.sports import SportsVenueSelection

        sel = SportsVenueSelection(
            bookmaker_key="pinnacle",
            fixture_id="f1",
            market="1X2",
            expected_margin_pct=3.0,
            is_exchange=False,
            reason="Best margin",
        )
        assert sel.reason == "Best margin"

    def test_sports_venue_selection_default_reason(self) -> None:
        from unified_api_contracts.internal.domain.execution_service.sports import SportsVenueSelection

        sel = SportsVenueSelection(
            bookmaker_key="pinnacle",
            fixture_id="f2",
            market="BTTS",
            expected_margin_pct=4.0,
            is_exchange=False,
        )
        assert sel.reason == ""

    def test_all_exports(self) -> None:
        import unified_api_contracts.internal.domain.execution_service.sports as m

        for name in m.__all__:
            assert hasattr(m, name)


# ---------------------------------------------------------------------------
# domain/features_calendar/__init__.py
# ---------------------------------------------------------------------------


class TestFeaturesCalendar:
    def test_time_features_schema_name(self) -> None:
        from unified_api_contracts.internal.domain.features_calendar import TIME_FEATURES_SCHEMA

        assert TIME_FEATURES_SCHEMA.name == "time_features"
        assert any(c.name == "timestamp" for c in TIME_FEATURES_SCHEMA.columns)

    def test_economic_events_schema_name(self) -> None:
        from unified_api_contracts.internal.domain.features_calendar import ECONOMIC_EVENTS_SCHEMA

        assert ECONOMIC_EVENTS_SCHEMA.name == "economic_events"
        assert any(c.name == "event_type" for c in ECONOMIC_EVENTS_SCHEMA.columns)

    def test_get_schema_for_category_time(self) -> None:
        from unified_api_contracts.internal.domain.features_calendar import get_schema_for_category

        schema = get_schema_for_category("time_features")
        assert schema is not None
        assert schema.name == "time_features"

    def test_get_schema_for_category_economic(self) -> None:
        from unified_api_contracts.internal.domain.features_calendar import get_schema_for_category

        schema = get_schema_for_category("economic_events")
        assert schema is not None

    def test_get_schema_for_category_unknown_returns_none(self) -> None:
        from unified_api_contracts.internal.domain.features_calendar import get_schema_for_category

        schema = get_schema_for_category("nonexistent")
        assert schema is None

    def test_calendar_schemas_dict(self) -> None:
        from unified_api_contracts.internal.domain.features_calendar import CALENDAR_SCHEMAS

        assert "time_features" in CALENDAR_SCHEMAS
        assert "economic_events" in CALENDAR_SCHEMAS

    def test_all_exports(self) -> None:
        import unified_api_contracts.internal.domain.features_calendar as m
        from unified_api_contracts.internal.domain.features_calendar import __all__

        for name in __all__:
            assert hasattr(m, name)


# ---------------------------------------------------------------------------
# domain/features_cross_instrument/__init__.py
# ---------------------------------------------------------------------------


class TestFeaturesCrossInstrument:
    def test_re_exports_importable(self) -> None:
        from unified_api_contracts.internal.domain.features_cross_instrument import (
            CrossInstrumentFeatures,
            PairSpreadFeatureRecord,
        )

        assert CrossInstrumentFeatures is not None
        assert PairSpreadFeatureRecord is not None

    def test_all_exports(self) -> None:
        import unified_api_contracts.internal.domain.features_cross_instrument as m
        from unified_api_contracts.internal.domain.features_cross_instrument import __all__

        for name in __all__:
            assert hasattr(m, name)


# ---------------------------------------------------------------------------
# domain/features_delta_one/__init__.py
# ---------------------------------------------------------------------------


class TestFeaturesDeltaOne:
    def test_features_schema_name(self) -> None:
        from unified_api_contracts.internal.domain.features_delta_one import FEATURES_SCHEMA

        assert FEATURES_SCHEMA.name == "features_delta_one"
        assert any(c.name == "instrument_id" for c in FEATURES_SCHEMA.columns)

    def test_feature_groups_list(self) -> None:
        from unified_api_contracts.internal.domain.features_delta_one import FEATURE_GROUPS

        assert "technical_indicators" in FEATURE_GROUPS
        assert "targets" in FEATURE_GROUPS
        assert len(FEATURE_GROUPS) > 5

    def test_get_features_schema(self) -> None:
        from unified_api_contracts.internal.domain.features_delta_one import (
            FEATURES_SCHEMA,
            get_features_schema,
        )

        assert get_features_schema() is FEATURES_SCHEMA

    def test_validate_feature_columns_not_null_all_ok(self) -> None:
        from unified_api_contracts.internal.domain.features_delta_one import (
            validate_feature_columns_not_null,
        )

        df = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        ok, errors = validate_feature_columns_not_null(df, ["a", "b"])
        assert ok is True
        assert errors == []

    def test_validate_feature_columns_not_null_with_nan(self) -> None:
        from unified_api_contracts.internal.domain.features_delta_one import (
            validate_feature_columns_not_null,
        )

        df = pd.DataFrame({"a": [1.0, float("nan")], "b": [3.0, 4.0]})
        ok, errors = validate_feature_columns_not_null(df, ["a", "b"], context="test_run")
        assert ok is False
        assert len(errors) == 1
        assert "a" in errors[0]
        assert "test_run" in errors[0]

    def test_validate_feature_columns_missing_column_skipped(self) -> None:
        from unified_api_contracts.internal.domain.features_delta_one import (
            validate_feature_columns_not_null,
        )

        df = pd.DataFrame({"a": [1.0]})
        # "ghost" not in df — should be skipped, not an error
        ok, errors = validate_feature_columns_not_null(df, ["a", "ghost"])
        assert ok is True
        assert errors == []

    def test_validate_feature_columns_no_context(self) -> None:
        from unified_api_contracts.internal.domain.features_delta_one import (
            validate_feature_columns_not_null,
        )

        df = pd.DataFrame({"a": [float("nan")]})
        ok, errors = validate_feature_columns_not_null(df, ["a"])
        assert ok is False
        # No "(context)" suffix when context is empty
        assert "()" not in errors[0]

    def test_all_exports(self) -> None:
        import unified_api_contracts.internal.domain.features_delta_one as m
        from unified_api_contracts.internal.domain.features_delta_one import __all__

        for name in __all__:
            assert hasattr(m, name)


# ---------------------------------------------------------------------------
# domain/features_liquidity/__init__.py
# ---------------------------------------------------------------------------


class TestFeaturesLiquidity:
    def test_book_depth_feature_1m_minimal(self) -> None:
        from unified_api_contracts.internal.domain.features_liquidity import BookDepthFeature1m

        feat = BookDepthFeature1m(
            instrument_key="BINANCE-FUTURES:PERPETUAL:BTC-USDT",
            venue="BINANCE-FUTURES",
            timestamp=datetime.now(UTC),
        )
        assert feat.bid_depth_10bps is None
        assert feat.schema_version == "1.0.0"

    def test_book_depth_feature_1m_with_values(self) -> None:
        from unified_api_contracts.internal.domain.features_liquidity import BookDepthFeature1m

        feat = BookDepthFeature1m(
            instrument_key="BINANCE-FUTURES:PERPETUAL:BTC-USDT",
            venue="BINANCE-FUTURES",
            timestamp=datetime.now(UTC),
            bid_depth_10bps=0.01,
            ask_depth_10bps=0.02,
            mid_price=50000.0,
            adv_30d_usd=1_000_000.0,
            depth_imbalance_50bps=0.55,
        )
        assert feat.bid_depth_10bps == 0.01
        assert feat.mid_price == 50000.0

    def test_liquidity_wall_event(self) -> None:
        from unified_api_contracts.internal.domain.features_liquidity import LiquidityWallEvent

        evt = LiquidityWallEvent(
            instrument_key="BINANCE-FUTURES:PERPETUAL:BTC-USDT",
            venue="BINANCE-FUTURES",
            timestamp=datetime.now(UTC),
            side="bid",
            price_level=49500.0,
            wall_size_usd=5_000_000.0,
            wall_size_z=3.2,
            distance_bps=100.0,
            add_pressure=10000.0,
            cancel_pressure=5000.0,
        )
        assert evt.side == "bid"
        assert evt.schema_version == "1.0.0"

    def test_liquidation_cluster_feature_1m(self) -> None:
        from unified_api_contracts.internal.domain.features_liquidity import LiquidationClusterFeature1m

        feat = LiquidationClusterFeature1m(
            instrument_key="BINANCE-FUTURES:PERPETUAL:BTC-USDT",
            venue="BINANCE-FUTURES",
            timestamp=datetime.now(UTC),
            nearest_short_cluster_distance_bps=50.0,
            nearest_short_cluster_usd=2_000_000.0,
            nearest_long_cluster_distance_bps=80.0,
            nearest_long_cluster_usd=1_500_000.0,
            long_short_cluster_asymmetry=0.14,
            wall_cluster_overlap_count=2,
            source="coinglass",
        )
        assert feat.source == "coinglass"
        assert feat.wall_cluster_overlap_count == 2

    def test_flow_interaction_feature_1m(self) -> None:
        from unified_api_contracts.internal.domain.features_liquidity import FlowInteractionFeature1m

        feat = FlowInteractionFeature1m(
            instrument_key="BINANCE-FUTURES:PERPETUAL:BTC-USDT",
            venue="BINANCE-FUTURES",
            timestamp=datetime.now(UTC),
            cvd_usd=50000.0,
            cvd_5m_usd=200000.0,
            taker_buy_ratio=0.6,
            wall_absorption_usd=10000.0,
            wall_absorption_ratio=0.05,
        )
        assert feat.cvd_usd == 50000.0
        assert feat.schema_version == "1.0.0"

    def test_composite_sr_feature_1m(self) -> None:
        from unified_api_contracts.internal.domain.features_liquidity import CompositeSRFeature1m

        feat = CompositeSRFeature1m(
            instrument_key="BINANCE-FUTURES:PERPETUAL:BTC-USDT",
            venue="BINANCE-FUTURES",
            timestamp=datetime.now(UTC),
            top_bid_sr_price=49000.0,
            top_bid_sr_score=0.85,
            top_ask_sr_price=51000.0,
            top_ask_sr_score=0.75,
            top_bid_sr_distance_bps=200.0,
            top_ask_sr_distance_bps=200.0,
            sr_zone_count=4,
        )
        assert feat.sr_zone_count == 4
        assert feat.schema_version == "1.0.0"

    def test_all_exports(self) -> None:
        import unified_api_contracts.internal.domain.features_liquidity as m
        from unified_api_contracts.internal.domain.features_liquidity import __all__

        for name in __all__:
            assert hasattr(m, name)


# ---------------------------------------------------------------------------
# domain/features_multi_timeframe/__init__.py
# ---------------------------------------------------------------------------


class TestFeaturesMultiTimeframe:
    def test_re_exports_importable(self) -> None:
        from unified_api_contracts.internal.domain.features_multi_timeframe import (
            CrossTimeframeFeatures,
        )

        assert CrossTimeframeFeatures is not None

    def test_all_exports(self) -> None:
        import unified_api_contracts.internal.domain.features_multi_timeframe as m
        from unified_api_contracts.internal.domain.features_multi_timeframe import __all__

        for name in __all__:
            assert hasattr(m, name)


# ---------------------------------------------------------------------------
# domain/features_onchain/__init__.py
# ---------------------------------------------------------------------------


class TestFeaturesOnchain:
    def test_re_exports_importable(self) -> None:
        from unified_api_contracts.internal.domain.features_onchain import OnchainFeatureRecord

        assert OnchainFeatureRecord is not None

    def test_all_exports(self) -> None:
        import unified_api_contracts.internal.domain.features_onchain as m
        from unified_api_contracts.internal.domain.features_onchain import __all__

        for name in __all__:
            assert hasattr(m, name)


# ---------------------------------------------------------------------------
# domain/features_volatility/__init__.py
# ---------------------------------------------------------------------------


class TestFeaturesVolatility:
    def test_options_iv_schema(self) -> None:
        from unified_api_contracts.internal.domain.features_volatility import OPTIONS_IV_SCHEMA

        assert OPTIONS_IV_SCHEMA.name == "options_iv"
        col_names = [c.name for c in OPTIONS_IV_SCHEMA.columns]
        assert "atm_iv" in col_names
        assert "timestamp" in col_names

    def test_futures_term_structure_schema(self) -> None:
        from unified_api_contracts.internal.domain.features_volatility import (
            FUTURES_TERM_STRUCTURE_SCHEMA,
        )

        assert FUTURES_TERM_STRUCTURE_SCHEMA.name == "futures_term_structure"
        col_names = [c.name for c in FUTURES_TERM_STRUCTURE_SCHEMA.columns]
        assert "basis" in col_names

    def test_volatility_features_schema_alias(self) -> None:
        from unified_api_contracts.internal.domain.features_volatility import (
            OPTIONS_IV_SCHEMA,
            VOLATILITY_FEATURES_SCHEMA,
        )

        assert VOLATILITY_FEATURES_SCHEMA is OPTIONS_IV_SCHEMA

    def test_volatility_schemas_dict(self) -> None:
        from unified_api_contracts.internal.domain.features_volatility import VOLATILITY_SCHEMAS

        assert "options_iv" in VOLATILITY_SCHEMAS
        assert "futures_term_structure" in VOLATILITY_SCHEMAS

    def test_get_schema_for_feature_group_options_iv(self) -> None:
        from unified_api_contracts.internal.domain.features_volatility import (
            get_schema_for_feature_group,
        )

        schema = get_schema_for_feature_group("options_iv")
        assert schema is not None
        assert schema.name == "options_iv"

    def test_get_schema_for_feature_group_unknown(self) -> None:
        from unified_api_contracts.internal.domain.features_volatility import (
            get_schema_for_feature_group,
        )

        schema = get_schema_for_feature_group("nonexistent")
        assert schema is None

    def test_all_exports(self) -> None:
        import unified_api_contracts.internal.domain.features_volatility as m
        from unified_api_contracts.internal.domain.features_volatility import __all__

        for name in __all__:
            assert hasattr(m, name)

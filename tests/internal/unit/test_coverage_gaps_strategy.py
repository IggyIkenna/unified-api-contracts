"""Tests to close coverage gaps — strategy and sports execution domain modules.

Covers:
- unified_api_contracts.internal/domain/sports/__init__.py
- unified_api_contracts.internal/domain/sports/execution.py
  (CanonicalSportsOrder, CanonicalSportsFill)
- unified_api_contracts.internal/domain/strategy_service/signal_vector.py
  (RegimeStateRecord, SignalVectorRecord, MetaSignalRecord)

Split from test_coverage_gaps.py to stay under the 900-line QG limit.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# domain/sports/__init__.py + domain/sports/execution.py
# ---------------------------------------------------------------------------


class TestDomainSportsExecution:
    def test_canonical_sports_order_importable(self) -> None:
        from unified_api_contracts.internal.domain.sports import CanonicalSportsOrder

        assert CanonicalSportsOrder is not None

    def test_canonical_sports_fill_importable(self) -> None:
        from unified_api_contracts.internal.domain.sports import CanonicalSportsFill

        assert CanonicalSportsFill is not None

    def test_canonical_sports_order_instantiate_minimal(self) -> None:

        from unified_api_contracts.internal.domain.sports.execution import CanonicalSportsOrder

        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        order = CanonicalSportsOrder(
            order_id="ord-001",
            timestamp=ts,
            venue="betfair",
            instrument_id="1.234567890/12345678",
            side="buy",
            order_type="limit",
            quantity=10.0,
        )
        assert order.order_id == "ord-001"
        assert order.market_id is None
        assert order.selection_id is None
        assert order.persistence_type is None
        assert order.bet_side is None
        assert order.token_id is None
        assert order.bookmaker_key is None

    def test_canonical_sports_order_betfair_fields(self) -> None:

        from unified_api_contracts.internal.domain.sports.execution import CanonicalSportsOrder

        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        order = CanonicalSportsOrder(
            order_id="ord-002",
            timestamp=ts,
            venue="betfair",
            instrument_id="1.234567890/12345678",
            side="buy",
            order_type="limit",
            quantity=5.0,
            market_id="1.234567890",
            selection_id="12345678",
            persistence_type="LAPSE",
            bet_side="BACK",
            bookmaker_key="betfair",
            decimal_odds=Decimal("3.0"),
        )
        assert order.market_id == "1.234567890"
        assert order.selection_id == "12345678"
        assert order.persistence_type == "LAPSE"
        assert order.bet_side == "BACK"
        assert order.bookmaker_key == "betfair"

    def test_canonical_sports_order_pinnacle_fields(self) -> None:

        from unified_api_contracts.internal.domain.sports.execution import CanonicalSportsOrder

        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        order = CanonicalSportsOrder(
            order_id="ord-003",
            timestamp=ts,
            venue="pinnacle",
            instrument_id="event-999/line-111",
            side="buy",
            order_type="limit",
            quantity=20.0,
            line_id=111,
            period_number=0,
            team="TEAM1",
            bookmaker_key="pinnacle",
        )
        assert order.line_id == 111
        assert order.period_number == 0
        assert order.team == "TEAM1"

    def test_canonical_sports_order_polymarket_fields(self) -> None:

        from unified_api_contracts.internal.domain.sports.execution import CanonicalSportsOrder

        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        order = CanonicalSportsOrder(
            order_id="ord-004",
            timestamp=ts,
            venue="polymarket",
            instrument_id="token-abc",
            side="buy",
            order_type="limit",
            quantity=50.0,
            token_id="token-abc",
            outcome="Yes",
            transaction_hash="0xdeadbeef",
            bookmaker_key="polymarket",
        )
        assert order.token_id == "token-abc"
        assert order.outcome == "Yes"
        assert order.transaction_hash == "0xdeadbeef"

    def test_canonical_sports_fill_instantiate_minimal(self) -> None:

        from unified_api_contracts.internal.domain.sports.execution import CanonicalSportsFill

        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        fill = CanonicalSportsFill(
            fill_id="fill-001",
            order_id="ord-001",
            timestamp=ts,
            venue="betfair",
            instrument_id="1.234567890/12345678",
            side="buy",
            quantity=10.0,
            price=2.5,
        )
        assert fill.fill_id == "fill-001"
        assert fill.market_id is None
        assert fill.bet_id is None
        assert fill.size_matched is None
        assert fill.token_id is None

    def test_canonical_sports_fill_betfair_fields(self) -> None:

        from unified_api_contracts.internal.domain.sports.execution import CanonicalSportsFill

        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        fill = CanonicalSportsFill(
            fill_id="fill-002",
            order_id="ord-002",
            timestamp=ts,
            venue="betfair",
            instrument_id="1.234567890/12345678",
            side="buy",
            quantity=10.0,
            price=2.5,
            market_id="1.234567890",
            selection_id="12345678",
            bet_id="BET-999",
            size_matched=Decimal("10.0"),
            size_remaining=Decimal("0.0"),
            bookmaker_key="betfair",
            decimal_odds_matched=Decimal("2.5"),
        )
        assert fill.bet_id == "BET-999"
        assert fill.size_matched == Decimal("10.0")
        assert fill.size_remaining == Decimal("0.0")
        assert fill.bookmaker_key == "betfair"

    def test_canonical_sports_fill_polymarket_fields(self) -> None:

        from unified_api_contracts.internal.domain.sports.execution import CanonicalSportsFill

        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        fill = CanonicalSportsFill(
            fill_id="fill-003",
            order_id="ord-004",
            timestamp=ts,
            venue="polymarket",
            instrument_id="token-abc",
            side="buy",
            quantity=50.0,
            price=0.6,
            token_id="token-abc",
            outcome="Yes",
        )
        assert fill.token_id == "token-abc"
        assert fill.outcome == "Yes"

    def test_all_exports(self) -> None:
        import unified_api_contracts.internal.domain.sports as m
        from unified_api_contracts.internal.domain.sports import __all__

        for name in __all__:
            assert hasattr(m, name)


# ---------------------------------------------------------------------------
# domain/strategy_service/signal_vector.py
# ---------------------------------------------------------------------------


class TestDomainStrategyServiceSignalVector:
    def test_regime_state_record_importable(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.signal_vector import (
            RegimeStateRecord,
        )

        assert RegimeStateRecord is not None

    def test_signal_vector_record_importable(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.signal_vector import (
            SignalVectorRecord,
        )

        assert SignalVectorRecord is not None

    def test_meta_signal_record_importable(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.signal_vector import (
            MetaSignalRecord,
        )

        assert MetaSignalRecord is not None

    def test_regime_state_record_instantiate_defaults(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.signal_vector import (
            RegimeStateRecord,
        )

        r = RegimeStateRecord()
        assert r.macro_state is None
        assert r.macro_prob is None
        assert r.intraday_state is None
        assert r.micro_state is None
        assert r.strategy_allowed is None
        assert r.size_allowed is None
        assert r.entry_allowed is None
        assert r.composite_score is None

    def test_regime_state_record_instantiate_full(self) -> None:
        from unified_api_contracts.internal.domain.strategy_service.signal_vector import (
            RegimeStateRecord,
        )

        r = RegimeStateRecord(
            macro_state=1,
            macro_prob=0.85,
            time_in_regime=12,
            changepoint_score=0.1,
            macro_volatility=0.18,
            intraday_state="TRENDING",
            intraday_confidence=0.75,
            hours_in_intraday_regime=3,
            ewma_vol_ratio=1.2,
            micro_state="NORMAL",
            microstructure_stress=0.05,
            strategy_allowed=True,
            size_allowed=True,
            entry_allowed=True,
            composite_score=0.72,
        )
        assert r.macro_state == 1
        assert r.macro_prob == 0.85
        assert r.intraday_state == "TRENDING"
        assert r.micro_state == "NORMAL"
        assert r.strategy_allowed is True
        assert r.composite_score == 0.72

    def test_signal_vector_record_instantiate(self) -> None:

        from unified_api_contracts.internal.domain.strategy_service.signal_vector import (
            SignalVectorRecord,
        )

        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        sv = SignalVectorRecord(
            timestamp=ts,
            instrument_id="CEFI:BINANCE:BTC:USDT",
            direction_signal=0.6,
            vol_signal=-0.2,
            timing_signal=0.8,
            sizing_confidence=0.9,
        )
        assert sv.instrument_id == "CEFI:BINANCE:BTC:USDT"
        assert sv.direction_signal == 0.6
        assert sv.vol_signal == -0.2
        assert sv.timing_signal == 0.8
        assert sv.sizing_confidence == 0.9
        assert sv.source_features_used == []
        assert sv.direction_subcomponents == {}
        assert sv.vol_subcomponents == {}

    def test_signal_vector_record_with_regime_and_subcomponents(self) -> None:

        from unified_api_contracts.internal.domain.strategy_service.signal_vector import (
            RegimeStateRecord,
            SignalVectorRecord,
        )

        regime = RegimeStateRecord(macro_state=0, macro_prob=0.9, strategy_allowed=True)
        sv = SignalVectorRecord(
            timestamp=datetime(2026, 1, 2, 8, 0, 0, tzinfo=UTC),
            instrument_id="CEFI:DERIBIT:BTC:USD",
            direction_signal=0.0,
            vol_signal=0.5,
            timing_signal=0.4,
            sizing_confidence=0.7,
            regime_state=regime,
            source_features_used=["vrp_z_score_252d", "skew_25d"],
            direction_subcomponents={"cascade_confidence_score": 0.3},
            vol_subcomponents={"vrp_z_score_252d": 0.5, "skew_25d": 0.2},
        )
        assert sv.regime_state.macro_state == 0
        assert "vrp_z_score_252d" in sv.source_features_used
        assert sv.vol_subcomponents["skew_25d"] == 0.2

    def test_meta_signal_record_instantiate(self) -> None:

        from unified_api_contracts.internal.domain.strategy_service.signal_vector import (
            MetaSignalRecord,
        )

        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        ms = MetaSignalRecord(
            timestamp=ts,
            instrument_id="CEFI:BINANCE:ETH:USDT",
            meta_signal=0.4,
            meta_confidence=0.78,
            signal_weights={
                "direction": 0.4,
                "vol": 0.3,
                "timing": 0.2,
                "sizing": 0.1,
            },
        )
        assert ms.meta_signal == 0.4
        assert ms.meta_confidence == 0.78
        assert ms.signal_weights["direction"] == 0.4
        assert ms.is_fallback_equal_weight is False
        assert ms.meta_model_version == ""

    def test_meta_signal_record_fallback(self) -> None:

        from unified_api_contracts.internal.domain.strategy_service.signal_vector import (
            MetaSignalRecord,
        )

        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        ms = MetaSignalRecord(
            timestamp=ts,
            instrument_id="CEFI:BINANCE:ETH:USDT",
            meta_signal=0.0,
            meta_confidence=0.5,
            signal_weights={"direction": 0.4, "vol": 0.3, "timing": 0.2, "sizing": 0.1},
            is_fallback_equal_weight=True,
            meta_model_version="v1.2.0",
        )
        assert ms.is_fallback_equal_weight is True
        assert ms.meta_model_version == "v1.2.0"

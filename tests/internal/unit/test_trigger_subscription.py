"""Unit tests for TriggerSubscription and TriggerEvent models.

Tests cover:
- Model construction and validation
- TriggerEventType enum values
- Filter conditions serialization
- Default values
"""

from __future__ import annotations

from unified_api_contracts.internal.domain.strategy_service.trigger_subscription import (
    TriggerEvent,
    TriggerEventType,
    TriggerSubscription,
)


class TestTriggerSubscription:
    def test_minimal_construction(self) -> None:
        sub = TriggerSubscription(
            subscription_id="sub-001",
            event_type="FEATURE_UPDATE",
            strategy_ids=["STRAT_1"],
        )
        assert sub.subscription_id == "sub-001"
        assert sub.event_type == "FEATURE_UPDATE"
        assert sub.strategy_ids == ["STRAT_1"]
        assert sub.enabled is True
        assert sub.priority == 0
        assert sub.filter_conditions == {}

    def test_full_construction(self) -> None:
        sub = TriggerSubscription(
            subscription_id="sub-002",
            event_type="PRICE_CROSS",
            filter_conditions={"instrument_id": "BTC-PERP", "threshold": 0.5},
            strategy_ids=["STRAT_1", "STRAT_2"],
            enabled=False,
            priority=10,
            description="Price cross trigger for BTC",
        )
        assert sub.filter_conditions == {"instrument_id": "BTC-PERP", "threshold": 0.5}
        assert sub.enabled is False
        assert sub.priority == 10
        assert sub.description == "Price cross trigger for BTC"

    def test_multiple_strategy_ids(self) -> None:
        sub = TriggerSubscription(
            subscription_id="sub-003",
            event_type="ODDS_CHANGE",
            strategy_ids=["A", "B", "C"],
        )
        assert len(sub.strategy_ids) == 3

    def test_serialization_round_trip(self) -> None:
        sub = TriggerSubscription(
            subscription_id="sub-004",
            event_type="FEATURE_UPDATE",
            filter_conditions={"instrument_id": "ETH-PERP"},
            strategy_ids=["STRAT_1"],
        )
        data = sub.model_dump()
        restored = TriggerSubscription(**data)
        assert restored == sub


class TestTriggerEventType:
    def test_enum_values(self) -> None:
        assert TriggerEventType.FEATURE_UPDATE == "FEATURE_UPDATE"
        assert TriggerEventType.ODDS_CHANGE == "ODDS_CHANGE"
        assert TriggerEventType.PRICE_CROSS == "PRICE_CROSS"
        assert TriggerEventType.VOLATILITY_REGIME_CHANGE == "VOLATILITY_REGIME_CHANGE"
        assert TriggerEventType.RISK_ALERT == "RISK_ALERT"
        assert TriggerEventType.ML_PREDICTION == "ML_PREDICTION"
        assert TriggerEventType.CUSTOM == "CUSTOM"

    def test_used_as_event_type(self) -> None:
        sub = TriggerSubscription(
            subscription_id="sub-enum",
            event_type=TriggerEventType.FEATURE_UPDATE,
            strategy_ids=["STRAT_1"],
        )
        assert sub.event_type == "FEATURE_UPDATE"


class TestTriggerEvent:
    def test_minimal_construction(self) -> None:
        event = TriggerEvent(
            event_id="evt-001",
            event_type="FEATURE_UPDATE",
        )
        assert event.event_id == "evt-001"
        assert event.event_type == "FEATURE_UPDATE"
        assert event.payload == {}

    def test_with_payload(self) -> None:
        event = TriggerEvent(
            event_id="evt-002",
            event_type="PRICE_CROSS",
            payload={"instrument_id": "BTC-PERP", "price": 50000, "crossed_above": True},
            timestamp_iso="2026-03-16T12:00:00Z",
        )
        assert event.payload["instrument_id"] == "BTC-PERP"
        assert event.payload["price"] == 50000
        assert event.payload["crossed_above"] is True

    def test_serialization_round_trip(self) -> None:
        event = TriggerEvent(
            event_id="evt-003",
            event_type="ODDS_CHANGE",
            payload={"event_id": "match-123", "odds_delta": 0.15},
        )
        data = event.model_dump()
        restored = TriggerEvent(**data)
        assert restored == event


class TestMultiLegModels:
    """Basic tests for the multi-leg execution models."""

    def test_multi_leg_instruction_import(self) -> None:
        from unified_api_contracts.internal import (
            MultiLegExecutionMode,
            MultiLegInstruction,
        )

        assert MultiLegExecutionMode.LEADER_FOLLOWER == "LEADER_FOLLOWER"
        # Just verify importability
        assert MultiLegInstruction is not None

    def test_trigger_subscription_import(self) -> None:
        from unified_api_contracts.internal import TriggerSubscription

        assert TriggerSubscription is not None

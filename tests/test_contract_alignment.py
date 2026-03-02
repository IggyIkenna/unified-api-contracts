"""Tests that unified-api-contracts schemas are well-formed and internally consistent.

Verifies:
- All exported Pydantic models can be instantiated (schema loads, no import errors)
- Enum values are non-empty
- Schema fields have proper type annotations (no bare ``Any``)
- Internal subpackage (AC.internal) re-exports align with their source modules
"""

from __future__ import annotations

import inspect
from enum import Enum

import pytest
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_exports(module_obj: object) -> list[str]:
    """Return __all__ list from a module, or its public names."""
    all_names: list[str] | None = getattr(module_obj, "__all__", None)
    if all_names is not None:
        return list(all_names)
    return [n for n in dir(module_obj) if not n.startswith("_")]


def _is_pydantic_model(obj: object) -> bool:
    return inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel


def _is_enum(obj: object) -> bool:
    return inspect.isclass(obj) and issubclass(obj, Enum) and obj is not Enum


# ---------------------------------------------------------------------------
# Top-level AC exports
# ---------------------------------------------------------------------------


class TestTopLevelExports:
    """unified_api_contracts.__init__ exports must all resolve."""

    def test_all_exports_are_importable(self) -> None:
        import unified_api_contracts

        missing: list[str] = []
        for name in _collect_exports(unified_api_contracts):
            if not hasattr(unified_api_contracts, name):
                missing.append(name)
        assert missing == [], f"Exports declared in __all__ but not importable: {missing}"


# ---------------------------------------------------------------------------
# AC schemas subpackage (external / venue-facing schemas)
# ---------------------------------------------------------------------------


class TestACSchemas:
    """unified_api_contracts.schemas models are well-formed."""

    def test_funding_rate_instantiation(self) -> None:
        from unified_api_contracts.schemas import FundingRate

        obj = FundingRate(symbol="BTC-PERP", venue="binance", rate=0.0001, timestamp="2025-01-01T00:00:00Z")
        assert obj.symbol == "BTC-PERP"

    def test_heartbeat_message_instantiation(self) -> None:
        from unified_api_contracts.schemas import HeartbeatMessage

        obj = HeartbeatMessage(venue="binance", timestamp="2025-01-01T00:00:00Z")
        assert obj.venue == "binance"

    def test_subscribe_request_instantiation(self) -> None:
        from unified_api_contracts.schemas import SubscribeRequest

        obj = SubscribeRequest(venue="binance", channel="trades", symbols=["BTC/USDT"])
        assert obj.channel == "trades"
        assert obj.venue == "binance"

    def test_error_action_enum_non_empty(self) -> None:
        from unified_api_contracts.schemas import ErrorAction

        values = list(ErrorAction)
        assert len(values) > 0, "ErrorAction enum must have at least one member"

    def test_websocket_connection_state_is_dataclass(self) -> None:
        import dataclasses

        from unified_api_contracts.schemas import WebSocketConnectionState

        assert dataclasses.is_dataclass(WebSocketConnectionState), (
            "WebSocketConnectionState must be a dataclass"
        )
        field_names = {f.name for f in dataclasses.fields(WebSocketConnectionState)}
        assert "last_heartbeat" in field_names
        assert "reconnect_count" in field_names


# ---------------------------------------------------------------------------
# AC sports subpackage
# ---------------------------------------------------------------------------


class TestACSports:
    """Sports-betting schemas in unified_api_contracts.sports."""

    def test_odds_type_enum(self) -> None:
        from unified_api_contracts.sports import OddsType

        values = list(OddsType)
        assert len(values) > 0

    def test_outcome_type_enum(self) -> None:
        from unified_api_contracts.sports import OutcomeType

        values = list(OutcomeType)
        assert len(values) > 0

    def test_bookmaker_category_enum(self) -> None:
        from unified_api_contracts.sports import BookmakerCategory

        values = list(BookmakerCategory)
        assert len(values) > 0

    def test_arbitrage_status_enum(self) -> None:
        from unified_api_contracts.sports import ArbitrageStatus

        values = list(ArbitrageStatus)
        assert len(values) > 0

    def test_bet_status_enum(self) -> None:
        from unified_api_contracts.sports import BetStatus

        values = list(BetStatus)
        assert len(values) > 0

    def test_bookmaker_registry_populated(self) -> None:
        from unified_api_contracts.sports import BOOKMAKER_REGISTRY

        assert isinstance(BOOKMAKER_REGISTRY, dict), "BOOKMAKER_REGISTRY must be a dict"
        assert len(BOOKMAKER_REGISTRY) > 0, "Registry must contain at least one bookmaker"


# ---------------------------------------------------------------------------
# AC internal subpackage — ML, events, features, risk, pubsub, health, execution
# ---------------------------------------------------------------------------


class TestACInternalML:
    """AC internal ML schemas are well-formed."""

    def test_model_type_enum(self) -> None:
        from unified_api_contracts.internal import ModelType

        values = list(ModelType)
        assert len(values) >= 5, "ModelType should have lightgbm, xgboost, random_forest, neural_net, linear, ensemble"

    def test_target_type_enum(self) -> None:
        from unified_api_contracts.internal import TargetType

        values = list(TargetType)
        assert len(values) >= 5

    def test_model_variant_config_fields(self) -> None:
        from unified_api_contracts.internal import ModelVariantConfig, TargetType

        obj = ModelVariantConfig(
            instrument_id="BTC-USDT",
            timeframe="1h",
            lookback_window=100,
            target_type=TargetType.DIRECTION,
            std_dev_threshold=2.0,
            breakout_threshold=0.05,
        )
        assert obj.instrument_id == "BTC-USDT"

    def test_training_period_fields(self) -> None:
        from unified_api_contracts.internal import TrainingPeriod

        obj = TrainingPeriod(start="2024-01-01", end="2024-12-31")
        assert obj.start == "2024-01-01"


class TestACInternalEvents:
    """AC internal events schemas."""

    def test_lifecycle_event_type_enum(self) -> None:
        from unified_api_contracts.internal import LifecycleEventType

        values = list(LifecycleEventType)
        assert len(values) >= 10

    def test_event_severity_enum(self) -> None:
        from unified_api_contracts.internal import EventSeverity

        values = list(EventSeverity)
        assert {"INFO", "WARNING", "ERROR", "CRITICAL"} == {v.value for v in values}

    def test_service_mode_enum(self) -> None:
        from unified_api_contracts.internal import ServiceMode

        assert set(ServiceMode) == {ServiceMode.BATCH, ServiceMode.LIVE}


class TestACInternalHealth:
    """AC internal health schemas."""

    def test_error_category_enum(self) -> None:
        from unified_api_contracts.internal import ErrorCategory

        values = list(ErrorCategory)
        assert len(values) >= 10

    def test_error_severity_enum(self) -> None:
        from unified_api_contracts.internal import ErrorSeverity

        values = list(ErrorSeverity)
        assert {"low", "medium", "high", "critical"} == {v.value for v in values}

    def test_error_recovery_strategy_enum(self) -> None:
        from unified_api_contracts.internal import ErrorRecoveryStrategy

        values = list(ErrorRecoveryStrategy)
        assert len(values) >= 5

    def test_enhanced_error_instantiation(self) -> None:
        from unified_api_contracts.internal import (
            EnhancedError,
            ErrorCategory,
            ErrorContext,
            ErrorRecoveryStrategy,
            ErrorSeverity,
        )

        obj = EnhancedError(
            message="test error",
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.HIGH,
            recovery_strategy=ErrorRecoveryStrategy.RETRY,
            context=ErrorContext(service="test-svc"),
        )
        assert obj.category == ErrorCategory.TIMEOUT

    def test_circuit_breaker_state_enum(self) -> None:
        from unified_api_contracts.internal import CircuitBreakerStateEnum

        values = list(CircuitBreakerStateEnum)
        assert {"closed", "open", "half_open"} == {v.value for v in values}


class TestACInternalRisk:
    """AC internal risk schemas."""

    def test_risk_status_enum(self) -> None:
        from unified_api_contracts.internal import RiskStatus

        values = list(RiskStatus)
        assert {"OK", "WARNING", "CRITICAL"} == {v.value for v in values}

    def test_alert_type_enum(self) -> None:
        from unified_api_contracts.internal import AlertType

        values = list(AlertType)
        assert len(values) >= 6

    def test_position_side_enum(self) -> None:
        from unified_api_contracts.internal import PositionSide

        values = list(PositionSide)
        assert {"LONG", "SHORT", "FLAT"} == {v.value for v in values}


class TestACInternalPubsub:
    """AC internal pubsub schemas."""

    def test_internal_pubsub_topic_enum(self) -> None:
        from unified_api_contracts.internal import InternalPubSubTopic

        values = list(InternalPubSubTopic)
        assert len(values) >= 15


class TestACInternalExecution:
    """AC internal execution schemas."""

    def test_order_side_enum(self) -> None:
        from unified_api_contracts.internal import OrderSide

        values = list(OrderSide)
        assert len(values) >= 2

    def test_order_type_enum(self) -> None:
        from unified_api_contracts.internal import OrderType

        values = list(OrderType)
        assert len(values) >= 2

    def test_execution_status_enum(self) -> None:
        from unified_api_contracts.internal import ExecutionStatus

        values = list(ExecutionStatus)
        assert len(values) >= 2


# ---------------------------------------------------------------------------
# No bare ``Any`` in type annotations
# ---------------------------------------------------------------------------


class TestNoAnyAnnotations:
    """No field should use bare ``Any`` — per coding standards."""

    def _models_from_module(self, module_path: str) -> list[type[BaseModel]]:
        """Import module and return all Pydantic models defined in it."""
        import importlib

        mod = importlib.import_module(module_path)
        models: list[type[BaseModel]] = []
        for name in dir(mod):
            obj = getattr(mod, name)
            if _is_pydantic_model(obj) and obj.__module__ == mod.__name__:
                models.append(obj)
        return models

    @pytest.mark.parametrize(
        "module_path",
        [
            "unified_api_contracts.internal.ml",
            "unified_api_contracts.internal.events",
            "unified_api_contracts.internal.health",
            "unified_api_contracts.internal.risk",
            "unified_api_contracts.internal.pubsub",
            "unified_api_contracts.internal.features",
            "unified_api_contracts.internal.execution",
        ],
    )
    def test_no_bare_any_in_internal_models(self, module_path: str) -> None:
        """Every field annotation in internal models must use a concrete type, not ``Any``."""
        from typing import Any

        models = self._models_from_module(module_path)
        violations: list[str] = []
        for model_cls in models:
            for field_name, field_info in model_cls.model_fields.items():
                annotation = field_info.annotation
                if annotation is Any:
                    violations.append(f"{model_cls.__name__}.{field_name} uses bare Any")
        assert violations == [], f"Fields with bare Any: {violations}"

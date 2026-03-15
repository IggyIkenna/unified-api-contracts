"""Tests that unified-api-contracts schemas are well-formed and internally consistent.

Verifies:
- All exported Pydantic models can be instantiated (schema loads, no import errors)
- Enum values are non-empty
- Schema fields have proper type annotations (no bare ``Any``) in normalised contracts
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
        from unified_api_contracts import FundingRateHistory

        obj = FundingRateHistory(fundingTime="2025-01-01T00:00:00Z", rate="0.0001")
        assert obj.rate

    def test_heartbeat_message_instantiation(self) -> None:
        from unified_api_contracts import HeartbeatMessage

        obj = HeartbeatMessage(venue="binance", timestamp="2025-01-01T00:00:00Z")
        assert obj.venue == "binance"

    def test_subscribe_request_instantiation(self) -> None:
        from unified_api_contracts import SubscribeRequest

        obj = SubscribeRequest(venue="binance", channel="trades", symbols=["BTC/USDT"])
        assert obj.channel == "trades"
        assert obj.venue == "binance"

    def test_error_action_enum_non_empty(self) -> None:
        from unified_api_contracts import ErrorAction

        values = list(ErrorAction)
        assert len(values) > 0, "ErrorAction enum must have at least one member"

    def test_websocket_connection_state_is_dataclass(self) -> None:
        import dataclasses

        from unified_api_contracts import WebSocketConnectionState

        assert dataclasses.is_dataclass(WebSocketConnectionState), "WebSocketConnectionState must be a dataclass"
        field_names = {f.name for f in dataclasses.fields(WebSocketConnectionState)}
        assert "last_heartbeat" in field_names
        assert "reconnect_count" in field_names


# ---------------------------------------------------------------------------
# AC sports subpackage
# ---------------------------------------------------------------------------


class TestACSports:
    """Sports-betting schemas in unified_api_contracts.sports."""

    def test_odds_type_enum(self) -> None:
        from unified_api_contracts import OddsType

        values = list(OddsType)
        assert len(values) > 0

    def test_outcome_type_enum(self) -> None:
        from unified_api_contracts import OutcomeType

        values = list(OutcomeType)
        assert len(values) > 0

    def test_bookmaker_category_enum(self) -> None:
        from unified_api_contracts import BookmakerCategory

        values = list(BookmakerCategory)
        assert len(values) > 0

    def test_arbitrage_status_enum(self) -> None:
        from unified_api_contracts import ArbitrageStatus

        values = list(ArbitrageStatus)
        assert len(values) > 0

    def test_bet_status_enum(self) -> None:
        from unified_api_contracts import BetStatus

        values = list(BetStatus)
        assert len(values) > 0

    def test_bookmaker_registry_populated(self) -> None:
        from unified_api_contracts import BOOKMAKER_REGISTRY

        assert isinstance(BOOKMAKER_REGISTRY, dict), "BOOKMAKER_REGISTRY must be a dict"
        assert len(BOOKMAKER_REGISTRY) > 0, "Registry must contain at least one bookmaker"


# ---------------------------------------------------------------------------
# No bare ``Any`` in type annotations (external + normalised only; internal moved to UIC)
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
            "unified_api_contracts.canonical.domain",
            "unified_api_contracts.canonical.execution",
            "unified_api_contracts.canonical.errors",
        ],
    )
    def test_no_bare_any_in_normalised_models(self, module_path: str) -> None:
        """Every field annotation in normalised models must use a concrete type, not ``Any``."""
        from typing import Any

        models = self._models_from_module(module_path)
        violations: list[str] = []
        for model_cls in models:
            for field_name, field_info in model_cls.model_fields.items():
                annotation = field_info.annotation
                if annotation is Any:
                    violations.append(f"{model_cls.__name__}.{field_name} uses bare Any")
        assert violations == [], f"Fields with bare Any: {violations}"

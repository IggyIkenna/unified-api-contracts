"""Tests for DeFiPosition.is_at_risk resolving from LIQUIDATION_PARAMS_REGISTRY."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.internal.domain.execution_service.defi_position import DeFiPosition
from unified_api_contracts.internal.domain.execution_service.types import PositionType
from unified_api_contracts.internal.risk import LIQUIDATION_PARAMS_REGISTRY, MarginModel


def _make_position(health_factor: Decimal | None) -> DeFiPosition:
    return DeFiPosition(
        position_id="test_pos_0001",
        position_type=PositionType.A_TOKEN,
        venue="AAVE_V3-ETHEREUM",
        token="aUSDT",
        underlying="USDT",
        amount=Decimal("10000"),
        entry_timestamp=datetime.now(UTC),
        health_factor=health_factor,
    )


def test_defi_position_is_at_risk_resolves_from_registry() -> None:
    """is_at_risk must use LIQUIDATION_PARAMS_REGISTRY[AAVE_V3].health_factor_critical (1.15), not a hardcoded 1.1."""
    threshold = LIQUIDATION_PARAMS_REGISTRY[MarginModel.AAVE_V3].health_factor_critical
    assert threshold == Decimal("1.15")

    # Below the registry threshold (1.15) but above the old hardcoded 1.1 -> must now read at-risk.
    at_risk = _make_position(Decimal("1.12"))
    assert at_risk.is_at_risk is True

    not_at_risk = _make_position(Decimal("1.5"))
    assert not_at_risk.is_at_risk is False

    exactly_at_threshold = _make_position(threshold)
    assert exactly_at_threshold.is_at_risk is False


def test_defi_position_is_at_risk_none_health_factor() -> None:
    """No health_factor -> never at risk (no comparison possible)."""
    assert _make_position(None).is_at_risk is False

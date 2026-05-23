"""Closed-set sanity tests for the UAC drawdown + response-policy schemas.

Phase 1 of
``plans/active/drawdown_liquidation_policy_and_strategy_risk_config_2026_05_23.md``.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.risk import (
    DrawdownThresholdKind,
    ExpectedDrawdownModel,
    ExpectedDrawdownModelBasis,
    ResponsePolicy,
    RiskThresholds,
)


def test_drawdown_threshold_kind_has_7_members() -> None:
    assert len(list(DrawdownThresholdKind)) == 7


def test_expected_drawdown_basis_has_6_members() -> None:
    assert len(list(ExpectedDrawdownModelBasis)) == 6


def _full_thresholds(
    warn: Decimal | None = Decimal("-0.005"),
    inv: Decimal | None = Decimal("-0.01"),
    he: Decimal | None = Decimal("-0.02"),
    pause: Decimal | None = Decimal("-0.03"),
    reduce: Decimal | None = Decimal("-0.04"),
    close: Decimal | None = Decimal("-0.05"),
    liq: Decimal | None = Decimal("-0.07"),
) -> RiskThresholds:
    return RiskThresholds(
        pnl_drawdown={
            DrawdownThresholdKind.WARNING: warn,
            DrawdownThresholdKind.INVESTIGATION: inv,
            DrawdownThresholdKind.HUMAN_ESCALATION: he,
            DrawdownThresholdKind.AUTO_PAUSE: pause,
            DrawdownThresholdKind.AUTO_REDUCE: reduce,
            DrawdownThresholdKind.AUTO_CLOSE_ALL: close,
            DrawdownThresholdKind.LIQUIDATION_RISK: liq,
        }
    )


def test_risk_thresholds_accepts_all_7_declared() -> None:
    rt = _full_thresholds()
    assert rt.pnl_drawdown[DrawdownThresholdKind.AUTO_PAUSE] == Decimal("-0.03")


def test_risk_thresholds_rejects_missing_kind() -> None:
    with pytest.raises(ValidationError):
        RiskThresholds(
            pnl_drawdown={
                DrawdownThresholdKind.WARNING: Decimal("-0.005"),
                # all others missing
            }
        )


def test_risk_thresholds_allows_explicit_none() -> None:
    """None means "this threshold opted out" — must still appear as a key."""
    rt = _full_thresholds(pause=None)
    assert rt.pnl_drawdown[DrawdownThresholdKind.AUTO_PAUSE] is None


def test_risk_thresholds_rejects_non_monotonic_ladder() -> None:
    """AUTO_PAUSE less-negative than HUMAN_ESCALATION violates the ladder."""
    with pytest.raises(ValidationError):
        _full_thresholds(he=Decimal("-0.03"), pause=Decimal("-0.02"))


def test_response_policy_requires_all_5_flags() -> None:
    rp = ResponsePolicy(
        allow_agent_investigation=True,
        allow_auto_pause=True,
        allow_auto_reduce=False,
        allow_auto_close_all=False,
        require_human_for_resume=True,
    )
    assert rp.allow_agent_investigation is True
    assert rp.require_human_for_resume is True


def test_response_policy_rejects_missing_field() -> None:
    with pytest.raises(ValidationError):
        ResponsePolicy(
            allow_agent_investigation=True,
            allow_auto_pause=True,
            allow_auto_reduce=False,
            allow_auto_close_all=False,
            # require_human_for_resume missing
        )  # type: ignore[call-arg]


def test_expected_drawdown_model_basis_is_closed_set() -> None:
    m = ExpectedDrawdownModel(basis=ExpectedDrawdownModelBasis.VAR, confidence_level=Decimal("0.95"))
    assert m.basis == ExpectedDrawdownModelBasis.VAR
    # CUSTOM is a valid escape hatch
    ExpectedDrawdownModel(basis=ExpectedDrawdownModelBasis.CUSTOM)


def test_expected_drawdown_model_lookback_optional() -> None:
    m = ExpectedDrawdownModel(
        basis=ExpectedDrawdownModelBasis.HISTORICAL_BACKTEST,
        lookback_window=timedelta(days=30),
    )
    assert m.lookback_window == timedelta(days=30)

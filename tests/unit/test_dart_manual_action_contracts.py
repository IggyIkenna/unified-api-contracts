"""DART manual-action contract tests — `cross_cutting_may_23_deliverables` deliverable #4.

Verifies the closed-set + audit-log surface that Harsh T6 consumes when wiring
the 5 DART manual surfaces (DeFi swap/lend/borrow/stake, CeFi orders, ML training
trigger, sports manual bet, prediction-market manual trade).

Pairs with `codex/04-architecture/manual-trade-booking.md` + `codex/09-strategy/
architecture-v2/cross-cutting/dart-manual-trade-spec.md`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.internal.execution import (
    ManualAuditCategory,
    ManualExecutionMode,
    ManualInstruction,
    ManualInstructionAuditLog,
    ManualMLTrainingAction,
    MLTrainingControlRequest,
    MLTrainingControlResponse,
)


def _now() -> datetime:
    return datetime(2026, 5, 12, 10, 30, 0, tzinfo=UTC)


def test_manual_ml_training_action_closed_set() -> None:
    """ManualMLTrainingAction enum is the closed set of training-control verbs."""
    members = {member.value for member in ManualMLTrainingAction}
    assert members == {"pause", "resume", "retrain"}


def test_manual_audit_category_closed_set() -> None:
    """ManualAuditCategory closed set covers both manual trade + ML training control."""
    members = {member.value for member in ManualAuditCategory}
    assert members == {"manual_trade", "ml_training_control"}


def test_ml_training_control_request_round_trip() -> None:
    """MLTrainingControlRequest serializes + deserializes with required fields."""
    request = MLTrainingControlRequest(
        request_id="req-001",
        submitted_by="operator@anthropic.com",
        archetype="ml_directional_continuous",
        action=ManualMLTrainingAction.PAUSE,
        submitted_at=_now(),
        reason="halt for retrain config update",
        strategy_id="ML_DIR.ml_directional_continuous.binance-eth-perp-1h-USDT-prod",
    )

    payload = request.model_dump()
    restored = MLTrainingControlRequest.model_validate(payload)

    assert restored.request_id == "req-001"
    assert restored.action == ManualMLTrainingAction.PAUSE
    assert restored.archetype == "ml_directional_continuous"
    assert restored.client_id == ""


def test_ml_training_control_response_correlates_with_request_id() -> None:
    """MLTrainingControlResponse echoes the request_id for audit-log correlation."""
    response = MLTrainingControlResponse(
        request_id="req-001",
        archetype="ml_directional_continuous",
        action=ManualMLTrainingAction.PAUSE,
        status="applied",
        effective_at=_now(),
        detail="paused at checkpoint epoch=42",
    )

    assert response.request_id == "req-001"
    assert response.status == "applied"


def test_audit_log_manual_trade_category() -> None:
    """Audit-log row for a MANUAL_TRADE category populates manual_instruction only."""
    instruction = ManualInstruction(
        instruction_id="inst-100",
        submitted_by="operator@anthropic.com",
        venue="binance",
        account_id="acct-1",
        instrument_key="binance:perpetual:BTC-USDT",
        side="BUY",
        order_type="MARKET",
        quantity=Decimal("0.1"),
        submitted_at=_now(),
        execution_mode=ManualExecutionMode.EXECUTE,
        client_id="client-A",
        strategy_id="CARRY.carry_basis_perp.binance-btc-perp-8h-USDT-prod",
        portfolio_id="pf-1",
        asset_group="cefi",
    )

    audit_row = ManualInstructionAuditLog(
        audit_id="aud-100",
        action_category=ManualAuditCategory.MANUAL_TRADE,
        persisted_at=_now(),
        submitted_by="operator@anthropic.com",
        asset_group="cefi",
        strategy_id=instruction.strategy_id,
        client_id=instruction.client_id,
        portfolio_id=instruction.portfolio_id,
        manual_instruction=instruction,
        pre_trade_check_passed=True,
        routed_to_venue="binance",
    )

    assert audit_row.action_category == ManualAuditCategory.MANUAL_TRADE
    assert audit_row.manual_instruction is not None
    assert audit_row.manual_instruction.instruction_id == "inst-100"
    assert audit_row.ml_training_request is None
    assert audit_row.ml_training_response is None


def test_audit_log_ml_training_category() -> None:
    """Audit-log row for ML_TRAINING_CONTROL populates ml_training_* only."""
    request = MLTrainingControlRequest(
        request_id="req-200",
        submitted_by="operator@anthropic.com",
        archetype="ml_directional_continuous",
        action=ManualMLTrainingAction.RETRAIN,
        submitted_at=_now(),
        strategy_id="ML_DIR.ml_directional_continuous.binance-eth-perp-1h-USDT-prod",
    )
    response = MLTrainingControlResponse(
        request_id="req-200",
        archetype="ml_directional_continuous",
        action=ManualMLTrainingAction.RETRAIN,
        status="accepted",
        effective_at=_now(),
    )

    audit_row = ManualInstructionAuditLog(
        audit_id="aud-200",
        action_category=ManualAuditCategory.ML_TRAINING_CONTROL,
        persisted_at=_now(),
        submitted_by="operator@anthropic.com",
        strategy_id=request.strategy_id,
        ml_training_request=request,
        ml_training_response=response,
    )

    assert audit_row.action_category == ManualAuditCategory.ML_TRAINING_CONTROL
    assert audit_row.manual_instruction is None
    assert audit_row.ml_training_request is not None
    assert audit_row.ml_training_request.action == ManualMLTrainingAction.RETRAIN
    assert audit_row.ml_training_response is not None
    assert audit_row.ml_training_response.status == "accepted"


def test_audit_log_request_response_correlation() -> None:
    """Audit row's request + response carry matching request_id (correlation invariant)."""
    request = MLTrainingControlRequest(
        request_id="req-corr",
        submitted_by="operator@anthropic.com",
        archetype="ml_directional_continuous",
        action=ManualMLTrainingAction.RESUME,
        submitted_at=_now(),
    )
    response = MLTrainingControlResponse(
        request_id="req-corr",
        archetype="ml_directional_continuous",
        action=ManualMLTrainingAction.RESUME,
        status="applied",
        effective_at=_now(),
    )
    audit_row = ManualInstructionAuditLog(
        audit_id="aud-corr",
        action_category=ManualAuditCategory.ML_TRAINING_CONTROL,
        persisted_at=_now(),
        submitted_by="operator@anthropic.com",
        ml_training_request=request,
        ml_training_response=response,
    )

    assert audit_row.ml_training_request is not None
    assert audit_row.ml_training_response is not None
    assert audit_row.ml_training_request.request_id == audit_row.ml_training_response.request_id

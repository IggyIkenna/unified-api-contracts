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
    ManualInstructionPrecheckResponse,
    ManualMLTrainingAction,
    MLTrainingControlRequest,
    MLTrainingControlResponse,
    WalletSpendingPreCheckResult,
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


def test_manual_instruction_carries_wallet_id() -> None:
    """ManualInstruction.wallet_id provides provenance for DeFi audit-log rollups."""
    instruction = ManualInstruction(
        instruction_id="inst-defi-1",
        submitted_by="operator@anthropic.com",
        venue="aave_v3",
        account_id="vault-7",
        instrument_key="ethereum:lending:USDC",
        side="BUY",
        order_type="LEND",
        quantity=Decimal("50000"),
        submitted_at=_now(),
        execution_mode=ManualExecutionMode.EXECUTE,
        client_id="client-A",
        strategy_id="LST_LEV.carry_staked_basis.aave-v3-USDC-1d-USDC-prod",
        asset_group="defi",
        wallet_id="hot-trading-eth-1",
    )
    assert instruction.wallet_id == "hot-trading-eth-1"
    # Non-DeFi default stays empty.
    cefi = ManualInstruction(
        instruction_id="inst-cefi-1",
        submitted_by="operator@anthropic.com",
        venue="binance",
        account_id="acct-1",
        instrument_key="binance:spot:BTC-USDT",
        side="BUY",
        order_type="MARKET",
        quantity=Decimal("0.1"),
        submitted_at=_now(),
    )
    assert cefi.wallet_id == ""


def test_wallet_spending_precheck_result_passed_path() -> None:
    """WalletSpendingPreCheckResult on a clean pre-trade check (all caps within)."""
    result = WalletSpendingPreCheckResult(
        wallet_id="hot-trading-eth-1",
        checked_at=_now(),
        passed=True,
        kill_switch_armed=False,
        kill_switch_id="KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS",
        amount_usd=Decimal("50000"),
        per_tx_check=True,
        per_hour_check=True,
        per_day_check=True,
        per_protocol_check=True,
    )
    assert result.passed is True
    assert result.kill_switch_armed is False
    assert result.denial_reason == ""


def test_wallet_spending_precheck_result_kill_switch_armed() -> None:
    """Kill-switch armed short-circuits the check; denial_reason populated."""
    result = WalletSpendingPreCheckResult(
        wallet_id="hot-trading-eth-1",
        checked_at=_now(),
        passed=False,
        kill_switch_armed=True,
        kill_switch_id="KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS",
        denial_reason="kill_switch_armed",
    )
    assert result.passed is False
    assert result.kill_switch_armed is True
    assert result.denial_reason == "kill_switch_armed"


def test_audit_log_defi_trade_carries_wallet_spending_check() -> None:
    """Audit row for a DeFi manual trade populates wallet_id + wallet_spending_check."""
    instruction = ManualInstruction(
        instruction_id="inst-defi-100",
        submitted_by="operator@anthropic.com",
        venue="aave_v3",
        account_id="vault-7",
        instrument_key="ethereum:lending:USDC",
        side="BUY",
        order_type="LEND",
        quantity=Decimal("50000"),
        submitted_at=_now(),
        execution_mode=ManualExecutionMode.EXECUTE,
        asset_group="defi",
        wallet_id="hot-trading-eth-1",
    )
    spending_check = WalletSpendingPreCheckResult(
        wallet_id="hot-trading-eth-1",
        checked_at=_now(),
        passed=True,
        kill_switch_armed=False,
        amount_usd=Decimal("50000"),
        per_tx_check=True,
        per_hour_check=True,
        per_day_check=True,
        per_protocol_check=True,
    )
    audit_row = ManualInstructionAuditLog(
        audit_id="aud-defi-100",
        action_category=ManualAuditCategory.MANUAL_TRADE,
        persisted_at=_now(),
        submitted_by="operator@anthropic.com",
        asset_group="defi",
        wallet_id=instruction.wallet_id,
        manual_instruction=instruction,
        wallet_spending_check=spending_check,
        pre_trade_check_passed=True,
        routed_to_venue="aave_v3",
    )
    assert audit_row.wallet_id == "hot-trading-eth-1"
    assert audit_row.wallet_spending_check is not None
    assert audit_row.wallet_spending_check.passed is True
    assert audit_row.wallet_spending_check.wallet_id == audit_row.wallet_id


def test_audit_log_non_defi_trade_omits_wallet_spending_check() -> None:
    """Audit row for a CeFi manual trade leaves wallet_spending_check None."""
    instruction = ManualInstruction(
        instruction_id="inst-cefi-2",
        submitted_by="operator@anthropic.com",
        venue="binance",
        account_id="acct-1",
        instrument_key="binance:spot:BTC-USDT",
        side="BUY",
        order_type="MARKET",
        quantity=Decimal("0.1"),
        submitted_at=_now(),
        asset_group="cefi",
    )
    audit_row = ManualInstructionAuditLog(
        audit_id="aud-cefi-2",
        action_category=ManualAuditCategory.MANUAL_TRADE,
        persisted_at=_now(),
        submitted_by="operator@anthropic.com",
        asset_group="cefi",
        manual_instruction=instruction,
        pre_trade_check_passed=True,
        routed_to_venue="binance",
    )
    assert audit_row.wallet_id == ""
    assert audit_row.wallet_spending_check is None


def test_manual_instruction_precheck_response_accepted() -> None:
    """Precheck response on an accepted dry-run echoes wallet check + routing target."""
    spending_check = WalletSpendingPreCheckResult(
        wallet_id="hot-trading-eth-1",
        checked_at=_now(),
        passed=True,
        kill_switch_armed=False,
        amount_usd=Decimal("50000"),
        per_tx_check=True,
        per_hour_check=True,
        per_day_check=True,
        per_protocol_check=True,
    )
    response = ManualInstructionPrecheckResponse(
        instruction_id="inst-defi-100",
        checked_at=_now(),
        accepted=True,
        wallet_spending_check=spending_check,
        capital_allocation_remaining_usd=Decimal("250000"),
        routing_target="ethereum:aave_v3",
        estimated_amount_usd=Decimal("50000"),
    )
    assert response.accepted is True
    assert response.rejection_reason == ""
    assert response.wallet_spending_check is not None
    assert response.routing_target == "ethereum:aave_v3"


def test_manual_instruction_precheck_response_rejected_capital_allocation() -> None:
    """Precheck rejected on capital allocation exhaustion populates rejection_reason."""
    response = ManualInstructionPrecheckResponse(
        instruction_id="inst-cefi-3",
        checked_at=_now(),
        accepted=False,
        rejection_reason="capital_allocation_exhausted",
        capital_allocation_remaining_usd=Decimal("0"),
        routing_target="binance",
        estimated_amount_usd=Decimal("100000"),
    )
    assert response.accepted is False
    assert response.rejection_reason == "capital_allocation_exhausted"
    assert response.capital_allocation_remaining_usd == Decimal("0")


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

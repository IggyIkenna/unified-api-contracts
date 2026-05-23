"""Execution-service top-level internal contracts.

Contains schemas for manual/operator-initiated execution operations that
are not covered by the canonical ExecutionInstruction in UAC.

Note: CanonicalOrder, CanonicalFill, ExecutionInstruction, ExecutionResult
live in UAC unified_api_contracts.canonical.domain.execution (the canonical layer).
This module is for UIC-owned internal schemas consumed within and between
execution-service components.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SettlementType(StrEnum):
    """Types of settlement events that change token balances."""

    FUNDING_8H = "funding_8h"
    FUNDING_CONTINUOUS = "funding_continuous"
    SEASONAL_WEEKLY = "seasonal_weekly"
    AAVE_INDEX = "aave_index"
    STAKING_YIELD = "staking_yield"
    LST_YIELD = "lst_yield"
    TRANSACTION_FEE = "transaction_fee"
    GAS_REBATE = "gas_rebate"
    LIQUIDATION = "liquidation"
    LP_FEE = "lp_fee"
    FLASH_LOAN_FEE = "flash_loan_fee"


class BatchExecutionMode(StrEnum):
    """How batch/backtest fills should be simulated."""

    BENCHMARK = "benchmark"
    """Always fill at requested price. Zero execution alpha. Isolates strategy P&L."""

    SIMULATED = "simulated"
    """Realistic fills with commission, margin, latency. Measures execution alpha."""


class ManualExecutionMode(StrEnum):
    """How a manual instruction should be processed by the execution service."""

    EXECUTE = "execute"
    """Route to venue via orchestrator (normal flow — same path as automated strategies)."""

    RECORD_ONLY = "record_only"
    """Skip venue execution, record fill directly (OTC, missed trades, simulation)."""


class ManualMLTrainingAction(StrEnum):
    """Operator-initiated lifecycle actions on an ML archetype training run.

    Separate axis from `OperationType` because these are training-control
    operations, not trade operations. Consumed by the DART manual ML training
    trigger surface (`cross_cutting_may_23_deliverables` deliverable #4 BUILD 3)
    which posts to `ml-training-service` `POST /training/{archetype}/{action}`.
    """

    PAUSE = "pause"
    """Suspend the in-flight training loop without losing checkpoint state."""

    RESUME = "resume"
    """Resume a paused training run from its last checkpoint."""

    RETRAIN = "retrain"
    """Force a fresh training run; discards any in-flight loop for the archetype."""


class ManualAuditCategory(StrEnum):
    """Which child schema populated a `ManualInstructionAuditLog` row.

    Closed set so the audit-log surface stays type-safe; downstream consumers
    (pnl-attribution / batch-live-reconciliation / alerting) dispatch on this
    rather than null-checking each child field.
    """

    MANUAL_TRADE = "manual_trade"
    """`manual_instruction` field populated; ml_training_* fields None."""

    ML_TRAINING_CONTROL = "ml_training_control"
    """`ml_training_request` (and optionally response) populated; manual_instruction None."""


class ManualInstruction(BaseModel):
    """An operator-submitted manual execution instruction for audit and routing.

    Created by the manual-trading API endpoint and persisted to the audit log
    before being forwarded to the live orchestrator (EXECUTE mode) or recorded
    directly as a fill (RECORD_ONLY mode).

    Attributes:
        instruction_id: Unique UUID for idempotency and audit tracing.
        submitted_by: Identity of the operator (OAuth sub claim).
        venue: Target venue slug (e.g. "binance", "deribit", or counterparty for OTC).
        account_id: Account identifier at the venue.
        instrument_key: Canonical instrument key (VENUE:TYPE:SYMBOL).
        side: Trade direction. CeFi/DeFi: "BUY" or "SELL". Sports: "HOME"/"AWAY"/"DRAW".
            Prediction: "YES"/"NO". Validated at the endpoint per asset_group.
        order_type: Execution algorithm (e.g. "MARKET", "TWAP", "VWAP"). Always the HOW.
        operation_type: Operation verb — the WHAT. Empty for CeFi (implicit from side).
            DeFi: OperationType value (e.g. "SWAP", "STAKE", "LEND"). Sports/prediction:
            "PLACE_BET". Populated from ManualInstructionRequest.instruction_type.
        quantity: Order quantity in base asset units.
        price: Limit price; None for market orders.
        reason: Human-readable reason for the manual trade (audit log).
        submitted_at: UTC wall-clock time of submission.
        execution_mode: EXECUTE (route to venue) or RECORD_ONLY (direct fill recording).
        client_id: Org hierarchy — client identifier.
        strategy_id: Org hierarchy — strategy identifier.
        portfolio_id: Org hierarchy — portfolio/book identifier.
        asset_group: Instrument asset group (e.g. "cefi", "defi", "sports", "prediction").
        counterparty: OTC counterparty identifier.
        source_reference: External trade ID (exchange reference, broker confirmation).
    """

    model_config = ConfigDict(populate_by_name=True)

    instruction_id: str
    submitted_by: str
    venue: str
    account_id: str
    instrument_key: str
    side: str
    order_type: str
    operation_type: str = ""
    quantity: Decimal
    submitted_at: datetime
    price: Decimal | None = None
    reason: str = Field(default="manual_trade")
    execution_mode: ManualExecutionMode = ManualExecutionMode.EXECUTE
    client_id: str = ""
    strategy_id: str = ""
    portfolio_id: str = ""
    asset_group: str = Field(
        default="",
        description="Instrument asset group (cefi, defi, sports, prediction).",
    )
    counterparty: str = ""
    source_reference: str = ""
    wallet_id: str = Field(
        default="",
        description=(
            "DeFi wallet identifier per WalletProvisioningConfig.wallet_id "
            "(empty for CeFi/sports/prediction trades). Provenance for audit-log rollup "
            "+ pre-trade wallet-tier kill-switch + SpendingCaps validation."
        ),
    )


class MLTrainingControlRequest(BaseModel):
    """Operator-submitted ML training lifecycle control instruction.

    Posted from the DART `MlTrainingControlPanel` UI to
    `ml-training-service` `POST /training/{archetype}/{action}`. Persisted
    to the same audit log as `ManualInstruction` so all operator-initiated
    actions (manual trade + manual training trigger) share one timeline.
    """

    model_config = ConfigDict(populate_by_name=True)

    request_id: str
    submitted_by: str
    archetype: str
    action: ManualMLTrainingAction
    submitted_at: datetime
    reason: str = Field(default="manual_training_action")
    strategy_id: str = ""
    client_id: str = ""


class MLTrainingControlResponse(BaseModel):
    """Response from `ml-training-service` after applying a training control action.

    Echoes the originating request_id for audit-log correlation. `status` is a
    closed set of outcome states (e.g. `accepted` / `rejected` / `applied` /
    `no_op`); `effective_at` is the wall-clock time the training-service applied
    the action (may differ from request submitted_at by API latency + queueing).
    """

    model_config = ConfigDict(populate_by_name=True)

    request_id: str
    archetype: str
    action: ManualMLTrainingAction
    status: str
    effective_at: datetime
    detail: str = ""


class PositionHealthSnapshot(BaseModel):
    """Current position-health state for a single wallet, as queried by PBM
    ``GET /positions/health?wallet_id=X``.

    Consumed by execution-service ``run_wallet_preflight_checks`` Layer-4
    (position-health gate) to compute ``projected_ltv`` / ``projected_margin_ratio``
    before forwarding a manual or automated instruction.

    All four numeric fields are optional because a wallet may have only a lending
    leg (no perp), only a perp leg (no lending), or be freshly provisioned with no
    open positions yet.
    """

    model_config = ConfigDict(populate_by_name=True)

    wallet_id: str
    snapshot_at: datetime

    ltv: Decimal | None = None
    """Current loan-to-value ratio ``debt / collateral`` in ``[0, 1]``.
    Populated for Aave / Compound lending positions. ``None`` for non-lending
    wallets."""

    margin_ratio: Decimal | None = None
    """Current margin ratio for perp positions (maintenance margin / account value).
    Populated for CeFi perp-hedged legs. ``None`` for lending-only wallets."""

    liquidation_threshold: Decimal | None = None
    """Protocol-defined LTV at which the lending position is liquidated
    (e.g. Aave WETH collateral ETH mainnet = 0.825). ``None`` if no lending leg."""

    maintenance_margin: Decimal | None = None
    """Minimum margin ratio floor before venue liquidation for perp positions.
    ``None`` if no perp leg."""


class WalletSpendingPreCheckResult(BaseModel):
    """Outcome of pre-trade wallet-tier kill-switch + SpendingCaps validation.

    Computed at the `/manual/instruction` API boundary BEFORE forwarding to the
    executor when `manual_instruction.wallet_id` is non-empty. Persisted into
    `ManualInstructionAuditLog.wallet_spending_check` so pnl-attribution +
    batch-live-reconciliation + alerting can reconstruct the pre-trade envelope
    state for any manual action.

    The validation algorithm (implemented in execution-service runtime, NOT in
    UAC) loads the operator-target `WalletProvisioningConfig` and:

    1. If `kill_switch_id` is armed → `kill_switch_armed=True`, `passed=False`.
    2. Else, compute `amount_usd` from `manual_instruction.quantity x price` (or
       reference price for market orders) and run:
       - `SpendingCaps.is_within_per_tx(amount_usd)` → populate `per_tx_check`.
       - Look up rolling 1h spend from position-balance-monitor →
         `per_hour_check`.
       - Look up rolling 24h spend → `per_day_check`.
       - If `manual_instruction.venue` matches a `per_protocol_usd` key →
         `per_protocol_check`.
    3. Layer-4 position-health (R-17): query PBM ``/positions/health?wallet_id=X``
       (5s TTL cache); compute projected LTV (lending) or projected margin ratio
       (perp) after this trade. Populate ``position_health_check``,
       ``projected_ltv``, ``projected_margin_ratio``, ``position_health_denial_reason``.
    4. Aggregate: ``passed = (kill_switch_armed is False) and all 5 checks True``
       (4 spending-cap checks + 1 position-health check).
    5. Populate `denial_reason` with the failed-check name if `passed is False`.

    Empty result (`wallet_id == ""` on the source instruction) means "non-DeFi
    trade, wallet checks skipped" — the field stays None in the audit row.
    """

    model_config = ConfigDict(populate_by_name=True)

    wallet_id: str
    checked_at: datetime
    passed: bool
    kill_switch_armed: bool
    kill_switch_id: str = ""
    amount_usd: Decimal | None = None
    per_tx_check: bool | None = None
    per_hour_check: bool | None = None
    per_day_check: bool | None = None
    per_protocol_check: bool | None = None
    denial_reason: str = ""

    # --- Layer-4 position-health (R-17) ---

    position_health_check: bool | None = None
    """Layer-4 position-health gate result (lending LTV + perp margin-ratio check).
    ``None`` when no open positions exist for this wallet at check time (e.g.
    first entry before any borrow). ``True`` = projected values within safety
    margins. ``False`` = trade would tip LTV above ``ltv_safety_margin`` or
    margin ratio below ``margin_safety_factor`` floor."""

    projected_ltv: Decimal | None = None
    """Projected loan-to-value ratio after this trade (lending leg only).
    Range ``[0, 1]``; ``None`` for non-lending operations (e.g. perp hedges)."""

    projected_margin_ratio: Decimal | None = None
    """Projected margin ratio after this trade (perp leg only).
    ``None`` for non-perp operations (e.g. lending deposits)."""

    position_health_denial_reason: str = ""
    """Human-readable denial reason when ``position_health_check is False``.
    E.g. ``"projected_ltv=0.87 exceeds ltv_safety_margin=0.85"``."""


class ManualInstructionPrecheckResponse(BaseModel):
    """Dry-run validation response for `POST /manual/instruction/precheck`.

    Returned to the DART UI BEFORE the operator clicks Submit, so the wallet-tier
    + capital-allocation + venue-eligibility decisions are surfaced visually
    without spending quote-asset capital. Identical inputs to `/manual/instruction`
    but `execution_mode=ManualExecutionMode.RECORD_ONLY` semantics — no order is
    routed, no fill is recorded.

    `routing_target` echoes the venue the EXECUTE flow would dispatch to (for
    DeFi this includes the chain+protocol resolution from `venue` → connector);
    operator-visible field that lets the operator double-check the dispatch path
    before committing.
    """

    model_config = ConfigDict(populate_by_name=True)

    instruction_id: str
    checked_at: datetime
    accepted: bool
    rejection_reason: str = ""
    wallet_spending_check: WalletSpendingPreCheckResult | None = None
    capital_allocation_remaining_usd: Decimal | None = None
    routing_target: str = ""
    estimated_amount_usd: Decimal | None = None


class ManualInstructionAuditLog(BaseModel):
    """Persistence shape for every operator-initiated action (manual trade + ML control).

    Single audit-log surface for both `ManualInstruction` submissions and
    `MLTrainingControlRequest` submissions. Consumed by:
    - `pnl-attribution-service` — rolls up manual fills by strategy_id alongside automated fills.
    - `batch-live-reconciliation-service` — isolates execution alpha by comparing manual vs simulated fills.
    - `alerting-service` — emits strategy_id per fired alert when manual action triggers a threshold.

    Dispatched via `action_category` (closed `ManualAuditCategory` set):
    `MANUAL_TRADE` → `manual_instruction` populated; `ml_training_*` fields None.
    `ML_TRAINING_CONTROL` → `ml_training_request` (and optionally response) populated;
    `manual_instruction` None.

    `wallet_spending_check` is populated for DeFi manual trades (wallet_id non-empty
    on the source instruction); None otherwise. The `wallet_id` top-level field
    mirrors `manual_instruction.wallet_id` to support indexed audit-log queries by
    wallet without joining through the embedded instruction body.

    Persisted by execution-service / ml-training-service at the API boundary
    BEFORE forwarding to downstream consumers (EXECUTE flow) or directly
    after recording the fill (RECORD_ONLY flow).
    """

    model_config = ConfigDict(populate_by_name=True)

    audit_id: str
    action_category: ManualAuditCategory
    persisted_at: datetime
    submitted_by: str
    asset_group: str = ""
    strategy_id: str = ""
    client_id: str = ""
    portfolio_id: str = ""
    wallet_id: str = ""
    manual_instruction: ManualInstruction | None = None
    ml_training_request: MLTrainingControlRequest | None = None
    ml_training_response: MLTrainingControlResponse | None = None
    pre_trade_check_passed: bool | None = None
    pre_trade_check_detail: str = ""
    wallet_spending_check: WalletSpendingPreCheckResult | None = None
    routed_to_venue: str = ""
    fill_reference: str = ""


__all__ = [
    "BatchExecutionMode",
    "MLTrainingControlRequest",
    "MLTrainingControlResponse",
    "ManualAuditCategory",
    "ManualExecutionMode",
    "ManualInstruction",
    "ManualInstructionAuditLog",
    "ManualInstructionPrecheckResponse",
    "ManualMLTrainingAction",
    "PositionHealthSnapshot",
    "SettlementType",
    "WalletSpendingPreCheckResult",
]

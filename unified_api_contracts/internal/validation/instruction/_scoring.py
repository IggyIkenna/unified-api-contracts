"""Integration depth scoring functions for client instructions."""

from __future__ import annotations

from ._main_models import ClientInstruction
from ._nested_models import OrderConstraints, RiskAndAllocationConstraints, SizeOrTargetExposure

# Structured-vs-free-text weight per plan §Phase 2B:
#   structured enum  = 1.0 (fully integrated)
#   hybrid           = 0.5 (e.g. has a value but no unit)
#   free text / None = 0.0 (client not integrated on this axis)
_STRUCTURED_WEIGHT = 1.0
_HYBRID_WEIGHT = 0.5
_FREETEXT_WEIGHT = 0.0


def _score_size(size: SizeOrTargetExposure) -> float:
    if size.quantity_value is not None and size.quantity_unit is not None:
        return _STRUCTURED_WEIGHT
    if size.notional_value is not None and size.notional_currency is not None:
        return _STRUCTURED_WEIGHT
    if size.target_portfolio_weight is not None:
        return _STRUCTURED_WEIGHT
    return _FREETEXT_WEIGHT


def _score_order_constraints(oc: OrderConstraints) -> float:
    # Constraints are all optional; richness = count of structured fields (max 5).
    count = 0
    if oc.price_limit is not None:
        count += 1
    if oc.max_participation_pct is not None:
        count += 1
    if oc.slippage_budget_bps is not None:
        count += 1
    if oc.time_in_force is not None:
        count += 1
    if oc.venue_restrictions:
        count += 1
    if count == 0:
        return _FREETEXT_WEIGHT
    if count >= 3:
        return _STRUCTURED_WEIGHT
    return _HYBRID_WEIGHT


def _score_risk(risk: RiskAndAllocationConstraints) -> float:
    count = 0
    if risk.per_instruction_max_loss is not None:
        count += 1
    if risk.per_client_allocation_cap is not None:
        count += 1
    if risk.kill_switch_conditions:
        count += 1
    if risk.correlation_limits:
        count += 1
    if count >= 3:
        return _STRUCTURED_WEIGHT
    if count >= 2:
        return _HYBRID_WEIGHT
    return _FREETEXT_WEIGHT


def compute_integration_depth(instruction: ClientInstruction) -> float:
    """Return integration-depth score ∈ [0, 1].

    Aggregates per-field structured-ness:
    - instrument_venue_context (always structured if present) = 1.0
    - intended_action enum = 1.0
    - size_or_target_exposure (structured by oneof invariant) = 1.0
    - timeframe_urgency enum mode + fields = 1.0
    - order_constraints: rich depth check
    - strategy_instruction_id (structured) = 1.0
    - lifecycle_replace_cancel enum = 1.0
    - risk_and_allocation_constraints rich depth check

    Ratio = sum / 8 → ∈ [0, 1].
    """

    scores = (
        _STRUCTURED_WEIGHT,  # instrument_venue_context
        _STRUCTURED_WEIGHT,  # intended_action
        _score_size(instruction.size_or_target_exposure),
        _STRUCTURED_WEIGHT,  # timeframe_urgency
        _score_order_constraints(instruction.order_constraints),
        _STRUCTURED_WEIGHT,  # strategy_instruction_id
        _STRUCTURED_WEIGHT,  # lifecycle_replace_cancel
        _score_risk(instruction.risk_and_allocation_constraints),
    )
    return round(sum(scores) / len(scores), 4)


__all__ = [
    "compute_integration_depth",
]

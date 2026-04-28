"""Client-instruction schema + validator — rule 10 + stage-3b contract.

G1.2 of ``stage-3e-refactor-plan``. The validator runs at the
execution-service edge and rejects instructions that do not conform to
stage-3b's 8-required-field shape OR that target a
(category, instrument_type, venue) tuple not declared SUPPORTED /
PARTIAL in the UAC ``ArchetypeCapability`` registry (G1.8).

Pipeline position:
    client ── POST ──► execution-service pre-handler
                            │
                            ▼
                    InstructionValidator.validate()
                            │
                ┌───────────┴───────────┐
                │                       │
          InstructionValidationResult   │
                │                       │
          integration_depth (0-1)  InstructionFieldError[]
                │                       │
          log UTL event ──► 400 structured rejection
    ``INSTRUCTION_INTEGRATION_DEPTH_OBSERVED``

Symbol naming is deliberately scoped to ``Instruction*`` to avoid
collisions with:
- ``unified_trading_library.domain.validation.ValidationResult``
  (different domain — trade-event validation).
- ``strategy_service.engine.core.validation_service`` (different
  concept — strategy-config validation).

Consumers import via the public facade ``unified_api_contracts.instruction``.

SSOT:
- ``codex/14-playbooks/infra-spec/stage-3b-instruction-schema-contract.md``
  §2 (the 8 required fields + nested validation rules).
- ``codex/14-playbooks/_ssot-rules/10-strategy-instruction-schema-principles.md``
  (rule 10 — schema depth as pricing dimension).
- ``codex/09-strategy/architecture-v2/category-instrument-coverage.md``
  (BL-1..BL-10 block-list groupings surfaced through
  ``archetypes_for_pair``).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from enum import StrEnum
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ArchetypeCapability,
    ArchetypeInstrumentType,
    archetypes_for_pair,
)
from unified_api_contracts.internal.architecture_v2.enums import VenueCategoryV2

# ---------------------------------------------------------------------------
# Action + mode enums
# ---------------------------------------------------------------------------


class InstructionAction(StrEnum):
    """Action types per stage-3b §2.2 ``intended_action`` enum."""

    BUY = "BUY"
    SELL = "SELL"
    HEDGE = "HEDGE"
    CLOSE = "CLOSE"
    ROLL = "ROLL"
    REBALANCE = "REBALANCE"
    BACK = "BACK"
    LAY = "LAY"
    LEND = "LEND"
    BORROW = "BORROW"
    STAKE = "STAKE"
    UNSTAKE = "UNSTAKE"
    BRIDGE = "BRIDGE"
    ATOMIC = "ATOMIC"


class TimeframeMode(StrEnum):
    """Timeframe urgency mode per stage-3b §2.4."""

    MARKET = "MARKET"
    LIMIT_PASSIVE = "LIMIT_PASSIVE"
    TIME_WINDOW = "TIME_WINDOW"
    SCHEDULED = "SCHEDULED"
    AT_OPEN = "AT_OPEN"
    AT_CLOSE = "AT_CLOSE"


class TimeInForce(StrEnum):
    """Time-in-force per stage-3b §2.5."""

    IOC = "IOC"
    FOK = "FOK"
    GTC = "GTC"
    GTD = "GTD"
    DAY = "DAY"


class LifecycleSemantic(StrEnum):
    """Lifecycle semantic per stage-3b §2.7."""

    NEW = "NEW"
    REPLACE = "REPLACE"
    AMEND = "AMEND"
    ADD_CHILD = "ADD_CHILD"
    CANCEL = "CANCEL"


# ---------------------------------------------------------------------------
# Nested field models — each mirrors one stage-3b required field
# ---------------------------------------------------------------------------


class InstrumentVenueContext(BaseModel):
    """§2.1 — unambiguous (instrument, venue, asset_group, instrument_type).

    ``asset_group`` is the :class:`VenueCategoryV2` value (cefi / defi / tradfi / …).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    instrument_id: str
    venue: str
    asset_group: VenueCategoryV2
    instrument_type: ArchetypeInstrumentType
    chain: str | None = None

    @model_validator(mode="after")
    def _chain_required_for_defi(self) -> InstrumentVenueContext:
        if self.asset_group == VenueCategoryV2.DEFI and not self.chain:
            raise ValueError("chain required when asset_group == DEFI")
        return self


class SizeOrTargetExposure(BaseModel):
    """§2.3 — exactly one of quantity / notional / target_portfolio_weight."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    quantity_value: Decimal | None = None
    quantity_unit: str | None = None
    notional_value: Decimal | None = None
    notional_currency: str | None = None
    target_portfolio_weight: Decimal | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def _exactly_one_populated(self) -> SizeOrTargetExposure:
        has_qty = self.quantity_value is not None and self.quantity_unit is not None
        has_notional = self.notional_value is not None and self.notional_currency is not None
        has_weight = self.target_portfolio_weight is not None
        populated = sum([has_qty, has_notional, has_weight])
        if populated != 1:
            raise ValueError("exactly one of {quantity, notional, target_portfolio_weight} must be populated")
        return self


class TimeframeUrgency(BaseModel):
    """§2.4 — mode + optional deadline + optional window."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: TimeframeMode
    deadline: str | None = None
    window_minutes: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _mode_dependent_fields(self) -> TimeframeUrgency:
        if self.mode in (TimeframeMode.TIME_WINDOW, TimeframeMode.SCHEDULED) and not self.deadline:
            raise ValueError(f"deadline required when mode == {self.mode.value}")
        if self.mode == TimeframeMode.TIME_WINDOW and self.window_minutes is None:
            raise ValueError("window_minutes required when mode == TIME_WINDOW")
        return self


class AtomicLeg(BaseModel):
    """§2.5 nested ``legs`` element — one leg of an ATOMIC bundle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    instrument_id: str
    action: InstructionAction
    size: SizeOrTargetExposure


class OrderConstraints(BaseModel):
    """§2.5 — optional price / slippage / TIF / venue restrictions / legs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    price_limit: Decimal | None = None
    max_participation_pct: Decimal | None = Field(default=None, ge=0, le=100)
    slippage_budget_bps: Decimal | None = Field(default=None, ge=0)
    venue_restrictions: tuple[str, ...] = ()
    time_in_force: TimeInForce | None = None
    legs: tuple[AtomicLeg, ...] = ()


class StrategyInstructionId(BaseModel):
    """§2.6 — (client_strategy_id, instruction_id, parent_instruction_id)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    client_strategy_id: str
    instruction_id: str
    parent_instruction_id: str | None = None

    @field_validator("client_strategy_id", "instruction_id")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must be non-empty")
        return v


class LifecycleReplaceCancel(BaseModel):
    """§2.7 — semantic + optional supersedes / parent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    semantic: LifecycleSemantic
    supersedes_instruction_id: str | None = None

    @model_validator(mode="after")
    def _semantic_dependencies(self) -> LifecycleReplaceCancel:
        if self.semantic == LifecycleSemantic.REPLACE and not self.supersedes_instruction_id:
            raise ValueError("REPLACE requires supersedes_instruction_id")
        return self


class KillSwitchCondition(BaseModel):
    """§2.8 nested ``kill_switch_conditions`` element."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: Literal["drawdown_bps", "realized_loss_usd", "venue_down", "feed_stale_sec"]
    threshold: Decimal


class CorrelationLimit(BaseModel):
    """§2.8 nested ``correlation_limits`` element."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    with_strategy_id: str
    max_joint_exposure: Decimal


class RiskAndAllocationConstraints(BaseModel):
    """§2.8 — at least one of per_instruction_max_loss /
    per_client_allocation_cap MUST be present."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    per_instruction_max_loss: Decimal | None = None
    per_client_allocation_cap: Decimal | None = None
    correlation_limits: tuple[CorrelationLimit, ...] = ()
    kill_switch_conditions: tuple[KillSwitchCondition, ...] = ()

    @model_validator(mode="after")
    def _at_least_one_risk_anchor(self) -> RiskAndAllocationConstraints:
        if self.per_instruction_max_loss is None and self.per_client_allocation_cap is None:
            raise ValueError("at least one of {per_instruction_max_loss, per_client_allocation_cap} required")
        return self


# ---------------------------------------------------------------------------
# Top-level ClientInstruction
# ---------------------------------------------------------------------------


class ClientInstruction(BaseModel):
    """Stage-3b-compliant client instruction — 8 required fields.

    All 8 must be populated for the instruction to be routable. Shape
    failure modes surface through the nested ``BaseModel.model_validate``
    machinery and are translated into ``InstructionFieldError`` rows by
    :meth:`InstructionValidator.validate`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    instrument_venue_context: InstrumentVenueContext
    intended_action: InstructionAction
    size_or_target_exposure: SizeOrTargetExposure
    timeframe_urgency: TimeframeUrgency
    order_constraints: OrderConstraints
    strategy_instruction_id: StrategyInstructionId
    lifecycle_replace_cancel: LifecycleReplaceCancel
    risk_and_allocation_constraints: RiskAndAllocationConstraints
    # Optional — carried through for pricing but not part of 8 required.
    client_id: str | None = None

    @model_validator(mode="after")
    def _atomic_requires_legs(self) -> ClientInstruction:
        if self.intended_action == InstructionAction.ATOMIC and len(self.order_constraints.legs) < 2:
            raise ValueError("ATOMIC requires legs with >= 2 legs")
        return self


# ---------------------------------------------------------------------------
# Error + result types
# ---------------------------------------------------------------------------


class InstructionFieldError(BaseModel):
    """One actionable validation error.

    Rule 10: every rejection names the violating field, the allowed
    values, and a single sentence explaining why. Consumers surface the
    full :class:`InstructionValidationResult.errors` list to clients so
    they can self-correct.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str
    violation: str
    allowed: tuple[str, ...]
    why: str


class InstructionValidationResult(BaseModel):
    """Validator output.

    Two discriminated states:

    * ``ok=True`` — instruction is stage-3b-compliant + the
      (asset_group, instrument_type, venue) tuple is declared SUPPORTED
      or PARTIAL by at least one ``ArchetypeCapability``.
      ``integration_depth`` ∈ [0, 1] is the Rule-10 pricing signal.
    * ``ok=False`` — one or more ``InstructionFieldError`` rows. The
      instruction MUST NOT be forwarded to the execution path.

    The two states are tracked by inspecting ``errors``: empty tuple =>
    ok. ``integration_depth`` on a failed result is 0.0.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ok: bool
    integration_depth: float = Field(ge=0.0, le=1.0)
    errors: tuple[InstructionFieldError, ...] = ()

    @model_validator(mode="after")
    def _ok_matches_errors(self) -> InstructionValidationResult:
        if self.ok and self.errors:
            raise ValueError("ok=True cannot carry errors")
        if not self.ok and not self.errors:
            raise ValueError("ok=False requires at least one error")
        return self


# ---------------------------------------------------------------------------
# Integration-depth scoring
# ---------------------------------------------------------------------------


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


def _compute_integration_depth(instruction: ClientInstruction) -> float:
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


# ---------------------------------------------------------------------------
# InstructionValidator — the public entry point
# ---------------------------------------------------------------------------


class InstructionValidator:
    """Stateless stage-3b-contract validator.

    ``validate()`` is the single entry point — called by the
    execution-service pre-handler middleware. All methods are pure
    functions of their arguments; construction is cheap.

    Heavy work (archetype lookup) goes through the module-level
    ``archetypes_for_pair()`` helper which consults the frozen
    ``ARCHETYPE_CAPABILITY_REGISTRY`` from G1.8.
    """

    def validate(self, instruction: ClientInstruction) -> InstructionValidationResult:
        """Return a pass/fail result for a (pre-parsed) ClientInstruction.

        Parse errors are the caller's responsibility — the middleware
        catches ``pydantic.ValidationError`` from ``model_validate`` and
        translates it into ``InstructionFieldError`` rows itself (see
        :meth:`errors_from_pydantic`). This entry point assumes a
        well-shaped :class:`ClientInstruction` and focuses on
        cross-field business rules:

        1. Is the (asset_group, instrument_type) pair declared SUPPORTED
           or PARTIAL by any registered archetype?
        2. Is the chosen venue in any matching archetype's
           ``supported_venues``?
        3. If ATOMIC, do the legs map onto a cell flagged ATOMIC-capable?

        On success — return ok=True with an
        ``integration_depth`` score. On failure — return ok=False with
        one :class:`InstructionFieldError` per violation.
        """

        errors: list[InstructionFieldError] = []
        ctx = instruction.instrument_venue_context

        matching = archetypes_for_pair(
            ctx.asset_group,
            ctx.instrument_type,
            include_partial=True,
        )
        pair_error = self._validate_pair(ctx, matching)
        if pair_error is not None:
            errors.append(pair_error)

        if matching:
            venue_error = self._validate_venue(ctx, matching)
            if venue_error is not None:
                errors.append(venue_error)

        if errors:
            return InstructionValidationResult(
                ok=False,
                integration_depth=0.0,
                errors=tuple(errors),
            )

        return InstructionValidationResult(
            ok=True,
            integration_depth=_compute_integration_depth(instruction),
            errors=(),
        )

    @staticmethod
    def _validate_pair(
        ctx: InstrumentVenueContext,
        matching: Sequence[ArchetypeCapability],
    ) -> InstructionFieldError | None:
        """Pair must be declared SUPPORTED or PARTIAL by some archetype."""

        if matching:
            return None
        return InstructionFieldError(
            field="instrument_venue_context.asset_group+instrument_type",
            violation=(f"no registered archetype supports ({ctx.asset_group.value}, {ctx.instrument_type.value})"),
            allowed=_allowed_pairs_digest(),
            why=(
                "UAC ArchetypeCapabilityRegistry has zero SUPPORTED or PARTIAL "
                "cells for this pair — routing would land in a BL-* block-list "
                "group (see codex/09-strategy/architecture-v2/"
                "category-instrument-coverage.md)."
            ),
        )

    @staticmethod
    def _validate_venue(
        ctx: InstrumentVenueContext,
        matching: Sequence[ArchetypeCapability],
    ) -> InstructionFieldError | None:
        """Venue must be in supported_venues of at least one matching archetype."""

        allowed_venues: set[str] = set()
        for archetype in matching:
            allowed_venues.update(archetype.supported_venues)
        if ctx.venue in allowed_venues:
            return None
        return InstructionFieldError(
            field="instrument_venue_context.venue",
            violation=(
                f"venue {ctx.venue!r} not in supported_venues for any "
                f"archetype covering ({ctx.asset_group.value}, "
                f"{ctx.instrument_type.value})"
            ),
            allowed=tuple(sorted(allowed_venues)),
            why=(
                "Venue must appear in at least one non-BLOCKED cell of a "
                "matching ArchetypeCapability row. Check "
                "archetype_capability_manifest.json for the authoritative "
                "venue list."
            ),
        )

    @staticmethod
    def errors_from_pydantic(
        pydantic_errors: Sequence[dict[str, object]],
    ) -> tuple[InstructionFieldError, ...]:
        """Translate ``pydantic.ValidationError.errors()`` output.

        Utility for middleware that does ``ClientInstruction.model_validate``
        on the raw payload and catches ``ValidationError``. Each pydantic
        row becomes one :class:`InstructionFieldError` so the caller can
        return a uniformly-shaped 400 regardless of whether the failure
        came from structural parsing or business-rule validation.
        """

        out: list[InstructionFieldError] = []
        for err in pydantic_errors:
            loc_raw: object = err.get("loc", ())
            if isinstance(loc_raw, tuple | list):
                parts = cast("tuple[object, ...] | list[object]", loc_raw)
                field_path = ".".join(str(part) for part in parts)
            else:
                field_path = str(loc_raw)
            msg = str(err.get("msg", "validation failed"))
            err_type = str(err.get("type", "value_error"))
            out.append(
                InstructionFieldError(
                    field=field_path or "<root>",
                    violation=msg,
                    allowed=(),
                    why=(
                        "Pydantic-layer rejection — see stage-3b §2 for the authoritative "
                        f"field contract. Error type: {err_type}."
                    ),
                )
            )
        return tuple(out)


def _allowed_pairs_digest() -> tuple[str, ...]:
    """Deterministic flat list of (asset_group, instrument_type) pair names.

    Used in error copy so clients see a concrete allowed-value hint
    without pulling the full manifest in. Non-exhaustive on purpose —
    the manifest is the SSOT.
    """

    # Hand-picked representative pairs — ordered, deduplicated.
    return (
        "CEFI:spot",
        "CEFI:perp",
        "CEFI:option",
        "CEFI:dated_future",
        "DEFI:spot",
        "DEFI:perp",
        "DEFI:lending",
        "DEFI:staking",
        "DEFI:lp",
        "TRADFI:spot",
        "TRADFI:option",
        "TRADFI:dated_future",
        "SPORTS:event_settled",
        "PREDICTION:event_settled",
    )


__all__ = [
    "AtomicLeg",
    "ClientInstruction",
    "CorrelationLimit",
    "InstructionAction",
    "InstructionFieldError",
    "InstructionValidationResult",
    "InstructionValidator",
    "InstrumentVenueContext",
    "KillSwitchCondition",
    "LifecycleReplaceCancel",
    "LifecycleSemantic",
    "OrderConstraints",
    "RiskAndAllocationConstraints",
    "SizeOrTargetExposure",
    "StrategyInstructionId",
    "TimeInForce",
    "TimeframeMode",
    "TimeframeUrgency",
]

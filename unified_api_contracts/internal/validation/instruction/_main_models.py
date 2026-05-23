"""Main client instruction model and error/result types."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ._enums import InstructionAction
from ._nested_models import (
    InstrumentVenueContext,
    LifecycleReplaceCancel,
    OrderConstraints,
    RiskAndAllocationConstraints,
    SizeOrTargetExposure,
    StrategyInstructionId,
    TimeframeUrgency,
)


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


__all__ = [
    "ClientInstruction",
    "InstructionFieldError",
    "InstructionValidationResult",
    "errors_from_pydantic",
]

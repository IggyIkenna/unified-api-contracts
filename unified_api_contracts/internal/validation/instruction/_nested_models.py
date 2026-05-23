"""Nested field models for client instruction validation."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ArchetypeInstrumentType,
)
from unified_api_contracts.internal.architecture_v2.enums import VenueCategoryV2

from ._enums import InstructionAction, LifecycleSemantic, TimeframeMode, TimeInForce


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


__all__ = [
    "AtomicLeg",
    "CorrelationLimit",
    "InstrumentVenueContext",
    "KillSwitchCondition",
    "LifecycleReplaceCancel",
    "OrderConstraints",
    "RiskAndAllocationConstraints",
    "SizeOrTargetExposure",
    "StrategyInstructionId",
    "TimeframeUrgency",
]

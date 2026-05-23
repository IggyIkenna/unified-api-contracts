"""Scenario mutation specifications — typed discriminated union for mutations."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class _MutationBase(BaseModel):
    """Common base — frozen + extra-forbid + discriminator literal in each subclass."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class PriceShift(_MutationBase):
    """Shift a price-like value by a target delta. Funding-rate / mid-price / peg-price all use this."""

    mutation_type: Literal["PriceShift"] = "PriceShift"
    target_value_bps: Decimal
    """Absolute target value in bps (e.g. 100 = 0.1%/period for funding)."""
    baseline_bps: Decimal | None = Field(default=None)
    """Optional baseline for delta-mode; ``None`` = absolute-target mode."""
    duration_seconds: int = Field(gt=0)
    recovery_curve: Literal["step", "linear", "exponential_decay", "ramp"] = "step"


class StaleHold(_MutationBase):
    """Freeze last value emitted — emulates feed staleness past heartbeat."""

    mutation_type: Literal["StaleHold"] = "StaleHold"
    stale_duration_seconds: int = Field(gt=0)
    heartbeat_count: int | None = Field(default=None, gt=0)
    """If set: number of heartbeats to skip (preferred over absolute seconds for feeds with non-uniform heartbeat)."""


class LatencyInject(_MutationBase):
    """Add fixed/variable latency on a pipeline edge."""

    mutation_type: Literal["LatencyInject"] = "LatencyInject"
    added_latency_seconds: Decimal = Field(gt=0)
    duration_seconds: int = Field(gt=0)
    recovery_curve: Literal["step", "linear", "exponential_decay"] = "step"


class BookSpoof(_MutationBase):
    """Inject synthetic book imbalance / liquidity withdrawal."""

    mutation_type: Literal["BookSpoof"] = "BookSpoof"
    book_depth_scale: Decimal = Field(gt=0, le=1)
    """0..1 multiplier on book depth (e.g. 0.3 = withdraw 70% of LP liquidity)."""
    duration_seconds: int = Field(gt=0)
    imbalance_target: Decimal | None = Field(default=None, ge=-1, le=1)
    """Optional book-imbalance target in [-1, 1]."""


class RejectFills(_MutationBase):
    """Force matching-engine to reject fills with a typed reason."""

    mutation_type: Literal["RejectFills"] = "RejectFills"
    reject_rate: Decimal = Field(ge=0, le=1)
    """0..1 fraction of fills to reject."""
    duration_seconds: int = Field(gt=0)
    reject_reason: str
    """Typed reject reason (e.g. ``"BorrowCapExceeded"`` / ``"PoolPaused"`` / ``"VenueHalted"``)."""


class OracleDeviate(_MutationBase):
    """Wild-print or sustained-deviation oracle mutation. Distinct from StaleHold."""

    mutation_type: Literal["OracleDeviate"] = "OracleDeviate"
    deviation_sigma: Decimal
    """30sigma for the canonical worst case; sign indicates direction."""
    deviation_duration_heartbeats: int = Field(gt=0)
    oracle_id: str
    """Oracle-feed identifier (e.g. `pyth_solana_usdc`, Chainlink aggregator address)."""


class GasSurge(_MutationBase):
    """Spike gas / priority-fee on a chain."""

    mutation_type: Literal["GasSurge"] = "GasSurge"
    surge_multiplier: Decimal = Field(gt=1)
    """Multiplier over baseline (e.g. 50 = 50x spike)."""
    baseline_gwei: Decimal = Field(gt=0)
    surge_duration_seconds: int = Field(gt=0)
    recovery_curve: Literal["step", "linear", "exponential_decay"] = "linear"


class DropRows(_MutationBase):
    """Drop rows entirely from raw-tick or feature output."""

    mutation_type: Literal["DropRows"] = "DropRows"
    drop_rate: Decimal = Field(ge=0, le=1)
    duration_seconds: int = Field(gt=0)


class EventDrop(_MutationBase):
    """Drop named events from the event stream."""

    mutation_type: Literal["EventDrop"] = "EventDrop"
    event_types: frozenset[str]
    duration_seconds: int = Field(gt=0)


class EventDuplicate(_MutationBase):
    """Duplicate a synthetic event payload onto the stream."""

    mutation_type: Literal["EventDuplicate"] = "EventDuplicate"
    event_type: str
    payload_template: str
    """Operator-readable payload template for the synthetic event (parsed at apply-time by UTL applier)."""


class ManifestPhantom(_MutationBase):
    """Inject a synthetic manifest row at a target (asset_group, venue, data_type, day, ...)."""

    mutation_type: Literal["ManifestPhantom"] = "ManifestPhantom"
    target_capture_status: Literal["captured", "empty_confirmed", "attempted_failed", "expected_unattempted"]
    target_value: Decimal | None = Field(default=None)
    """Optional manifest-row value (e.g. utilization=0.99 for lending-indices phantoms)."""


ScenarioMutationSpec = Annotated[
    PriceShift
    | StaleHold
    | LatencyInject
    | BookSpoof
    | RejectFills
    | OracleDeviate
    | GasSurge
    | DropRows
    | EventDrop
    | EventDuplicate
    | ManifestPhantom,
    Field(discriminator="mutation_type"),
]
"""Discriminated union over the 11 mutation types.

Per `simulation_scenarios_topology_price_shocks_2026_05_09.md` Phase 1.B
compressed-scope: 5 mutations shipped pre-cutover. Day-1 scenario design
surfaced needs for all 11 — shipping all in one pass.

Adding new mutation types: append a new ``_MutationBase`` subclass + a new
discriminator literal + extend the union. UTL applier per Phase 2.A MUST
add a corresponding ``apply_<mutation>()`` method in the same logical unit
(per Citadel-Grade Pre-Audit).
"""


__all__ = [
    "BookSpoof",
    "DropRows",
    "EventDrop",
    "EventDuplicate",
    "GasSurge",
    "LatencyInject",
    "ManifestPhantom",
    "OracleDeviate",
    "PriceShift",
    "RejectFills",
    "ScenarioMutationSpec",
    "StaleHold",
]

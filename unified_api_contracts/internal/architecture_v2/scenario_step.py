"""Scenario stepper contracts — deterministic single-step audit of a v2 archetype.

The scenario stepper (``e2e-testing/scripts/strategy/scenario_stepper.py``) drives
the REAL v2 archetype engine loop (``V2BatchHarness.on_tick`` — the batch=live code
path) with a synthetic market state the operator steers by hand, plus benchmark
fills, and captures the engine's per-step emissions into these models.

This module owns ONLY the step-level I/O contract:

* :class:`StepInput`   — user-supplied key numbers (keyed by ``(venue, feature)``)
  plus an RNG seed for unspecified-value fillers.
* :class:`TriggerEvaluation` — one armed predicate's value-vs-threshold + fired flag
  + distance-to-trigger (the "DAILY_LOSS_BREACH arms at -5%, you are at -1.2%" line).
* :class:`StepReport`  — the per-step engine emission capture: instructions, fills,
  position deltas, PnL delta, trigger evaluations, and risk-gate decisions per
  :class:`RiskGateLayer`.
* :class:`ScenarioSession` — a config reference + an ordered list of step reports.

Determinism contract: given the same ``(config, [StepInput...], rng_seed)`` the
stepper produces byte-identical :class:`StepReport` sequences. The only sources of
non-determinism (unspecified market values) are drawn from a seeded RNG carried on
each :class:`StepInput`.

Instruction models are REUSED, not duplicated — the captured ``instructions_emitted``
hold the JSON dump of the existing
``unified_api_contracts.internal.architecture_v2.schemas.StrategyInstructionEnvelope``
subclasses (TradeInstruction / SwapInstruction / LendInstruction / …). Risk-gate
results reuse :class:`RiskGateLayer` / :class:`RiskGateDecision`; kill-switch reasons
reuse :class:`KillSwitchReason`; benchmark fills reuse :class:`BenchmarkFillMode`.

Codex SSOT:
  ``codex/09-strategy/architecture-v2/capability-wizard.md`` (§ "Phase 3.5 stepper")
Plan:
  ``plans/active/capability_wizard_and_manifest_2026_06_11.md`` Phase 3.5 [SPEC] P1.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.internal.architecture_v2.enums import (
    BenchmarkFillMode,
    KillSwitchReason,
    RiskGateDecision,
    RiskGateLayer,
    StrategyArchetype,
)

# ---------------------------------------------------------------------------
# Trigger taxonomy
# ---------------------------------------------------------------------------


class TriggerKind(StrEnum):
    """The class of decision-tree branch a :class:`TriggerEvaluation` reports.

    These are the predicate families the stepper enumerates from the configured
    archetype + risk thresholds. ``ENTRY`` / ``EXIT`` / ``REBALANCE`` are
    engine-internal predicates read from config thresholds; ``STOP_LOSS`` /
    ``KILL_SWITCH`` are protective predicates fired by the runtime risk layer
    (the engine exposes the post-fire ``flatten_on_kill`` emission, not the
    predicate itself — see the ``introspection_gap`` field on :class:`StepReport`).
    """

    ENTRY = "entry"
    """Position-open predicate (e.g. net carry >= entry_bps; dispersion >= min_bps)."""

    EXIT = "exit"
    """Position-close predicate (e.g. net carry <= exit_bps)."""

    STOP_LOSS = "stop_loss"
    """Protective per-position loss limit (runtime-fired)."""

    REBALANCE = "rebalance"
    """Hedge-ratio / leg-rebalance predicate (e.g. health_factor < min_health_factor)."""

    KILL_SWITCH = "kill_switch"
    """Firm-/strategy-level protective halt; carries a :class:`KillSwitchReason`."""


# ---------------------------------------------------------------------------
# Step input — what the operator steers
# ---------------------------------------------------------------------------


class StepInput(BaseModel):
    """One step's user-supplied key numbers + RNG seed for fillers.

    ``feature_values`` keys are ``(venue, feature)`` pairs flattened to a single
    string ``"<venue>:<feature>"`` (e.g. ``"binance:mid_price_binance"``,
    ``"_:funding_rate_apy_bps"`` where ``_`` is the no-venue sentinel) so a JSON
    object can carry them. The stepper resolves the keys into the
    ``dict[str, float]`` features the engine ``on_tick`` consumes; any feature the
    archetype reads but the operator did not supply is filled from a seeded RNG.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_index: int = Field(
        ...,
        ge=0,
        description="Zero-based position of this step in the scenario sequence.",
    )
    mark_price: Decimal | None = Field(
        default=None,
        description=(
            "Mark/mid price for the engine's subscribed instrument this step "
            "(the ``mid_price`` argument to ``on_tick``). None → seeded-RNG filler."
        ),
    )
    feature_values: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "User-supplied key numbers keyed by ``'<venue_or_underscore>:<feature>'`` "
            "(funding_rate_apy_bps, staking_apy_bps, mid_price_<venue>, health_factor, "
            "spot prices, feature values). Overrides any seeded-RNG filler."
        ),
    )
    forced_kill_switch: KillSwitchReason | None = Field(
        default=None,
        description=(
            "When set, the stepper fires this kill-switch reason on the engine THIS "
            "step (protective path), capturing flatten_on_kill emissions. Models the "
            "runtime risk layer tripping a firm-level halt."
        ),
    )
    rng_seed: int = Field(
        default=0,
        description=(
            "Seed for the deterministic filler RNG used for any engine-read feature "
            "the operator did not supply. Same seed + inputs → identical StepReport."
        ),
    )
    note: str = Field(
        default="",
        description="Free-text operator annotation for this step (echoed into the report).",
    )


# ---------------------------------------------------------------------------
# Trigger evaluation — one armed predicate's resolution
# ---------------------------------------------------------------------------


class TriggerEvaluation(BaseModel):
    """One armed predicate's value-vs-threshold resolution for a single step.

    ``distance_to_trigger`` is signed in the threshold's own units (bps, ratio, …)
    and is the headroom before the predicate fires — e.g. ``DAILY_LOSS_BREACH arms
    at -5%, you are at -1.2%`` → ``threshold=-5.0, current_value=-1.2,
    distance_to_trigger=3.8`` (still 3.8% of room). It is None when the trigger has
    no numeric threshold the stepper can read (an ``introspection_gap`` case).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: TriggerKind = Field(..., description="The decision-tree branch family this evaluates.")
    label: str = Field(
        ...,
        description="Human-readable predicate name (e.g. 'net_carry_entry', 'health_factor_rebalance').",
    )
    kill_switch_reason: KillSwitchReason | None = Field(
        default=None,
        description="The KillSwitchReason this trigger maps to, when kind == KILL_SWITCH; else None.",
    )
    threshold: Decimal | None = Field(
        default=None,
        description="The armed threshold in its native units; None when the predicate exposes no readable threshold.",
    )
    current_value: Decimal | None = Field(
        default=None,
        description="The current observed value compared against the threshold; None when not observable.",
    )
    distance_to_trigger: Decimal | None = Field(
        default=None,
        description="Signed headroom (current_value vs threshold) before the predicate fires; None if unreadable.",
    )
    fired: bool = Field(..., description="True iff the predicate resolved true (or the kill switch tripped) this step.")
    introspection_gap: bool = Field(
        default=False,
        description=(
            "True when the engine does not expose this predicate under LOGIC FREEZE, so the "
            "stepper reports it derived-from-config rather than read from the engine — a gap to "
            "close with engine-side predicate tracing post-unfreeze."
        ),
    )


# ---------------------------------------------------------------------------
# Risk-gate decision capture (per RiskGateLayer)
# ---------------------------------------------------------------------------


class RiskGateDecisionRecord(BaseModel):
    """A single risk-gate layer's decision captured for a step.

    Mirrors the engine's ``RiskGateResult`` dataclass (which is not a pydantic
    model) into a serialisable report row, keyed by :class:`RiskGateLayer`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    layer: RiskGateLayer = Field(..., description="Which risk-gate layer produced this decision.")
    decision: RiskGateDecision = Field(..., description="APPROVED / REJECTED / RESIZED / DEFERRED.")
    reason: str = Field(
        default="", description="Free-text rationale emitted by the gate (e.g. 'killed:DAILY_LOSS_BREACH')."
    )
    suggested_size: Decimal | None = Field(
        default=None,
        description="Resized order size when decision == RESIZED; else None.",
    )


# ---------------------------------------------------------------------------
# Fill capture (benchmark fills)
# ---------------------------------------------------------------------------


class StepFill(BaseModel):
    """A single benchmark fill produced for an instruction this step.

    Benchmark fills are deterministic reference-price simulations (no venue I/O);
    the ``fill_mode`` reuses the canonical :class:`BenchmarkFillMode` per action.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    instruction_id: str = Field(..., description="The emitting instruction's id.")
    instrument: str = Field(..., description="Instrument the fill is for.")
    venue: str = Field(default="", description="Venue the fill executed against (benchmark venue token).")
    side: str = Field(default="", description="BUY / SELL / LEND / STAKE / … (the instruction action's side).")
    quantity: Decimal = Field(..., description="Filled quantity in instrument units.")
    price: Decimal = Field(..., description="Benchmark reference fill price.")
    fill_mode: BenchmarkFillMode = Field(..., description="The benchmark fill mode used (per-action canonical).")
    notional_usd: Decimal = Field(default=Decimal("0"), description="Signed USD notional of the fill (quantity*price).")


# ---------------------------------------------------------------------------
# Step report — the per-step capture
# ---------------------------------------------------------------------------


class StepReport(BaseModel):
    """The deterministic capture of one engine tick under steered inputs.

    Holds everything the engine emitted this step plus the derived trigger map.
    ``instructions_emitted`` are JSON dumps of the existing
    ``StrategyInstructionEnvelope`` subclasses (reused, never re-declared).
    ``introspection_gaps`` names every predicate the stepper could NOT read off the
    engine (LOGIC FREEZE) and reported from config instead.
    """

    model_config = ConfigDict(extra="forbid")

    step_index: int = Field(..., ge=0, description="Zero-based step position, echoing the StepInput.")
    timestamp_utc: datetime = Field(..., description="The synthetic UTC tick timestamp passed to the engine.")
    mark_price: Decimal = Field(..., description="The mark/mid price used for the engine's subscribed instrument.")
    instructions_emitted: list[dict[str, object]] = Field(
        default_factory=list,
        description=(
            "JSON dumps (model_dump(mode='json')) of the StrategyInstructionEnvelope subclasses the "
            "engine emitted this step. Reused UAC instruction models — never duplicated here."
        ),
    )
    fills: list[StepFill] = Field(
        default_factory=list, description="Benchmark fills produced for the emitted instructions."
    )
    position_deltas: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Per-position-key change in units this step (post-tick minus pre-tick harness position state).",
    )
    position_state: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Full post-tick harness position snapshot (key → units).",
    )
    pnl_delta_usd: Decimal = Field(
        default=Decimal("0"),
        description="Change in mark-to-market PnL (USD) attributable to this step's fills + price move.",
    )
    cumulative_pnl_usd: Decimal = Field(
        default=Decimal("0"),
        description="Running session PnL (USD) through this step inclusive.",
    )
    trigger_evaluations: list[TriggerEvaluation] = Field(
        default_factory=list,
        description="Every armed predicate's value-vs-threshold resolution + distance-to-trigger for this step.",
    )
    risk_gate_decisions: list[RiskGateDecisionRecord] = Field(
        default_factory=list,
        description="Risk-gate decisions captured per RiskGateLayer for this step (≥ the STRATEGY_SELF_CHECK).",
    )
    killed: bool = Field(default=False, description="True iff the engine is in the killed state after this step.")
    kill_reason: KillSwitchReason | None = Field(
        default=None,
        description="The KillSwitchReason the engine is halted on, when killed; else None.",
    )
    introspection_gaps: list[str] = Field(
        default_factory=list,
        description=(
            "Predicate labels the stepper derived from config because the engine does not expose them "
            "under LOGIC FREEZE (engine-side predicate tracing is the post-unfreeze enhancement)."
        ),
    )
    note: str = Field(default="", description="The operator annotation echoed from the StepInput.")


# ---------------------------------------------------------------------------
# Scenario session — config ref + ordered steps
# ---------------------------------------------------------------------------


class ScenarioConfigRef(BaseModel):
    """Minimal reference to the strategy config a session was stepped against.

    Loosely aligned with what the capability wizard will emit (Phase 4): an
    archetype id, the venues/instruments scope, capital, and the risk thresholds
    the trigger map is derived from. The stepper resolves this into a real engine
    via ``V2BatchHarness`` — it is NOT a parallel mini-engine.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    archetype_id: StrategyArchetype = Field(..., description="The v2 archetype the engine instantiates.")
    strategy_type: str = Field(
        default="",
        description="Optional STRATEGY_TYPE_TO_SLOT registry key (colocated path); blank when slot_label is used.",
    )
    slot_label: str = Field(default="", description="Explicit v2 slot label, when not resolving via strategy_type.")
    venues: list[str] = Field(
        default_factory=list, description="Venues in scope (drives the candidate/feature universe)."
    )
    instruments: list[str] = Field(default_factory=list, description="Instruments in scope.")
    capital_usd: Decimal = Field(..., gt=0, description="Initial strategy equity (USD).")
    risk_thresholds: dict[str, Decimal] = Field(
        default_factory=dict,
        description=(
            "Threshold name → value, the source of the derived trigger map "
            "(entry_bps, exit_bps, min_health_factor, daily_loss_breach_pct, max_drawdown_pct, …)."
        ),
    )


class ScenarioSession(BaseModel):
    """A full stepper run: the config reference + the ordered step reports.

    Deterministic given ``(config, [inputs], seed)``. Serialises to the JSON the
    stepper writes in ``--steps`` mode and the UI renders as a timeline (Phase 4).
    """

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., description="Stable id for this stepper run (uuid or operator-supplied).")
    config: ScenarioConfigRef = Field(..., description="The strategy config the session was stepped against.")
    started_at_utc: datetime = Field(..., description="When the session run began (UTC).")
    steps: list[StepReport] = Field(default_factory=list, description="Ordered per-step capture, one per StepInput.")
    final_pnl_usd: Decimal = Field(
        default=Decimal("0"), description="Cumulative session PnL (USD) after the last step."
    )
    kill_switch_tripped: bool = Field(
        default=False,
        description="True iff any step left the engine in the killed state (a kill-switch trip occurred).",
    )


__all__ = [
    "RiskGateDecisionRecord",
    "ScenarioConfigRef",
    "ScenarioSession",
    "StepFill",
    "StepInput",
    "StepReport",
    "TriggerEvaluation",
    "TriggerKind",
]

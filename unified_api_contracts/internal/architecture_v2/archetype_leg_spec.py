"""Archetype leg-spec registry — structural per-leg restriction model (F22).

WHY THIS MODULE EXISTS (operator-caught in the live capability wizard, 2026-06-11):
``ARCHETYPE_CAPABILITY_REGISTRY`` (``archetype_capability.py`` +
``archetype_capability_manifest.json``) models a multi-leg archetype like
``CARRY_STAKED_BASIS`` as ONE cell ``(DEFI, staking)``. The real 3-leg structure
(stake + lend + perp hedge) lives only in the cell's prose ``notes``, and the
CeFi/DeFi perp hedge venues are mixed undifferentiated into a flat ``venue_ids``
list with no per-leg ``instrument_type`` or leg role. The wizard therefore offered
only "Staking" as an instrument type for a basis trade.

The engine, by contrast, DOES know the legs structurally —
``CarryStakedBasisEngine._build_legs`` emits SWAP(spot) + STAKE + TRANSFER + TRADE
(perp short), and ``_derive_structure`` gates on
``accepted_perp_collateral(perp_venue)`` (the staked-vs-straight-basis conditional).
This module makes that structural truth a first-class, queryable UAC registry so the
wizard, prospectus and capability manifest can render exhaustive per-leg
restrictions instead of prose.

DUAL-REPRESENTATION (read this before touching either side) — F22 / F4:
  This registry is the NEW SSOT for **leg truth** (per-archetype structural legs:
  role, instrument types, asset groups, venue eligibility, conditional collateral
  constraints). ``ARCHETYPE_CAPABILITY_REGISTRY`` / ``archetype_capability_manifest.json``
  remains the SSOT for the **flat coverage cell matrix** that existing consumers
  (UI ``coverage.ts``, strategy-service instruction validation, the capability
  manifest exporter) depend on. The two intentionally OVERLAP and, for the seeded
  multi-leg archetypes, the cell model is a lossy flattening of the leg model — e.g.
  ``CARRY_STAKED_BASIS`` is one ``(DEFI, staking)`` cell here but three legs
  (spot_long, stake, hedge_short) there. This pass does NOT rewrite the cell registry
  / JSON (F4: the JSON is SSOT with no drift check; consumers depend on it). The
  capability-manifest exporter **bridges** the two: it emits leg nodes/edges from
  this registry while still emitting cell edges from the cell registry, and flags
  archetypes whose cell ``notes`` imply legs ("ATOMIC"/"hedge"/"+") but lack a leg
  spec here.

FOLLOW-UP (named, F22): the cell model should eventually be DERIVED FROM the leg
specs (flatten legs → ``(asset_group, instrument_type)`` cells) so there is a single
authored source. That derivation + a parity drift-check between the two
representations is the next tranche — tracked in
``plans/active/issues/capability_wizard_analysis_findings_2026_06_11.md`` F22.

PHASE 6A — EXHAUSTIVE 57-ARCHETYPE COVERAGE: the per-archetype seed builders live
in the sibling ``archetype_leg_spec_seeds`` module (split out so the full backfill
fits the file cap). ``ARCHETYPE_LEG_STRUCTURES`` enumerates EVERY one of the 57
``StrategyArchetype`` values — a real leg structure where derivable from
engine/doc/cells, an explicit ``not_registered`` structure (``legs=()`` +
``not_registered_reason``) where genuinely underivable (a meta-allocation overlay
or an archetype intentionally absent from the strategy factory). There are NO
absent keys; ``archetypes_without_leg_structures()`` returns the not_registered set.

LOGIC FREEZE: every seeded leg is a *citation of* the shipped engine structure +
codex archetype docs + existing manifest cells (cited per leg in
``source_of_truth``). They DO NOT change any engine behaviour. Numbers / venues
come only from those three sources.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, model_validator

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ArchetypeInstrumentType,
)
from unified_api_contracts.internal.architecture_v2.enums import (
    AtomicExecutionMode,
    StrategyArchetype,
    VenueCategoryV2,
)

# ---------------------------------------------------------------------------
# Leg role + constraint vocabulary (closed sets)
# ---------------------------------------------------------------------------


class ArchetypeLegRole(StrEnum):
    """The structural role a leg plays in a multi-leg archetype.

    Closed set derived from what the carry / arbitrage / market-making families
    actually emit in the shipped engines (NOT a speculative superset):

    - ``stake`` / ``lend`` / ``borrow`` — the carry-and-yield on-chain legs.
      ``CarryStakedBasisEngine`` emits STAKE; ``CarryRecursiveStakedEngine``
      emits the STAKE→LEND→BORROW loop (``recursive_staked._build_loop_legs``).
    - ``spot_long`` / ``spot_short`` — the spot leg. The staked-basis SWAP
      (USDC→ETH leader) is a ``spot_long``; ``ArbitragePriceDispersionEngine``
      emits a BUY (``spot_long``) + SELL (``spot_short``) cross-venue pair.
    - ``hedge_short`` — the delta-cancelling short leg (the perp hedge in a
      staked basis; ``CarryStakedBasisEngine`` TRADE leg ``role=hedge``).
    - ``perp_long`` / ``perp_short`` — a perp leg taken for its own funding edge
      (``CarryBasisPerpEngine`` — direction flips on funding sign).
    - ``future_long`` / ``future_short`` — a dated-future leg
      (``CarryBasisDatedEngine`` TRADE leg ``leg_type=FUTURE``).
    - ``lp_provide`` — an AMM liquidity-provision leg (DeFi LP / MM families,
      and the arbitrage flash-loan LP cell).

    ``transfer`` / ``bridge`` are deliberately NOT roles: they are capital
    *movements* between venues, not positions a leg holds. The staked-basis
    TRANSFER(LST→perp) is modelled as the ``execution_coupling`` between the
    ``stake`` leg and the ``hedge_short`` leg, not as its own leg.
    """

    STAKE = "stake"
    LEND = "lend"
    BORROW = "borrow"
    SPOT_LONG = "spot_long"
    SPOT_SHORT = "spot_short"
    HEDGE_SHORT = "hedge_short"
    PERP_LONG = "perp_long"
    PERP_SHORT = "perp_short"
    FUTURE_LONG = "future_long"
    FUTURE_SHORT = "future_short"
    LP_PROVIDE = "lp_provide"


class LegConstraintKind(StrEnum):
    """The kind of conditional structural constraint a leg can carry.

    Closed set derived from the shipped engine gates:

    - ``requires_collateral_acceptance`` — the leg is only structurally valid
      when a venue accepts a specific asset as collateral. THE staked-basis
      conditional: ``CarryStakedBasisEngine._derive_structure`` gates the whole
      slot on ``accepted_perp_collateral(perp_venue)`` containing the LST. When
      it does NOT, the archetype degrades to its ``fallback_variant``
      (``straight_basis`` = the LST/stake leg is dropped, leaving a perp-funding
      carry == ``CARRY_BASIS_PERP``). ``params``: ``asset`` (the LST/collateral
      token, or a slot-label token), ``venue_role`` (which leg's venue must
      accept it, e.g. ``hedge_short``).
    - ``requires_same_venue`` — two legs must execute on the SAME venue (e.g. a
      single-venue netted basis: spot + perp on one CEX for capital efficiency,
      per the ``CARRY_BASIS_PERP`` cell note "single-venue netted"). ``params``:
      ``other_leg_id``.
    - ``requires_atomic_bundle`` — the leg must execute atomically with the
      bundle (revert-all-or-nothing). The recursive-staked loop is
      ``ATOMIC_ON_CHAIN``; the arbitrage same-chain pair is ``ATOMIC``.
      ``params``: ``bundle_id`` (a free label grouping the co-atomic legs).
    """

    REQUIRES_COLLATERAL_ACCEPTANCE = "requires_collateral_acceptance"
    REQUIRES_SAME_VENUE = "requires_same_venue"
    REQUIRES_ATOMIC_BUNDLE = "requires_atomic_bundle"


# ---------------------------------------------------------------------------
# Constraint + leg + structure models
# ---------------------------------------------------------------------------


class LegConstraint(BaseModel):
    """A typed conditional constraint attached to a leg.

    The conditional that makes the staked-basis restriction exhaustive rather
    than prose: it encodes *when* a leg is structurally valid and *what the
    archetype degrades to* when the condition fails.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: LegConstraintKind = Field(
        description=(
            "The kind of conditional constraint (collateral-acceptance, "
            "same-venue, atomic-bundle). Drives the wizard's conditional "
            "surfacing + the exporter's constraint-edge metadata."
        )
    )
    params: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Constraint parameters keyed by name. For "
            "``requires_collateral_acceptance``: ``asset`` (the token that must "
            "be accepted as collateral) + ``venue_role`` (which leg's venue must "
            "accept it). For ``requires_same_venue``: ``other_leg_id``. For "
            "``requires_atomic_bundle``: ``bundle_id``. Values are strings."
        ),
    )
    fallback_variant: str | None = Field(
        default=None,
        description=(
            "What the archetype degrades to when the constraint is NOT met, if "
            "the degraded form is still a valid (different) structure. For the "
            "staked-basis collateral conditional this is ``'straight_basis'`` — "
            "the LST/stake leg is dropped and the position runs as a plain "
            "perp-funding basis (== CARRY_BASIS_PERP). ``None`` when failing the "
            "constraint simply rejects the slot with no fallback."
        ),
    )
    description: str = Field(
        description=(
            "Human-readable statement of the conditional, rendered verbatim in "
            "the wizard ('on venues where the LST is not accepted as perp "
            "collateral, this archetype runs straight basis') and the prospectus."
        )
    )


class ArchetypeLegSpec(BaseModel):
    """One structural leg of a multi-leg archetype.

    Reuses the existing UAC vocabularies (``ArchetypeInstrumentType``,
    ``VenueCategoryV2``) so leg-level truth lines up 1:1 with the flat cell
    model it refines.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    leg_id: str = Field(
        description=(
            "Stable identifier for this leg within its archetype "
            "(e.g. ``'spot'``, ``'stake'``, ``'hedge'``, ``'loop'``, ``'buy'``, "
            "``'sell'``). Referenced by other legs' ``requires_same_venue`` "
            "constraints. Never reassigned."
        )
    )
    role: ArchetypeLegRole = Field(
        description="The structural role this leg plays (stake / hedge_short / spot_long / …)."
    )
    required: bool = Field(
        description=(
            "Whether this leg is mandatory for the archetype to be the archetype. "
            "A non-required leg is one the engine may drop in a degraded variant "
            "(e.g. the staked-basis ``stake`` leg is dropped in straight-basis "
            "fallback). Mandatory legs are pre-selected + non-deselectable in the "
            "wizard."
        )
    )
    instrument_types: tuple[ArchetypeInstrumentType, ...] = Field(
        description=(
            "Instrument types this leg can be expressed in, drawn from the "
            "existing ``ArchetypeInstrumentType`` vocabulary (spot / perp / "
            "dated_future / lending / staking / lp / …). The wizard groups "
            "instrument choices BY leg role using this — fixing the F22 bug where "
            "a basis trade only offered 'Staking'."
        )
    )
    asset_groups: tuple[VenueCategoryV2, ...] = Field(
        description=(
            "Asset-group categories this leg's venues live in, drawn from the "
            "existing ``VenueCategoryV2`` vocabulary. A staked-basis hedge leg is "
            "cross-category (DEFI perp DEXes + CEFI CLOBs) — this is what breaks "
            "the single-category Stage-A assumption the wizard must surface."
        )
    )
    eligible_venue_ids: tuple[str, ...] = Field(
        description=(
            "Lowercase venue ids eligible for THIS leg (e.g. the hedge leg's "
            "``('hyperliquid', 'gmx_v2', 'drift', 'binance', 'bybit', 'deribit', "
            "'okx')``). Sourced per leg from the engine catalog / manifest cell "
            "``venue_ids`` / slot labels — NOT the archetype's flat mixed list."
        )
    )
    signal_variants: tuple[str, ...] = Field(
        default=(),
        description=(
            "Per-leg signal / sizing variants (e.g. dynamic-hedge-ratio for the "
            "staked-basis hedge leg). Empty tuple when the leg has no variant axis."
        ),
    )
    constraints: tuple[LegConstraint, ...] = Field(
        default=(),
        description=(
            "Typed conditional constraints on this leg (collateral-acceptance, "
            "same-venue, atomic-bundle). The exhaustive restriction surface."
        ),
    )
    source_of_truth: str = Field(
        description=(
            "Citation for where this leg's structure / venues come from: an "
            "engine code path, a codex archetype doc, and/or the manifest cell "
            "notes/slot-labels. Every leg MUST cite its source — numbers and "
            "venues are transcribed, never invented."
        )
    )


class ArchetypeLegStructure(BaseModel):
    """The full structural leg model for one archetype."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    archetype_id: StrategyArchetype = Field(description="The archetype this leg structure describes.")
    legs: tuple[ArchetypeLegSpec, ...] = Field(
        description="The ordered legs of the archetype (declaration order = execution / narrative order)."
    )
    execution_coupling: AtomicExecutionMode = Field(
        description=(
            "How the legs are coupled at execution, reusing the existing "
            "``AtomicExecutionMode`` vocabulary: ``ATOMIC`` / ``ATOMIC_ON_CHAIN`` "
            "(revert-all bundle), ``LEADER_HEDGE`` (leader fills then hedge), "
            "``SEQUENCED_WITH_PACING``. The staked-basis structure is "
            "``LEADER_HEDGE`` (the SWAP leader + perp hedge); the recursive loop "
            "is ``ATOMIC_ON_CHAIN``; the arbitrage same-chain pair is ``ATOMIC``."
        )
    )
    notes: str = Field(
        default="",
        description=(
            "Free-text structural notes (the prose that was previously the ONLY "
            "home for leg truth — kept as supplementary context, no longer the "
            "SSOT)."
        ),
    )
    not_registered: bool = Field(
        default=False,
        description=(
            "True when this archetype's leg structure is GENUINELY underivable "
            "(no engine in the strategy factory AND no structural legs in the "
            "codex doc — e.g. a pure meta-allocation overlay with no instrument "
            "legs, or an archetype intentionally absent from the factory pending "
            "an upstream feed). Such a structure carries ``legs=()`` and a "
            "``not_registered_reason``. The registry ENUMERATES all 58 archetypes "
            "(Phase 6A) so a consumer never sees an absent key — it sees an "
            "explicit not_registered marker instead. A normally-seeded structure "
            "leaves this ``False``."
        ),
    )
    not_registered_reason: str = Field(
        default="",
        description=(
            "Citation for WHY this archetype is not_registered (the engine-absence "
            "/ thin-doc / meta-allocation reason + its source). Required whenever "
            "``not_registered`` is True; empty otherwise. The exhaustive-honesty "
            "counterpart to ``source_of_truth`` on a real leg."
        ),
    )

    @model_validator(mode="after")
    def _validate_not_registered_invariant(self) -> ArchetypeLegStructure:
        """Enforce the not_registered ↔ legs/reason invariant (exhaustive honesty).

        A ``not_registered`` structure MUST have empty ``legs`` + a non-empty
        ``not_registered_reason``; a registered structure MUST have ≥1 leg.
        This makes the "absent key" antipattern unrepresentable — the registry
        enumerates all 58 archetypes, and an underivable one is an explicit
        not_registered marker, never silence.
        """

        if self.not_registered:
            if self.legs:
                raise ValueError(
                    f"{self.archetype_id.value}: not_registered structure must have legs=() (got {len(self.legs)} legs)"
                )
            if not self.not_registered_reason.strip():
                raise ValueError(
                    f"{self.archetype_id.value}: not_registered structure must cite a not_registered_reason"
                )
        else:
            if not self.legs:
                raise ValueError(
                    f"{self.archetype_id.value}: registered structure must have ≥1 leg "
                    "(use not_registered=True for an underivable archetype)"
                )
        return self

    @property
    def required_legs(self) -> tuple[ArchetypeLegSpec, ...]:
        """The mandatory legs (pre-selected + non-deselectable in the wizard)."""

        return tuple(leg for leg in self.legs if leg.required)

    @property
    def leg_roles(self) -> tuple[ArchetypeLegRole, ...]:
        """The roles present, in declaration order (used by tests + summaries)."""

        return tuple(leg.role for leg in self.legs)

    def leg(self, leg_id: str) -> ArchetypeLegSpec | None:
        """Return the leg with ``leg_id`` or ``None``."""

        for spec in self.legs:
            if spec.leg_id == leg_id:
                return spec
        return None


def _build_registry() -> dict[StrategyArchetype, ArchetypeLegStructure]:
    """Build the EXHAUSTIVE 57-archetype registry from the seeds module.

    The per-archetype seed builders live in ``archetype_leg_spec_seeds`` (split
    out so the full Phase 6A backfill fits the 900-line file cap). This function
    asserts the seeds cover EVERY ``StrategyArchetype`` value exactly once —
    real structures where derivable, explicit ``not_registered`` structures
    (legs=() + cited reason) where genuinely underivable. The registry therefore
    NEVER has an absent key (the exhaustive-enumeration guarantee).

    The import is deferred (inside the function) because the seeds module imports
    the schema classes from THIS module — a module-level import would be circular.
    """

    from unified_api_contracts.internal.architecture_v2.archetype_leg_spec_seeds import (
        build_all_structures,
    )

    structures = build_all_structures()
    registry = {s.archetype_id: s for s in structures}
    if len(registry) != len(structures):
        raise ValueError("archetype_leg_spec_seeds emitted a duplicate archetype_id")
    missing = set(StrategyArchetype) - set(registry)
    if missing:
        names = ", ".join(sorted(a.value for a in missing))
        raise ValueError(
            f"archetype_leg_spec_seeds does not enumerate all {len(StrategyArchetype)} archetypes "
            f"(missing: {names}) — the registry must be exhaustive (Phase 6A)"
        )
    return registry


ARCHETYPE_LEG_STRUCTURES: Final[dict[StrategyArchetype, ArchetypeLegStructure]] = _build_registry()
"""Registry of structural leg models, keyed by ``StrategyArchetype`` — EXHAUSTIVE.

SSOT for **leg truth** (see module docstring re: dual-representation with
``ARCHETYPE_CAPABILITY_REGISTRY``). Phase 6A: every one of the 58 archetypes is
present — real legs where derivable, an explicit ``not_registered`` structure
(``legs=()`` + ``not_registered_reason``) where genuinely underivable. There are
NO absent keys (use ``archetypes_without_leg_structures`` for the not_registered
set).
"""


def leg_structure_for(archetype_id: StrategyArchetype) -> ArchetypeLegStructure | None:
    """Return the leg structure for ``archetype_id``.

    Always non-``None`` for a valid archetype (the registry is exhaustive); the
    ``| None`` return is retained for call-site compatibility + dict-miss safety.
    A ``not_registered`` archetype returns its explicit not_registered structure,
    never ``None``.
    """

    return ARCHETYPE_LEG_STRUCTURES.get(archetype_id)


def all_leg_structures() -> tuple[ArchetypeLegStructure, ...]:
    """Return every leg structure (all 58), sorted by archetype id (deterministic)."""

    return tuple(ARCHETYPE_LEG_STRUCTURES[a] for a in sorted(ARCHETYPE_LEG_STRUCTURES, key=lambda x: x.value))


def registered_leg_structures() -> tuple[ArchetypeLegStructure, ...]:
    """The REAL-leg structures (not_registered=False), sorted (deterministic).

    These are the archetypes whose leg model is genuinely derivable from
    engine/doc/cells — the set the wizard renders as leg-aware. Complements
    ``archetypes_without_leg_structures``.
    """

    return tuple(s for s in all_leg_structures() if not s.not_registered)


def archetypes_without_leg_structures() -> tuple[StrategyArchetype, ...]:
    """The honest-gap set: archetypes whose structure is ``not_registered``.

    Phase 6A semantics: the registry now ENUMERATES all 58 archetypes, so this is
    no longer "absent keys" — it is the set of archetypes carrying an explicit
    ``not_registered`` structure (legs=() + cited reason). The exporter emits one
    ``not_registered`` 'legs' gap edge per such archetype; a test asserts the gap
    set is explicit (every member has a ``not_registered_reason``), not silent.
    """

    return tuple(
        a
        for a in sorted(StrategyArchetype, key=lambda x: x.value)
        if (s := ARCHETYPE_LEG_STRUCTURES.get(a)) is None or s.not_registered
    )


__all__ = [
    "ARCHETYPE_LEG_STRUCTURES",
    "ArchetypeLegRole",
    "ArchetypeLegSpec",
    "ArchetypeLegStructure",
    "LegConstraint",
    "LegConstraintKind",
    "all_leg_structures",
    "archetypes_without_leg_structures",
    "leg_structure_for",
    "registered_leg_structures",
]

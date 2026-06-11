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

LOGIC FREEZE: the seeds below are *citations of* the shipped engine structure +
codex archetype docs + existing manifest cells. They DO NOT change any engine
behaviour. Numbers / venues come only from those three sources (cited per leg in
``source_of_truth``).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

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


# ---------------------------------------------------------------------------
# Seeds — every leg cites its source (engine path / codex doc / manifest cell)
# ---------------------------------------------------------------------------

# Citation shorthands reused across seeds (kept as constants so a venue-list
# update has ONE edit site and the source is unambiguous).
_ENGINE_STAKED = (
    "strategy-service CarryStakedBasisEngine._build_legs / _derive_structure "
    "(staked_basis.py); catalog_staked_basis.py venue tuples"
)
_CELL_STAKED = (
    "manifest cell CARRY_STAKED_BASIS (DEFI, staking) notes '3-leg ATOMIC "
    "(stake + lending + perp)' + slot labels lido-aave-hyperliquid / "
    "jito-kamino-drift / lido-aave-{binance,bybit,deribit,okx}"
)
_DOC_STAKED = (
    "codex/09-strategy/architecture-v2/archetypes/carry-staked-basis.md § 'Token / position flow — LST_AS_MARGIN'"
)

# The staked-basis perp-hedge universe (lowercase manifest ids). Task-specified
# + manifest cell venue_ids: DeFi perp DEXes (hyperliquid/gmx_v2/drift) + CeFi
# CLOBs (binance/bybit/deribit/okx). Cross-category by construction.
_STAKED_HEDGE_VENUES: Final[tuple[str, ...]] = (
    "hyperliquid",
    "gmx_v2",
    "drift",
    "binance",
    "bybit",
    "deribit",
    "okx",
)
# The staked-basis stake protocols (ETH + SOL LSTs) and lend venues.
_STAKE_PROTOCOLS_ETH_SOL: Final[tuple[str, ...]] = ("lido", "rocketpool", "jito", "marinade")
_LEND_VENUES_STAKED: Final[tuple[str, ...]] = ("aave_v3", "kamino")
# The spot/swap (USDC→native) leg venues, per catalog_staked_basis.py.
_SPOT_VENUES_STAKED: Final[tuple[str, ...]] = ("uniswap_v3", "jupiter")


def _staked_basis_collateral_constraint() -> LegConstraint:
    """The staked-vs-straight-basis conditional (the F22 headline constraint).

    Cites ``CarryStakedBasisEngine._derive_structure`` gating on
    ``accepted_perp_collateral(perp_venue)``.
    """

    return LegConstraint(
        kind=LegConstraintKind.REQUIRES_COLLATERAL_ACCEPTANCE,
        params={"asset": "lst_token", "venue_role": "hedge_short"},
        fallback_variant="straight_basis",
        description=(
            "The LST must be accepted as cross-margin at the perp hedge venue "
            "(engine gate: accepted_perp_collateral(perp_venue)). On venues that "
            "accept the LST → staked basis (earn staking yield + funding). On "
            "venues that do NOT accept the LST as collateral → the stake leg is "
            "dropped and this runs as a straight perp-funding basis "
            "(== CARRY_BASIS_PERP) within the same archetype."
        ),
    )


def _staked_basis_structure(
    archetype: StrategyArchetype,
    *,
    hedge_role: ArchetypeLegRole,
    hedge_instrument: ArchetypeInstrumentType,
    notes: str,
) -> ArchetypeLegStructure:
    """Build a CARRY_STAKED_BASIS-family structure (perp or dated hedge).

    Shared between ``CARRY_STAKED_BASIS`` (perp hedge) and
    ``CARRY_STAKED_BASIS_DATED`` (dated-future hedge — the Deribit dated variant
    per the manifest cell + catalog_staked_basis dated slots).
    """

    coll = _staked_basis_collateral_constraint()
    atomic = LegConstraint(
        kind=LegConstraintKind.REQUIRES_ATOMIC_BUNDLE,
        params={"bundle_id": "staked_basis"},
        description=(
            "The SWAP→STAKE→TRANSFER→hedge sequence is coupled (LEADER_HEDGE): "
            "the hedge must fill within hedge_deadline_ms of the staked leader "
            "or the leader is closed (CompensationPolicy.CLOSE_LEADER_IF_HEDGE_FAILS)."
        ),
    )
    return ArchetypeLegStructure(
        archetype_id=archetype,
        legs=(
            ArchetypeLegSpec(
                leg_id="spot",
                role=ArchetypeLegRole.SPOT_LONG,
                required=True,
                instrument_types=(ArchetypeInstrumentType.SPOT,),
                asset_groups=(VenueCategoryV2.DEFI, VenueCategoryV2.CEFI),
                eligible_venue_ids=_SPOT_VENUES_STAKED,
                signal_variants=(),
                constraints=(),
                source_of_truth=f"{_ENGINE_STAKED} (SWAP leader leg, role=leader); {_DOC_STAKED}",
            ),
            ArchetypeLegSpec(
                leg_id="stake",
                role=ArchetypeLegRole.STAKE,
                required=False,  # dropped in straight-basis fallback
                instrument_types=(ArchetypeInstrumentType.STAKING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=_STAKE_PROTOCOLS_ETH_SOL,
                signal_variants=("staking_apy_total",),
                constraints=(coll,),
                source_of_truth=f"{_ENGINE_STAKED} (STAKE leg, role=stake); {_CELL_STAKED}",
            ),
            ArchetypeLegSpec(
                leg_id="lend",
                role=ArchetypeLegRole.LEND,
                required=False,
                instrument_types=(ArchetypeInstrumentType.LENDING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=_LEND_VENUES_STAKED,
                signal_variants=(),
                constraints=(),
                source_of_truth=(
                    f"{_CELL_STAKED} (lend@aave/kamino encoded in slot labels "
                    "lido-AAVE-hyperliquid / jito-KAMINO-drift)"
                ),
            ),
            ArchetypeLegSpec(
                leg_id="hedge",
                role=hedge_role,
                required=True,
                instrument_types=(hedge_instrument,),
                asset_groups=(VenueCategoryV2.DEFI, VenueCategoryV2.CEFI),
                eligible_venue_ids=_STAKED_HEDGE_VENUES,
                signal_variants=("dynamic_hedge_ratio",),
                constraints=(coll, atomic),
                source_of_truth=(f"{_ENGINE_STAKED} (TRADE hedge leg, role=hedge, leg_type=PERP); {_CELL_STAKED}"),
            ),
        ),
        execution_coupling=AtomicExecutionMode.LEADER_HEDGE,
        notes=notes,
    )


def _basis_perp_structure(archetype: StrategyArchetype, *, inverse: bool, notes: str) -> ArchetypeLegStructure:
    """CARRY_BASIS_PERP (+ _INV): spot + perp delta-neutral basis.

    ``CarryBasisPerpEngine`` is perp-side only (hedge wired by orchestrator);
    the structural pair is spot_long + perp_short (short the basis: hold spot,
    short perp when funding > 0). ``_INV`` flips: lend/USDC-margined perp + hold
    spot (manifest enum comment, enums.py CARRY_BASIS_PERP_INV).
    """

    spot_role = ArchetypeLegRole.SPOT_LONG
    perp_role = ArchetypeLegRole.PERP_LONG if inverse else ArchetypeLegRole.PERP_SHORT
    same_venue = LegConstraint(
        kind=LegConstraintKind.REQUIRES_SAME_VENUE,
        params={"other_leg_id": "spot"},
        description=(
            "Single-venue netted basis (spot + perp on one CEX) is the most "
            "capital-efficient form (manifest cell note 'single-venue netted'); "
            "cross-venue form runs LEADER_HEDGE instead."
        ),
    )
    return ArchetypeLegStructure(
        archetype_id=archetype,
        legs=(
            ArchetypeLegSpec(
                leg_id="spot",
                role=spot_role,
                required=True,
                instrument_types=(ArchetypeInstrumentType.SPOT,),
                asset_groups=(VenueCategoryV2.CEFI, VenueCategoryV2.DEFI),
                eligible_venue_ids=("binance", "okx", "bybit", "hyperliquid", "uniswap_v3"),
                source_of_truth=(
                    "manifest cell CARRY_BASIS_PERP (CEFI/DEFI, perp) venue_ids + "
                    "slot labels; strategy-service CarryBasisPerpEngine (basis_perp.py)"
                ),
            ),
            ArchetypeLegSpec(
                leg_id="perp",
                role=perp_role,
                required=True,
                instrument_types=(ArchetypeInstrumentType.PERP,),
                asset_groups=(VenueCategoryV2.CEFI, VenueCategoryV2.DEFI),
                eligible_venue_ids=("binance", "okx", "bybit", "hyperliquid", "deribit", "gmx_v2", "drift"),
                signal_variants=("funding_rate_annualised_bps",),
                constraints=(same_venue,),
                source_of_truth=(
                    "strategy-service CarryBasisPerpEngine.on_tick (basis_perp.py, "
                    "direction flips on funding sign); manifest cell CARRY_BASIS_PERP"
                ),
            ),
        ),
        execution_coupling=AtomicExecutionMode.LEADER_HEDGE,
        notes=notes,
    )


def _basis_dated_structure(archetype: StrategyArchetype, *, inverse: bool, notes: str) -> ArchetypeLegStructure:
    """CARRY_BASIS_DATED (+ _INV): spot + dated future cash-and-carry.

    Cites ``CarryBasisDatedEngine`` (basis_dated.py): contango → long spot /
    short future; backwardation (``_INV``) flips.
    """

    future_role = ArchetypeLegRole.FUTURE_LONG if inverse else ArchetypeLegRole.FUTURE_SHORT
    spot_role = ArchetypeLegRole.SPOT_SHORT if inverse else ArchetypeLegRole.SPOT_LONG
    return ArchetypeLegStructure(
        archetype_id=archetype,
        legs=(
            ArchetypeLegSpec(
                leg_id="spot",
                role=spot_role,
                required=True,
                instrument_types=(ArchetypeInstrumentType.SPOT,),
                asset_groups=(VenueCategoryV2.CEFI, VenueCategoryV2.TRADFI),
                eligible_venue_ids=("binance", "coinbase", "deribit", "ibkr"),
                source_of_truth=(
                    "strategy-service CarryBasisDatedEngine (basis_dated.py, spot leader); "
                    "manifest cell CARRY_BASIS_DATED (CEFI/TRADFI, dated_future)"
                ),
            ),
            ArchetypeLegSpec(
                leg_id="future",
                role=future_role,
                required=True,
                instrument_types=(ArchetypeInstrumentType.DATED_FUTURE,),
                asset_groups=(VenueCategoryV2.CEFI, VenueCategoryV2.TRADFI),
                eligible_venue_ids=("deribit", "cme", "ice", "binance"),
                source_of_truth=(
                    "strategy-service CarryBasisDatedEngine (TRADE future leg, "
                    "leg_type=FUTURE; side flips on basis sign); manifest cell CARRY_BASIS_DATED"
                ),
            ),
        ),
        execution_coupling=AtomicExecutionMode.LEADER_HEDGE,
        notes=notes,
    )


def _recursive_staked_structure() -> ArchetypeLegStructure:
    """CARRY_RECURSIVE_STAKED: leveraged LST loop (STAKE->LEND->BORROW) xN atomic.

    Cites ``CarryRecursiveStakedEngine._build_loop_legs`` (recursive_staked.py)
    emitting the ATOMIC_ON_CHAIN loop.
    """

    src = (
        "strategy-service CarryRecursiveStakedEngine._build_loop_legs "
        "(recursive_staked.py, STAKE→LEND→BORROW loop, ATOMIC_ON_CHAIN); "
        "manifest cell CARRY_RECURSIVE_STAKED (DEFI, staking)"
    )
    atomic = LegConstraint(
        kind=LegConstraintKind.REQUIRES_ATOMIC_BUNDLE,
        params={"bundle_id": "recursive_loop"},
        description="All loop iterations execute atomically on-chain (ATOMIC_ON_CHAIN composite call).",
    )
    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.CARRY_RECURSIVE_STAKED,
        legs=(
            ArchetypeLegSpec(
                leg_id="loop_stake",
                role=ArchetypeLegRole.STAKE,
                required=True,
                instrument_types=(ArchetypeInstrumentType.STAKING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=("lido", "rocketpool", "jito", "marinade"),
                constraints=(atomic,),
                source_of_truth=src,
            ),
            ArchetypeLegSpec(
                leg_id="loop_collateral",
                role=ArchetypeLegRole.LEND,
                required=True,
                instrument_types=(ArchetypeInstrumentType.LENDING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=("aave_v3", "kamino"),
                constraints=(atomic,),
                source_of_truth=src,
            ),
            ArchetypeLegSpec(
                leg_id="loop_borrow",
                role=ArchetypeLegRole.BORROW,
                required=True,
                instrument_types=(ArchetypeInstrumentType.LENDING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=("aave_v3", "kamino"),
                signal_variants=("effective_ltv", "target_leverage"),
                constraints=(atomic,),
                source_of_truth=src,
            ),
        ),
        execution_coupling=AtomicExecutionMode.ATOMIC_ON_CHAIN,
        notes="Up to 10 loop iterations (recursive_staked.py max_loops); LTV-gated leverage.",
    )


def _recursive_borrow_lending_only_structure() -> ArchetypeLegStructure:
    """CARRY_RECURSIVE_BORROW_LENDING_ONLY: pure lending-side recursion (no stake).

    Config sibling of CARRY_RECURSIVE_STAKED (recursive_staked.ALLOWED_ARCHETYPES);
    the LEND→BORROW loop without the STAKE leg.
    """

    src = (
        "strategy-service CarryRecursiveStakedEngine (recursive_staked.py, "
        "ALLOWED_ARCHETYPES includes CARRY_RECURSIVE_BORROW_LENDING_ONLY, "
        "LENDING_ONLY = LEND→BORROW loop); enums.py archetype comment"
    )
    atomic = LegConstraint(
        kind=LegConstraintKind.REQUIRES_ATOMIC_BUNDLE,
        params={"bundle_id": "recursive_loop"},
        description="Lending-loop iterations execute atomically on-chain.",
    )
    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.CARRY_RECURSIVE_BORROW_LENDING_ONLY,
        legs=(
            ArchetypeLegSpec(
                leg_id="loop_collateral",
                role=ArchetypeLegRole.LEND,
                required=True,
                instrument_types=(ArchetypeInstrumentType.LENDING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=("aave_v3", "kamino", "compound_v3", "morpho"),
                constraints=(atomic,),
                source_of_truth=src,
            ),
            ArchetypeLegSpec(
                leg_id="loop_borrow",
                role=ArchetypeLegRole.BORROW,
                required=True,
                instrument_types=(ArchetypeInstrumentType.LENDING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=("aave_v3", "kamino", "compound_v3", "morpho"),
                signal_variants=("effective_ltv", "target_leverage"),
                constraints=(atomic,),
                source_of_truth=src,
            ),
        ),
        execution_coupling=AtomicExecutionMode.ATOMIC_ON_CHAIN,
        notes="Family 2 recursive variant — lending-side only, no LST stake leg.",
    )


def _staking_simple_structure() -> ArchetypeLegStructure:
    """YIELD_STAKING_SIMPLE: a single stake leg, no hedge."""

    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.YIELD_STAKING_SIMPLE,
        legs=(
            ArchetypeLegSpec(
                leg_id="stake",
                role=ArchetypeLegRole.STAKE,
                required=True,
                instrument_types=(ArchetypeInstrumentType.STAKING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=("lido", "rocketpool", "etherfi", "jito", "marinade"),
                source_of_truth=(
                    "strategy-service YieldStakingSimpleEngine (staking_simple.py, "
                    "single STAKE leg); manifest cell YIELD_STAKING_SIMPLE (DEFI, staking) "
                    "note 'Pure staking, no hedge'"
                ),
            ),
        ),
        execution_coupling=AtomicExecutionMode.ATOMIC_ON_CHAIN,
        notes="Single-leg archetype — included for leg-model completeness (the trivial structure).",
    )


def _rotation_lending_structure() -> ArchetypeLegStructure:
    """YIELD_ROTATION_LENDING: a single lend leg, rotated across venues."""

    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.YIELD_ROTATION_LENDING,
        legs=(
            ArchetypeLegSpec(
                leg_id="lend",
                role=ArchetypeLegRole.LEND,
                required=True,
                instrument_types=(ArchetypeInstrumentType.LENDING,),
                asset_groups=(VenueCategoryV2.DEFI,),
                eligible_venue_ids=("aave_v3", "compound_v3", "euler", "morpho", "kamino"),
                signal_variants=("apy_rotation",),
                source_of_truth=(
                    "strategy-service YieldRotationLendingEngine (rotation_lending.py, "
                    "rotate lent capital to highest-APY venue); manifest cell "
                    "YIELD_ROTATION_LENDING (DEFI, lending)"
                ),
            ),
        ),
        execution_coupling=AtomicExecutionMode.SEQUENCED_WITH_PACING,
        notes="Single-leg archetype; rotation across venues is a venue-switch, not a second leg.",
    )


def _price_dispersion_structure() -> ArchetypeLegStructure:
    """ARBITRAGE_PRICE_DISPERSION: a buy leg + a sell leg cross-venue.

    Cites ``ArbitragePriceDispersionEngine`` (price_dispersion.py): the cheaper
    venue is the BUY leader (``spot_long``), the richer venue the SELL hedge
    (``spot_short``); same-chain → ATOMIC, cross-venue → LEADER_HEDGE.
    """

    src = (
        "strategy-service ArbitragePriceDispersionEngine (price_dispersion.py, "
        "BUY leader + SELL hedge AtomicLegs); manifest cell ARBITRAGE_PRICE_DISPERSION; "
        "codex/09-strategy/architecture-v2/archetypes/arbitrage-price-dispersion.md"
    )
    # candidate_venues spans CEFI + DEFI + SPORTS + PREDICTION per the doc venue_universe.
    venues = (
        "binance",
        "okx",
        "bybit",
        "hyperliquid",
        "deribit",
        "uniswap_v3",
        "balancer",
        "curve",
        "gmx_v2",
        "drift",
        "unity",
        "betfair_direct",
        "smarkets_direct",
        "polymarket",
    )
    groups = (
        VenueCategoryV2.CEFI,
        VenueCategoryV2.DEFI,
        VenueCategoryV2.SPORTS,
        VenueCategoryV2.PREDICTION,
        VenueCategoryV2.TRADFI,
    )
    atomic = LegConstraint(
        kind=LegConstraintKind.REQUIRES_ATOMIC_BUNDLE,
        params={"bundle_id": "dispersion_pair"},
        description=(
            "Same-chain pairs execute ATOMIC (multicall / flash-loan); cross-venue "
            "non-atomic pairs run LEADER_HEDGE with abort-on-adverse-move."
        ),
    )
    return ArchetypeLegStructure(
        archetype_id=StrategyArchetype.ARBITRAGE_PRICE_DISPERSION,
        legs=(
            ArchetypeLegSpec(
                leg_id="buy",
                role=ArchetypeLegRole.SPOT_LONG,
                required=True,
                instrument_types=(
                    ArchetypeInstrumentType.SPOT,
                    ArchetypeInstrumentType.PERP,
                    ArchetypeInstrumentType.EVENT_SETTLED,
                ),
                asset_groups=groups,
                eligible_venue_ids=venues,
                signal_variants=("dispersion_bps",),
                constraints=(atomic,),
                source_of_truth=f"{src} (cheaper venue = BUY leader)",
            ),
            ArchetypeLegSpec(
                leg_id="sell",
                role=ArchetypeLegRole.SPOT_SHORT,
                required=True,
                instrument_types=(
                    ArchetypeInstrumentType.SPOT,
                    ArchetypeInstrumentType.PERP,
                    ArchetypeInstrumentType.EVENT_SETTLED,
                ),
                asset_groups=groups,
                eligible_venue_ids=venues,
                signal_variants=("dispersion_bps",),
                constraints=(atomic,),
                source_of_truth=f"{src} (richer venue = SELL hedge)",
            ),
        ),
        execution_coupling=AtomicExecutionMode.ATOMIC,
        notes="2-leg paired cross-venue arb; same instrument (or equivalent) on two venues.",
    )


def _build_registry() -> dict[StrategyArchetype, ArchetypeLegStructure]:
    structures: tuple[ArchetypeLegStructure, ...] = (
        _staked_basis_structure(
            StrategyArchetype.CARRY_STAKED_BASIS,
            hedge_role=ArchetypeLegRole.HEDGE_SHORT,
            hedge_instrument=ArchetypeInstrumentType.PERP,
            notes=(
                "3-leg structure (spot_long + stake + lend) + perp hedge_short. "
                "Conditional: LST accepted as perp collateral on the hedge venue → "
                "staked basis; not accepted → straight_basis fallback (stake leg dropped)."
            ),
        ),
        _staked_basis_structure(
            StrategyArchetype.CARRY_STAKED_BASIS_DATED,
            hedge_role=ArchetypeLegRole.FUTURE_SHORT,
            hedge_instrument=ArchetypeInstrumentType.DATED_FUTURE,
            notes=(
                "Dated-hedge variant of CARRY_STAKED_BASIS — hedge leg is a Deribit "
                "dated ETH future (manifest cell CARRY_STAKED_BASIS_DATED; "
                "catalog_staked_basis dated slots). Same collateral conditional."
            ),
        ),
        _basis_perp_structure(
            StrategyArchetype.CARRY_BASIS_PERP,
            inverse=False,
            notes="Spot + perp delta-neutral basis (short the basis when funding > 0).",
        ),
        _basis_perp_structure(
            StrategyArchetype.CARRY_BASIS_PERP_INV,
            inverse=True,
            notes="Inverse basis-perp: lend/USDC-margined perp + hold spot (enums.py comment).",
        ),
        _basis_dated_structure(
            StrategyArchetype.CARRY_BASIS_DATED,
            inverse=False,
            notes="Spot + dated-future cash-and-carry (contango: long spot, short future).",
        ),
        _basis_dated_structure(
            StrategyArchetype.CARRY_BASIS_DATED_INV,
            inverse=True,
            notes="Inverse dated basis (backwardation: short spot, long future).",
        ),
        _recursive_staked_structure(),
        _recursive_borrow_lending_only_structure(),
        _staking_simple_structure(),
        _rotation_lending_structure(),
        _price_dispersion_structure(),
    )
    return {s.archetype_id: s for s in structures}


ARCHETYPE_LEG_STRUCTURES: Final[dict[StrategyArchetype, ArchetypeLegStructure]] = _build_registry()
"""Registry of structural leg models, keyed by ``StrategyArchetype``.

SSOT for **leg truth** (see module docstring re: dual-representation with
``ARCHETYPE_CAPABILITY_REGISTRY``). Only the multi-leg + representative
single-leg archetypes seeded for F22 are present; every other archetype is an
honest gap (see ``archetypes_without_leg_structures``).
"""


def leg_structure_for(archetype_id: StrategyArchetype) -> ArchetypeLegStructure | None:
    """Return the leg structure for ``archetype_id`` or ``None`` if not seeded."""

    return ARCHETYPE_LEG_STRUCTURES.get(archetype_id)


def all_leg_structures() -> tuple[ArchetypeLegStructure, ...]:
    """Return every seeded leg structure, sorted by archetype id (deterministic)."""

    return tuple(ARCHETYPE_LEG_STRUCTURES[a] for a in sorted(ARCHETYPE_LEG_STRUCTURES, key=lambda x: x.value))


def archetypes_without_leg_structures() -> tuple[StrategyArchetype, ...]:
    """The honest-gap set: archetypes with NO leg structure yet.

    Enumerable so the exporter can emit one ``not_registered`` 'legs' gap edge
    per archetype (exhaustive honesty) and so a test can assert the gap set is
    explicit, not silent.
    """

    return tuple(a for a in sorted(StrategyArchetype, key=lambda x: x.value) if a not in ARCHETYPE_LEG_STRUCTURES)


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
]

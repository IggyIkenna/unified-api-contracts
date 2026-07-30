"""Archetype → execution-algorithm compatibility registry (Phase 6A).

WHY THIS MODULE EXISTS (operator-caught, 2026-06-12):
The capability wizard could not BLOCK an impossible execution-algorithm x strategy
combination because NOTHING declared which algos are valid for which instruction.
The execution-service ``select_algorithm`` selector IS the compatibility truth —
this module transcribes that selector logic DECLARATIVELY so the wizard, the
verdict matrix and the capability manifest can render + block algo mismatches
without importing the execution service (service↔service imports are banned).

SOURCE OF TRUTH (transcribed verbatim — file:line citations per rule):
  - ``execution_service/algorithms/selector.py``
    - ``ALGORITHMS_BY_INSTRUCTION_TYPE`` (selector.py:25-70): the valid algorithm
      set per ``InstructionType``.
    - ``DEFAULT_ALGORITHM`` (selector.py:73-82): the default algorithm per type.
    - ``select_algorithm`` (selector.py:126-167): the 4-step priority chain —
      (1) ZERO_ALPHA forces BENCHMARK_FILL (selector.py:133-139); (2) a requested
      algo is honored IFF in the valid set, else falls through with a warning
      (selector.py:142-151); (3) a config algo likewise (selector.py:153-158);
      (4) else the default (selector.py:160-166).
  - ``execution_service/utils/instruction_type.py``
    - ``infer_instruction_type`` (instruction_type.py:69-112): venue-id →
      InstructionType (CLOB→TRADE, DEX→SWAP, lending/staking→ZERO_ALPHA, unknown→TRADE).
    - ``ZERO_ALPHA_OPERATIONS`` (instruction_type.py:29-41): LEND/BORROW/STAKE/… →
      ZERO_ALPHA regardless of venue.
    - ``_DIRECT_INSTRUCTION_TYPES`` (instruction_type.py:44-51): OPTIONS_COMBO /
      FUTURES_ROLL / PREDICTION_BET / SPORTS_BET / SPORTS_EXCHANGE direct map.
  - ``unified_api_contracts.{CLOB_VENUES,DEX_VENUES,ZERO_ALPHA_VENUES}`` — the
    venue-kind sets the selector consults (UAC-owned; the execution-service imports
    them, so this registry consults the SAME sets, no drift).

The ``InstructionType`` enum is itself a UAC type
(``unified_api_contracts.internal.domain.execution_service.types``), so this
registry imports + reuses it (no redefinition).

HONEST GAPS / TYPED AMBIGUITY (operator wants these caught, not hidden):
  - The "ghost" algorithms ``SEQUENTIAL_LEGS`` / ``SPREAD_ROLL`` / ``BEST_PRICE`` /
    ``KELLY_STAKE`` appear in the selector's valid sets but have NO implementation
    class in the execution service (selector returns the string; nothing executes
    it). They are transcribed here with ``implemented=False`` so a consumer can
    surface the gap. ``BENCHMARK_FILL`` is a mode flag (not a class) and
    ``MAX_SLIPPAGE`` is a matching-engine order type (not an ExecAlgorithm) — both
    likewise ``implemented=False`` as ExecAlgorithm objects.
  - The selector contradictions (ICEBERG split across code paths; SOR vs
    SMART_ORDER_ROUTER naming; the heuristic ``engine/live/algo_selector.py``
    bypassing the InstructionType rules; the ghost algos; the missing SSOT doc)
    are recorded in ``SELECTOR_CONTRADICTIONS`` so the manifest/finding-tracker
    can carry them. All five are ``resolved=True`` as of 2026-07-30 (see each
    record's ``resolution`` field + unified-trading-pm
    codex/04-architecture/execution-algorithm-selection.md) — kept as a
    permanent record, not deleted, since the taxonomy split they document
    (manual/live vs canonical-automated algo universes) is itself durable.

MAPPING archetype → valid algos: an archetype's valid-algo set is the UNION of the
valid sets of the InstructionTypes its legs induce (a leg's instrument-type + the
venue kind it runs on → an InstructionType, per ``leg_instruction_type``). A
not_registered archetype (no legs) carries ``not_registered`` reason and an empty
valid set (the verdict matrix renders not_registered cells for it).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ArchetypeInstrumentType,
)
from unified_api_contracts.internal.architecture_v2.archetype_leg_spec import (
    ARCHETYPE_LEG_STRUCTURES,
    ArchetypeLegStructure,
)
from unified_api_contracts.internal.architecture_v2.enums import (
    StrategyArchetype,
    VenueCategoryV2,
)
from unified_api_contracts.internal.domain.execution_service.types import InstructionType

# ---------------------------------------------------------------------------
# Venue-kind vocabulary (the axis the selector keys off)
# ---------------------------------------------------------------------------


class VenueExecutionKind(StrEnum):
    """How a venue executes — the axis ``infer_instruction_type`` classifies on.

    Transcribed from ``instruction_type.py:91-112`` (the CLOB / DEX / ZERO_ALPHA
    branch order) + the ``_DIRECT_INSTRUCTION_TYPES`` operation map. A venue-kind
    (not a raw venue id) is the stable compatibility axis: a CLOB venue runs TRADE
    algos, a DEX venue runs SWAP algos, an on-chain lending/staking venue runs
    ZERO_ALPHA (forced BENCHMARK_FILL), etc.

    - ``clob`` — central-limit-order-book venue (Binance/OKX/Bybit/Hyperliquid/
      Deribit/CME/CBOE/NASDAQ…; ``CLOB_VENUES``) → ``InstructionType.TRADE``.
    - ``dex`` — on-chain swap venue (Uniswap/Curve/Aerodrome…; ``DEX_VENUES``) →
      ``InstructionType.SWAP``.
    - ``onchain_zero_alpha`` — lending/staking protocol (Aave/Lido/Morpho…;
      ``ZERO_ALPHA_VENUES``) OR a zero-alpha operation (LEND/STAKE/…) →
      ``InstructionType.ZERO_ALPHA`` (forced BENCHMARK_FILL).
    - ``options`` — options venue with a combo instrument → ``OPTIONS_COMBO``.
    - ``dated_futures`` — a futures-roll context → ``FUTURES_ROLL``.
    - ``prediction`` — a prediction-market bet → ``PREDICTION_BET``.
    - ``sports`` — a sports book/exchange bet → ``SPORTS_BET`` / ``SPORTS_EXCHANGE``.
    """

    CLOB = "clob"
    DEX = "dex"
    ONCHAIN_ZERO_ALPHA = "onchain_zero_alpha"
    OPTIONS = "options"
    DATED_FUTURES = "dated_futures"
    PREDICTION = "prediction"
    SPORTS = "sports"


# ---------------------------------------------------------------------------
# The execution-algorithm declarations (transcribed from selector.py)
# ---------------------------------------------------------------------------


class ExecutionAlgo(BaseModel):
    """One execution algorithm the selector can return.

    Mirrors a string key in ``ALGORITHMS_BY_INSTRUCTION_TYPE``; carries whether a
    real ExecAlgorithm implementation exists (the ghost-algorithm honesty flag).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(
        description=(
            "The algorithm string the selector returns (UPPERCASE), e.g. "
            "``TWAP`` / ``SMART_ORDER_ROUTER`` / ``BENCHMARK_FILL`` — verbatim from "
            "``ALGORITHMS_BY_INSTRUCTION_TYPE`` (selector.py:25-70)."
        )
    )
    implemented: bool = Field(
        description=(
            "Whether a real ExecAlgorithm implementation backs this key. False for "
            "the ghost algorithms the selector returns but nothing executes "
            "(SEQUENTIAL_LEGS / SPREAD_ROLL / BEST_PRICE / KELLY_STAKE), for "
            "BENCHMARK_FILL (a mode flag, not a class) and MAX_SLIPPAGE (a "
            "matching-engine order type). A consumer can surface the gap."
        )
    )
    note: str = Field(
        description="What the algorithm does + its implementation status, cited.",
    )


# Every algorithm key that appears anywhere in ALGORITHMS_BY_INSTRUCTION_TYPE,
# with its implementation status (transcribed; the ghost set is the honest gap).
EXECUTION_ALGOS: Final[dict[str, ExecutionAlgo]] = {
    a.key: a
    for a in (
        ExecutionAlgo(
            key="BENCHMARK_FILL",
            implemented=False,
            note=(
                "Mode flag (fill at arrival, 0 alpha); not an ExecAlgorithm class "
                "(signal_driven_v3_base.benchmark_fill_mode)."
            ),
        ),
        ExecutionAlgo(key="TWAP", implemented=True, note="TWAPAlgorithm (engine/execution/algorithms)."),
        ExecutionAlgo(key="VWAP", implemented=True, note="VWAPAlgorithm."),
        ExecutionAlgo(key="ADAPTIVE_TWAP", implemented=True, note="AdaptiveTWAPAlgorithm (market-condition adjusted)."),
        ExecutionAlgo(
            key="ALMGREN_CHRISS", implemented=True, note="AlmgrenChrissAlgorithm (optimal market-impact execution)."
        ),
        ExecutionAlgo(key="POV_DYNAMIC", implemented=True, note="POVAlgorithm (percentage of volume)."),
        ExecutionAlgo(key="HYBRID_OPTIMAL", implemented=True, note="HybridOptimalAlgorithm (regime-based selection)."),
        ExecutionAlgo(
            key="PASSIVE_AGGRESSIVE_HYBRID", implemented=True, note="PassiveAggressiveAlgorithm (maker+taker hybrid)."
        ),
        ExecutionAlgo(
            key="SMART_ORDER_ROUTER", implemented=True, note="SORAlgorithm / SmartOrderRouter (route across DEXs)."
        ),
        ExecutionAlgo(key="SOR_TWAP", implemented=True, note="SorTwapAlgorithm (SOR + time-weighting, multi-venue)."),
        ExecutionAlgo(key="SWAP_TWAP", implemented=True, note="SwapTwapAlgorithm (time-weighting, single venue)."),
        ExecutionAlgo(
            key="MAX_SLIPPAGE",
            implemented=False,
            note="Matching-engine order type (trade_matcher MAX_SLIPPAGE), not an ExecAlgorithm class.",
        ),
        ExecutionAlgo(
            key="SEQUENTIAL_LEGS",
            implemented=False,
            note=(
                "GHOST: selector returns it for OPTIONS_COMBO but no implementation "
                "class (selector comment 'via StrikeMapper')."
            ),
        ),
        ExecutionAlgo(
            key="SPREAD_ROLL",
            implemented=False,
            note="GHOST: selector returns it for FUTURES_ROLL but no implementation class (near-far spread roll).",
        ),
        ExecutionAlgo(
            key="BEST_PRICE",
            implemented=False,
            note="GHOST: selector default for bet types; no implementation class (best bid/ask placement).",
        ),
        ExecutionAlgo(
            key="KELLY_STAKE",
            implemented=False,
            note="GHOST: selector option for bet types; no implementation class (Kelly stake sizing).",
        ),
    )
}


# ALGORITHMS_BY_INSTRUCTION_TYPE — transcribed verbatim (selector.py:25-70).
ALGOS_BY_INSTRUCTION_TYPE: Final[dict[InstructionType, tuple[str, ...]]] = {
    InstructionType.TRADE: (
        "BENCHMARK_FILL",
        "TWAP",
        "VWAP",
        "ADAPTIVE_TWAP",
        "ALMGREN_CHRISS",
        "POV_DYNAMIC",
        "HYBRID_OPTIMAL",
        "PASSIVE_AGGRESSIVE_HYBRID",
    ),
    InstructionType.SWAP: ("BENCHMARK_FILL", "SMART_ORDER_ROUTER", "SOR_TWAP", "SWAP_TWAP", "MAX_SLIPPAGE"),
    InstructionType.ZERO_ALPHA: ("BENCHMARK_FILL",),
    InstructionType.OPTIONS_COMBO: ("BENCHMARK_FILL", "SEQUENTIAL_LEGS"),
    InstructionType.FUTURES_ROLL: ("BENCHMARK_FILL", "SPREAD_ROLL"),
    InstructionType.PREDICTION_BET: ("BENCHMARK_FILL", "BEST_PRICE", "KELLY_STAKE"),
    InstructionType.SPORTS_BET: ("BENCHMARK_FILL", "BEST_PRICE", "KELLY_STAKE"),
    InstructionType.SPORTS_EXCHANGE: ("BENCHMARK_FILL", "BEST_PRICE", "KELLY_STAKE"),
}

# DEFAULT_ALGORITHM — transcribed verbatim (selector.py:73-82).
DEFAULT_ALGO_BY_INSTRUCTION_TYPE: Final[dict[InstructionType, str]] = {
    InstructionType.TRADE: "TWAP",
    InstructionType.SWAP: "SMART_ORDER_ROUTER",
    InstructionType.ZERO_ALPHA: "BENCHMARK_FILL",
    InstructionType.OPTIONS_COMBO: "SEQUENTIAL_LEGS",
    InstructionType.FUTURES_ROLL: "SPREAD_ROLL",
    InstructionType.PREDICTION_BET: "BEST_PRICE",
    InstructionType.SPORTS_BET: "BEST_PRICE",
    InstructionType.SPORTS_EXCHANGE: "BEST_PRICE",
}


# ---------------------------------------------------------------------------
# venue-kind x instrument-type → InstructionType (the selector's classification)
# ---------------------------------------------------------------------------


def instruction_type_for(
    venue_kind: VenueExecutionKind,
    instrument_type: ArchetypeInstrumentType,
) -> InstructionType:
    """Return the ``InstructionType`` the selector infers for (venue_kind, instrument).

    Transcribes ``infer_instruction_type`` (instruction_type.py:69-112) +
    ``_DIRECT_INSTRUCTION_TYPES`` (instruction_type.py:44-51). The venue-kind is
    the primary axis (a venue is CLOB/DEX/ZERO_ALPHA); the instrument-type refines
    the direct-map cases (option→OPTIONS_COMBO, dated_future→FUTURES_ROLL,
    event_settled→PREDICTION/SPORTS).
    """

    # Lending / staking + on-chain protocols → ZERO_ALPHA (forced BENCHMARK_FILL),
    # regardless of instrument-type (instruction_type.py:29-41, 106-108).
    if instrument_type in (ArchetypeInstrumentType.LENDING, ArchetypeInstrumentType.STAKING):
        return InstructionType.ZERO_ALPHA
    if venue_kind == VenueExecutionKind.ONCHAIN_ZERO_ALPHA:
        return InstructionType.ZERO_ALPHA

    # Options combo / dated-future roll — direct-mapped (instruction_type.py:44-51).
    if instrument_type == ArchetypeInstrumentType.OPTION:
        return InstructionType.OPTIONS_COMBO
    if instrument_type == ArchetypeInstrumentType.DATED_FUTURE:
        return InstructionType.FUTURES_ROLL

    # Event-settled — prediction vs sports per the venue kind.
    if instrument_type == ArchetypeInstrumentType.EVENT_SETTLED:
        if venue_kind == VenueExecutionKind.PREDICTION:
            return InstructionType.PREDICTION_BET
        return InstructionType.SPORTS_EXCHANGE

    # LP provision is an on-chain swap (mint/burn) → SWAP (instruction_type.py:100-103).
    if instrument_type == ArchetypeInstrumentType.LP:
        return InstructionType.SWAP

    # Spot / perp → DEX-SWAP or CLOB-TRADE by venue kind (instruction_type.py:91-103).
    if venue_kind == VenueExecutionKind.DEX:
        return InstructionType.SWAP
    # CLOB venue (or unknown → TRADE default, instruction_type.py:110-112).
    return InstructionType.TRADE


# The venue-kinds an asset-group category typically executes on (for deriving an
# archetype's algo set from its legs' asset_groups). DeFi spans on-chain swap +
# lending/staking; CeFi/TradFi are CLOB; sports/prediction are bet venues.
_ASSET_GROUP_VENUE_KINDS: Final[dict[VenueCategoryV2, tuple[VenueExecutionKind, ...]]] = {
    VenueCategoryV2.CEFI: (VenueExecutionKind.CLOB,),
    VenueCategoryV2.TRADFI: (VenueExecutionKind.CLOB,),
    VenueCategoryV2.DEFI: (
        VenueExecutionKind.DEX,
        VenueExecutionKind.ONCHAIN_ZERO_ALPHA,
    ),
    VenueCategoryV2.SPORTS: (VenueExecutionKind.SPORTS,),
    VenueCategoryV2.PREDICTION: (VenueExecutionKind.PREDICTION,),
    VenueCategoryV2.CROSS_CATEGORY: (VenueExecutionKind.CLOB, VenueExecutionKind.DEX),
}


def venue_kinds_for_asset_group(asset_group: VenueCategoryV2) -> tuple[VenueExecutionKind, ...]:
    """The venue-execution kinds an asset-group category typically executes on.

    DeFi spans on-chain swap + lending/staking; CeFi/TradFi are CLOB;
    sports/prediction are bet venues. Defaults to ``(CLOB,)`` for an unmapped
    category (the selector's conservative TRADE fallback). Used by the verdict
    matrix to derive, for a leg's asset_groups, the instruction actions its cells
    induce.
    """

    return _ASSET_GROUP_VENUE_KINDS.get(asset_group, (VenueExecutionKind.CLOB,))


# ---------------------------------------------------------------------------
# Per-archetype compatibility records
# ---------------------------------------------------------------------------


class AlgoVerdict(StrEnum):
    """The verdict for one (archetype, algo) pair."""

    VALID = "valid"
    INVALID = "invalid"
    NOT_REGISTERED = "not_registered"


class ArchetypeAlgoCompatibility(BaseModel):
    """The valid/invalid execution algorithms for one archetype.

    Derived from the archetype's leg structure: each leg induces an
    ``InstructionType`` (via ``instruction_type_for``), and the archetype's valid
    algo set is the UNION of those types' valid sets. Every algorithm key gets an
    explicit verdict — VALID (in the union), INVALID (with the reason: not valid
    for any of the archetype's instruction types), or NOT_REGISTERED (the archetype
    has no leg structure).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    archetype_id: StrategyArchetype = Field(description="The archetype.")
    not_registered: bool = Field(
        description="True when the archetype has no leg structure (no algos derivable).",
    )
    not_registered_reason: str = Field(
        default="",
        description="Cited reason when not_registered (from the leg structure).",
    )
    instruction_types: tuple[InstructionType, ...] = Field(
        description="The InstructionTypes this archetype's legs induce (sorted, deduped).",
    )
    valid_algos: tuple[str, ...] = Field(
        description="The union of valid algorithm keys across the archetype's instruction types (sorted).",
    )
    default_algos: tuple[str, ...] = Field(
        description="The selector default per induced InstructionType (sorted, deduped).",
    )
    invalid_algos: tuple[str, ...] = Field(
        description="Every algorithm key NOT in valid_algos (sorted) — the BLOCKED set with reasons in verdicts().",
    )

    def verdict_for(self, algo_key: str) -> AlgoVerdict:
        """The verdict for a single algorithm key against this archetype."""

        if self.not_registered:
            return AlgoVerdict.NOT_REGISTERED
        return AlgoVerdict.VALID if algo_key in self.valid_algos else AlgoVerdict.INVALID

    def reason_for(self, algo_key: str) -> str:
        """A human-readable reason for the verdict on ``algo_key``."""

        if self.not_registered:
            return f"archetype has no leg structure: {self.not_registered_reason}"
        if algo_key in self.valid_algos:
            types = ", ".join(t.value for t in self.instruction_types)
            return f"valid for instruction type(s) {types}"
        types = ", ".join(t.value for t in self.instruction_types)
        return (
            f"{algo_key} is not in ALGORITHMS_BY_INSTRUCTION_TYPE for any of this "
            f"archetype's instruction type(s) ({types}); the selector would raise "
            f"AlgorithmNotSupportedError / fall back to a default"
        )


def _instruction_types_for_structure(struct: ArchetypeLegStructure) -> tuple[InstructionType, ...]:
    """The set of InstructionTypes a leg structure induces (across all legs x venue-kinds)."""

    induced: set[InstructionType] = set()
    for leg in struct.legs:
        for group in leg.asset_groups:
            for kind in _ASSET_GROUP_VENUE_KINDS.get(group, (VenueExecutionKind.CLOB,)):
                for instrument in leg.instrument_types:
                    induced.add(instruction_type_for(kind, instrument))
    return tuple(sorted(induced, key=lambda t: t.value))


def _build_compatibility(struct: ArchetypeLegStructure) -> ArchetypeAlgoCompatibility:
    """Build the compatibility record for one archetype from its leg structure."""

    if struct.not_registered:
        return ArchetypeAlgoCompatibility(
            archetype_id=struct.archetype_id,
            not_registered=True,
            not_registered_reason=struct.not_registered_reason,
            instruction_types=(),
            valid_algos=(),
            default_algos=(),
            invalid_algos=tuple(sorted(EXECUTION_ALGOS)),
        )
    types = _instruction_types_for_structure(struct)
    valid: set[str] = set()
    defaults: set[str] = set()
    for t in types:
        valid.update(ALGOS_BY_INSTRUCTION_TYPE[t])
        defaults.add(DEFAULT_ALGO_BY_INSTRUCTION_TYPE[t])
    invalid = sorted(set(EXECUTION_ALGOS) - valid)
    return ArchetypeAlgoCompatibility(
        archetype_id=struct.archetype_id,
        not_registered=False,
        not_registered_reason="",
        instruction_types=types,
        valid_algos=tuple(sorted(valid)),
        default_algos=tuple(sorted(defaults)),
        invalid_algos=tuple(invalid),
    )


def _build_registry() -> dict[StrategyArchetype, ArchetypeAlgoCompatibility]:
    return {a: _build_compatibility(ARCHETYPE_LEG_STRUCTURES[a]) for a in StrategyArchetype}


ARCHETYPE_ALGO_COMPATIBILITY: Final[dict[StrategyArchetype, ArchetypeAlgoCompatibility]] = _build_registry()
"""Per-archetype execution-algorithm compatibility — EXHAUSTIVE (all 58 archetypes).

Derived from the leg-spec registry x the transcribed selector logic. A consumer
(the verdict matrix, the wizard) reads this to BLOCK an impossible
(archetype x execution-algo) combination with a cited reason.
"""


def algo_compatibility_for(archetype_id: StrategyArchetype) -> ArchetypeAlgoCompatibility:
    """Return the compatibility record for ``archetype_id`` (always present — exhaustive)."""

    return ARCHETYPE_ALGO_COMPATIBILITY[archetype_id]


def all_algo_compatibility() -> tuple[ArchetypeAlgoCompatibility, ...]:
    """Every archetype's compatibility record, sorted by archetype id (deterministic)."""

    return tuple(ARCHETYPE_ALGO_COMPATIBILITY[a] for a in sorted(StrategyArchetype, key=lambda x: x.value))


# ---------------------------------------------------------------------------
# Selector contradictions (operator wants these caught — code vs docs vs paths)
# ---------------------------------------------------------------------------


class SelectorContradiction(BaseModel):
    """A discrepancy between the execution-service selector code and docs/other paths."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    slug: str = Field(description="Stable id for the contradiction.")
    summary: str = Field(description="One-line statement of the contradiction.")
    citation: str = Field(description="The file:line evidence on each side.")
    resolved: bool = Field(
        default=False,
        description="Whether execution-service remediation (F33-F37) has landed for this slug.",
    )
    resolution: str = Field(
        default="",
        description="How + where this was reconciled, cited, when resolved=True.",
    )


SELECTOR_CONTRADICTIONS: Final[tuple[SelectorContradiction, ...]] = (
    SelectorContradiction(
        slug="iceberg_path_split",
        summary=(
            "ICEBERG is a valid algo on the manual-instruction API + adapters factory, "
            "but is EXCLUDED from the canonical ALGORITHMS_BY_INSTRUCTION_TYPE — "
            "requesting it through select_algorithm() falls back / would not validate, "
            "while the manual API accepts it."
        ),
        citation=(
            "selector.py:30-35 (ICEBERG removed comment) vs api/manual_instruction_helpers.py:70-75 "
            "(_SUPPORTED_ALGOS includes ICEBERG) + adapters/algorithm_factory.py (_ALGO_MAP 'iceberg')"
        ),
        resolved=True,
        resolution=(
            "RECONCILED 2026-07-30 as an intentional two-axis split, not a bug: ICEBERG has a real "
            "algo_library.IcebergAlgorithm implementation and stays valid for manual/live real-fill "
            "trading (no backtest-fill-simulation concern applies there); the canonical automated/"
            "backtest-driven selector deliberately excludes it for queue-position-modeling realism. "
            "Documented in unified-trading-pm codex/04-architecture/execution-algorithm-selection.md "
            "§3 + inline comments at both code sites (execution-service commit, "
            "capability_wizard_analysis_findings_2026_06_11.md F33)."
        ),
    ),
    SelectorContradiction(
        slug="sor_naming_mismatch",
        summary=(
            "The adapters factory keys the smart-order-router as 'sor' (lowercase) "
            "while the canonical selector knows it only as 'SMART_ORDER_ROUTER' — a "
            "caller forwarding select_algorithm()'s output into the factory would fail to resolve."
        ),
        citation="adapters/algorithm_factory.py (_ALGO_MAP 'sor') vs selector.py:39 ('SMART_ORDER_ROUTER')",
        resolved=True,
        resolution=(
            "FIXED 2026-07-30 — adapters/algorithm_factory.py._ALGO_MAP now carries BOTH 'sor' "
            "(back-compat) and 'smart_order_router' (canonical alias), both resolving to SORAlgorithm. "
            "Regression test: tests/unit/test_algorithm_factory.py::test_create_smart_order_router_alias "
            "(execution-service commit, capability_wizard_analysis_findings_2026_06_11.md F34)."
        ),
    ),
    SelectorContradiction(
        slug="ghost_algorithms",
        summary=(
            "SEQUENTIAL_LEGS / SPREAD_ROLL / BEST_PRICE / KELLY_STAKE are valid "
            "selector outputs (and some are the DEFAULT for their instruction type) "
            "but have NO ExecAlgorithm implementation class — the selector returns a "
            "string nothing executes."
        ),
        citation="selector.py:48-68 (valid sets + defaults) vs no class file in algorithms/ for these keys",
        resolved=True,
        resolution=(
            "DOCUMENTED 2026-07-30 (not a runtime bug — verified fail-loud, not silent): a caller "
            "routing one of these instruction types through ExecutionOrchestrator.execute_instruction "
            "gets algorithm_factory.get_algorithm() -> None -> ValueError('Unknown algorithm: ...'), "
            "never a silent misexecution. selector.py now inline-flags each GHOST key; building the "
            "real implementations is separate future strategy-service-scoped work, out of this "
            "reconciliation's scope. Registry here already carried implemented=False for all four — "
            "unchanged. See codex/04-architecture/execution-algorithm-selection.md §2 "
            "(capability_wizard_analysis_findings_2026_06_11.md F35)."
        ),
    ),
    SelectorContradiction(
        slug="heuristic_selector_bypasses_instruction_type",
        summary=(
            "engine/live/algo_selector.py applied a quantity-threshold heuristic "
            "(>=10 → TWAP else MARKET) that ignored InstructionType entirely — when "
            "active it would have bypassed ALL the canonical SWAP/TRADE/ZERO_ALPHA rules."
        ),
        citation=(
            "DELETED 2026-07-30 (was engine/live/algo_selector.py:31, quantity heuristic) vs "
            "selector.py:126-167 (canonical chain, unaffected)"
        ),
        resolved=True,
        resolution=(
            "FIXED 2026-07-30 by deletion, not repair — repo-wide grep confirmed AlgoSelector was "
            "never instantiated in any production code path (zero call sites besides its own module "
            "+ the package __init__.py re-export) and had zero test coverage: dead code with no live "
            "bypass, removed per the workspace no-shims/delete-deprecated-code rule rather than fixed "
            "in place. execution_service/engine/live/__init__.py no longer exports it. "
            "(execution-service commit, capability_wizard_analysis_findings_2026_06_11.md F36)."
        ),
    ),
    SelectorContradiction(
        slug="missing_ssot_doc",
        summary=(
            "selector.py cited UNIFIED_EXECUTION_DELTA.md as its taxonomy SSOT, but "
            "that document does not exist anywhere in the workspace — the selector "
            "code was the de-facto SSOT (this registry transcribes it declaratively)."
        ),
        citation="selector.py:7 (docstring 'Based on UNIFIED_EXECUTION_DELTA.md') vs no such file",
        resolved=True,
        resolution=(
            "FIXED 2026-07-30 — unified-trading-pm codex/04-architecture/execution-algorithm-selection.md "
            "is now the written SSOT; selector.py + instruction_type.py docstrings cite it in place of "
            "the nonexistent UNIFIED_EXECUTION_DELTA.md (execution-service commit, "
            "capability_wizard_analysis_findings_2026_06_11.md F37)."
        ),
    ),
)


__all__ = [
    "ALGOS_BY_INSTRUCTION_TYPE",
    "ARCHETYPE_ALGO_COMPATIBILITY",
    "DEFAULT_ALGO_BY_INSTRUCTION_TYPE",
    "EXECUTION_ALGOS",
    "SELECTOR_CONTRADICTIONS",
    "AlgoVerdict",
    "ArchetypeAlgoCompatibility",
    "ExecutionAlgo",
    "SelectorContradiction",
    "VenueExecutionKind",
    "algo_compatibility_for",
    "all_algo_compatibility",
    "instruction_type_for",
    "venue_kinds_for_asset_group",
]

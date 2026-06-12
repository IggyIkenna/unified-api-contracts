"""Tests for the archetype → execution-algorithm compatibility registry (Phase 6A).

Covers:
  - Exhaustive coverage: all 57 archetypes have a compatibility record.
  - The transcribed selector sets match selector.py's valid + default maps.
  - Impossible combinations are BLOCKED (the operator requirement): a ZERO_ALPHA
    archetype (pure staking/lending) admits ONLY BENCHMARK_FILL; a pure-SWAP (LP)
    archetype rejects TRADE algos; an options/bet archetype rejects TRADE algos.
  - venue-kind × instrument → InstructionType matches the selector's classification.
  - not_registered archetypes carry the NOT_REGISTERED verdict for every algo.
  - The ghost algorithms are flagged implemented=False.
  - Selector contradictions are enumerated.
  - Determinism of all_algo_compatibility() ordering.
"""

from __future__ import annotations

from unified_api_contracts.internal.architecture_v2.algo_compatibility import (
    ALGOS_BY_INSTRUCTION_TYPE,
    ARCHETYPE_ALGO_COMPATIBILITY,
    DEFAULT_ALGO_BY_INSTRUCTION_TYPE,
    EXECUTION_ALGOS,
    SELECTOR_CONTRADICTIONS,
    AlgoVerdict,
    VenueExecutionKind,
    algo_compatibility_for,
    all_algo_compatibility,
    instruction_type_for,
)
from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ArchetypeInstrumentType,
)
from unified_api_contracts.internal.architecture_v2.enums import StrategyArchetype
from unified_api_contracts.internal.domain.execution_service.types import InstructionType

# The ghost algorithms — valid selector outputs with NO implementation class.
_GHOST_ALGOS = frozenset(
    {"SEQUENTIAL_LEGS", "SPREAD_ROLL", "BEST_PRICE", "KELLY_STAKE", "BENCHMARK_FILL", "MAX_SLIPPAGE"}
)


def test_registry_covers_all_57_archetypes() -> None:
    assert set(ARCHETYPE_ALGO_COMPATIBILITY) == set(StrategyArchetype)
    assert len(ARCHETYPE_ALGO_COMPATIBILITY) == len(StrategyArchetype)


def test_transcribed_selector_sets_are_complete() -> None:
    """Every InstructionType has a valid set + a default, and every default is valid."""

    assert set(ALGOS_BY_INSTRUCTION_TYPE) == set(InstructionType)
    assert set(DEFAULT_ALGO_BY_INSTRUCTION_TYPE) == set(InstructionType)
    for t, algos in ALGOS_BY_INSTRUCTION_TYPE.items():
        assert DEFAULT_ALGO_BY_INSTRUCTION_TYPE[t] in algos
        for key in algos:
            assert key in EXECUTION_ALGOS, f"{key} not declared in EXECUTION_ALGOS"


def test_zero_alpha_archetype_admits_only_benchmark_fill() -> None:
    """Pure staking/lending archetypes are forced to BENCHMARK_FILL (impossible-combo block)."""

    for archetype in (
        StrategyArchetype.YIELD_STAKING_SIMPLE,
        StrategyArchetype.YIELD_ROTATION_LENDING,
        StrategyArchetype.CARRY_RECURSIVE_STAKED,
        StrategyArchetype.CARRY_RECURSIVE_BORROW_LENDING_ONLY,
    ):
        compat = algo_compatibility_for(archetype)
        assert compat.valid_algos == ("BENCHMARK_FILL",), f"{archetype}: {compat.valid_algos}"
        assert compat.verdict_for("TWAP") == AlgoVerdict.INVALID
        assert compat.verdict_for("SMART_ORDER_ROUTER") == AlgoVerdict.INVALID


def test_swap_only_archetype_rejects_trade_algos() -> None:
    """A pure-LP (SWAP) archetype admits SWAP algos, blocks CLOB-TRADE algos."""

    lp = algo_compatibility_for(StrategyArchetype.DEFI_LP_CONCENTRATED)
    assert lp.verdict_for("SMART_ORDER_ROUTER") == AlgoVerdict.VALID
    assert lp.verdict_for("SWAP_TWAP") == AlgoVerdict.VALID
    assert lp.verdict_for("TWAP") == AlgoVerdict.INVALID  # TRADE-only algo
    assert lp.verdict_for("ALMGREN_CHRISS") == AlgoVerdict.INVALID


def test_bet_archetype_rejects_trade_algos() -> None:
    """An event-settled (prediction/sports) archetype admits bet algos, blocks TRADE algos."""

    mde = algo_compatibility_for(StrategyArchetype.ML_DIRECTIONAL_EVENT_SETTLED)
    assert mde.verdict_for("BEST_PRICE") == AlgoVerdict.VALID
    assert mde.verdict_for("KELLY_STAKE") == AlgoVerdict.VALID
    assert mde.verdict_for("TWAP") == AlgoVerdict.INVALID
    assert mde.verdict_for("SMART_ORDER_ROUTER") == AlgoVerdict.INVALID


def test_instruction_type_classification_matches_selector() -> None:
    """venue-kind × instrument → InstructionType reproduces the selector's classification."""

    # CLOB + spot/perp → TRADE.
    assert instruction_type_for(VenueExecutionKind.CLOB, ArchetypeInstrumentType.SPOT) == InstructionType.TRADE
    assert instruction_type_for(VenueExecutionKind.CLOB, ArchetypeInstrumentType.PERP) == InstructionType.TRADE
    # DEX + spot → SWAP.
    assert instruction_type_for(VenueExecutionKind.DEX, ArchetypeInstrumentType.SPOT) == InstructionType.SWAP
    # lending / staking → ZERO_ALPHA regardless of venue kind.
    assert instruction_type_for(VenueExecutionKind.DEX, ArchetypeInstrumentType.LENDING) == InstructionType.ZERO_ALPHA
    assert instruction_type_for(VenueExecutionKind.CLOB, ArchetypeInstrumentType.STAKING) == InstructionType.ZERO_ALPHA
    # option → OPTIONS_COMBO; dated_future → FUTURES_ROLL.
    assert (
        instruction_type_for(VenueExecutionKind.CLOB, ArchetypeInstrumentType.OPTION) == InstructionType.OPTIONS_COMBO
    )
    assert (
        instruction_type_for(VenueExecutionKind.CLOB, ArchetypeInstrumentType.DATED_FUTURE)
        == InstructionType.FUTURES_ROLL
    )
    # event_settled → PREDICTION_BET vs SPORTS_EXCHANGE by venue kind.
    assert (
        instruction_type_for(VenueExecutionKind.PREDICTION, ArchetypeInstrumentType.EVENT_SETTLED)
        == InstructionType.PREDICTION_BET
    )
    assert (
        instruction_type_for(VenueExecutionKind.SPORTS, ArchetypeInstrumentType.EVENT_SETTLED)
        == InstructionType.SPORTS_EXCHANGE
    )
    # LP → SWAP.
    assert instruction_type_for(VenueExecutionKind.DEX, ArchetypeInstrumentType.LP) == InstructionType.SWAP


def test_not_registered_archetypes_carry_not_registered_verdict() -> None:
    """A not_registered archetype returns NOT_REGISTERED for every algo + has empty valid set."""

    for archetype in (
        StrategyArchetype.PORTFOLIO_RISK_PARITY,
        StrategyArchetype.PORTFOLIO_MULTI_STRATEGY,
        StrategyArchetype.ARBITRAGE_MEV_SANDWICH,
        StrategyArchetype.VOL_0DTE_PIN_RISK,
    ):
        compat = algo_compatibility_for(archetype)
        assert compat.not_registered is True
        assert compat.valid_algos == ()
        assert compat.not_registered_reason.strip()
        for key in EXECUTION_ALGOS:
            assert compat.verdict_for(key) == AlgoVerdict.NOT_REGISTERED


def test_every_algo_gets_an_explicit_verdict() -> None:
    """For every registered archetype, valid ∪ invalid == all algo keys (no silent gaps)."""

    all_keys = set(EXECUTION_ALGOS)
    for compat in all_algo_compatibility():
        if compat.not_registered:
            continue
        assert set(compat.valid_algos).isdisjoint(compat.invalid_algos)
        assert set(compat.valid_algos) | set(compat.invalid_algos) == all_keys
        # BENCHMARK_FILL is valid for every instruction type → always valid here.
        assert "BENCHMARK_FILL" in compat.valid_algos


def test_ghost_algorithms_flagged_unimplemented() -> None:
    """The ghost algorithms + mode-flags are flagged implemented=False; real ones True."""

    for key in _GHOST_ALGOS:
        assert EXECUTION_ALGOS[key].implemented is False, key
    for key in ("TWAP", "VWAP", "SMART_ORDER_ROUTER", "SOR_TWAP", "SWAP_TWAP", "ALMGREN_CHRISS"):
        assert EXECUTION_ALGOS[key].implemented is True, key


def test_selector_contradictions_enumerated() -> None:
    """The known selector code-vs-docs contradictions are carried with citations."""

    slugs = {c.slug for c in SELECTOR_CONTRADICTIONS}
    assert "iceberg_path_split" in slugs
    assert "ghost_algorithms" in slugs
    assert "missing_ssot_doc" in slugs
    for c in SELECTOR_CONTRADICTIONS:
        assert c.summary.strip() and c.citation.strip()


def test_all_algo_compatibility_deterministic_order() -> None:
    records = all_algo_compatibility()
    ids = [r.archetype_id.value for r in records]
    assert ids == sorted(ids)
    assert len(records) == len(StrategyArchetype)

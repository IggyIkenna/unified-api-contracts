"""Cross-repo invariant: execution-service interface/contract.

Validates that execution-service's key public surfaces remain stable:
- execution_service.models exports OperationType, ExecutionInstruction, ExecutionResult,
  ExecutionStatus, DeFiSignal, AtomicLeg — the core contracts strategy-service and
  trading-agent-service depend on (via the event-transport / instruction pipeline).
  Removing or renaming these breaks the execution pipeline silently.
- execution_service.orders exports OrderStatus, OrderTracker, UnifiedOrderManager —
  the order lifecycle surface. Removing any breaks order tracking at runtime.
- execution_service.strategy_instructions exports InstructionsLocation and the
  scheduling helpers — the GCS-backed instruction loader shared with strategy.
- unified_api_contracts.internal.domain.execution_service.types.InstructionType
  carries TRADE, SWAP, ZERO_ALPHA values — the algorithm-selector SSOT that
  execution_service.utils.instruction_type.py resolves on every order. UAC is the
  authoritative cross-repo SSOT; drift here silently mis-routes orders.

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — Phase 1
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _es_root() -> Path:
    return _workspace_root() / "execution-service" / "execution_service"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _import_names(source_path: Path) -> set[str]:
    """Return all names imported (or aliased) in source_path via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ImportFrom, ast.Import)):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _class_names(source_path: Path) -> set[str]:
    """Return all top-level class names defined in source_path."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}


# ---------------------------------------------------------------------------
# Sibling guard
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    es_sibling = _workspace_root() / "execution-service"
    if not es_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: execution-service not present at {es_sibling}; "
            "cross-repo execution-service invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Expected contracts
# ---------------------------------------------------------------------------

EXPECTED_MODEL_SYMBOLS: frozenset[str] = frozenset(
    [
        "OperationType",
        "ExecutionInstruction",
        "OrderType",
        "ExecutionResult",
        "ExecutionStatus",
        "SignalExecutionResult",
        "DeFiSignal",
        "AtomicLeg",
    ]
)

EXPECTED_ORDER_SYMBOLS: frozenset[str] = frozenset(
    [
        "OrderStatus",
        "OrderTracker",
        "UnifiedOrderManager",
    ]
)

EXPECTED_STRATEGY_INSTRUCTIONS_SYMBOLS: frozenset[str] = frozenset(
    [
        "InstructionsLocation",
        "build_instructions_location",
        "download_instructions_df",
        "upload_instructions_df",
        "instructions_to_schedule",
        "load_instructions",
    ]
)

# Core InstructionType values — the algorithm-selector SSOT.
# TRADE / SWAP / ZERO_ALPHA are the three primary execution branches.
EXPECTED_INSTRUCTION_TYPE_VALUES: frozenset[str] = frozenset(
    ["TRADE", "SWAP", "ZERO_ALPHA", "OPTIONS_COMBO", "FUTURES_ROLL"]
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_execution_service_models_stable() -> None:
    """execution_service/models/__init__.py re-exports the core execution contract types.

    OperationType, ExecutionInstruction, ExecutionResult, DeFiSignal, and AtomicLeg
    are the instruction-pipeline contracts. They are the input/output schema shared
    between strategy-service (which constructs instructions) and execution-service
    (which executes them). Removing any breaks the pipeline at the signal boundary.
    """
    _skip_if_absent()

    models_init = _es_root() / "models" / "__init__.py"
    assert models_init.is_file(), f"execution_service/models/__init__.py missing at {models_init}"

    imported = _import_names(models_init)
    missing = sorted(EXPECTED_MODEL_SYMBOLS - imported)
    assert not missing, (
        f"execution_service/models/__init__.py is MISSING contract symbols:\n"
        f"  {missing}\n\n"
        "These are the core execution instruction + result types — removing any "
        "breaks strategy-service's signal submission and execution-service's "
        "result reporting contract."
    )


def test_execution_service_orders_stable() -> None:
    """execution_service/orders/__init__.py re-exports the order lifecycle surface.

    OrderStatus, OrderTracker, and UnifiedOrderManager are the order-management
    objects. Removing any breaks order tracking in the live execution loop.
    """
    _skip_if_absent()

    orders_init = _es_root() / "orders" / "__init__.py"
    assert orders_init.is_file(), f"execution_service/orders/__init__.py missing at {orders_init}"

    imported = _import_names(orders_init)
    missing = sorted(EXPECTED_ORDER_SYMBOLS - imported)
    assert not missing, (
        f"execution_service/orders/__init__.py is MISSING order lifecycle symbols:\n"
        f"  {missing}\n\n"
        "OrderStatus / OrderTracker / UnifiedOrderManager are the order-lifecycle "
        "objects — removing any silently breaks order state tracking."
    )


def test_execution_service_strategy_instructions_stable() -> None:
    """execution_service/strategy_instructions/__init__.py has GCS instruction loader symbols.

    InstructionsLocation and the scheduling helpers are how strategy-service and
    execution-service share the instruction manifest from GCS. Removing these breaks
    instruction loading at execution startup.
    """
    _skip_if_absent()

    si_init = _es_root() / "strategy_instructions" / "__init__.py"
    assert si_init.is_file(), (
        f"execution_service/strategy_instructions/__init__.py missing at {si_init}"
    )

    imported = _import_names(si_init)
    missing = sorted(EXPECTED_STRATEGY_INSTRUCTIONS_SYMBOLS - imported)
    assert not missing, (
        f"execution_service/strategy_instructions/__init__.py is MISSING instruction-loader symbols:\n"
        f"  {missing}\n\n"
        "InstructionsLocation + scheduling helpers are the GCS-backed instruction "
        "manifest loader — removing any breaks execution startup."
    )


def test_execution_service_uac_instruction_type_stable() -> None:
    """unified_api_contracts.internal.domain.execution_service.types.InstructionType is stable.

    InstructionType is the algorithm-selector SSOT: execution_service maps every order
    to TRADE, SWAP, ZERO_ALPHA, etc. to pick the right execution algorithm. UAC is the
    cross-repo canonical source; if TRADE/SWAP/ZERO_ALPHA disappear from here, every
    order is silently mis-routed. (OPTIONS_COMBO and FUTURES_ROLL cover the options /
    futures roll branches.)
    """
    _skip_if_absent()

    types_py = (
        _workspace_root()
        / "unified-api-contracts"
        / "unified_api_contracts"
        / "internal"
        / "domain"
        / "execution_service"
        / "types.py"
    )
    assert types_py.is_file(), (
        f"unified_api_contracts/internal/domain/execution_service/types.py missing at {types_py}"
    )

    defined_classes = _class_names(types_py)
    assert "InstructionType" in defined_classes, (
        "unified_api_contracts/internal/domain/execution_service/types.py is MISSING "
        "the InstructionType class — this is the algorithm-selector SSOT for execution-service."
    )

    text = types_py.read_text(encoding="utf-8")
    missing_values = sorted(v for v in EXPECTED_INSTRUCTION_TYPE_VALUES if v not in text)
    assert not missing_values, (
        f"InstructionType in UAC types.py is MISSING algorithm-selector values:\n"
        f"  {missing_values}\n\n"
        "TRADE/SWAP/ZERO_ALPHA are the three primary execution branches that "
        "execution_service.utils.instruction_type resolves on every order — "
        "removing any silently mis-routes orders."
    )

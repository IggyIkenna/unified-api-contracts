"""Cross-repo invariant: trading-agent-service directive-pipeline contract vs strategy/execution.

Validates that trading-agent-service's published directive contract
(ArchetypeAllocationDirective fields, AllocationDirectiveLoop, MicroLoopOrchestrator)
aligns with the UAC canonical types that strategy-service consumes.

Uses static AST analysis for the trading-agent-service source (not installed in UAC venv).
UAC canonical types are imported directly (installed in this venv).

Negative-control contract: removing any field from ArchetypeAllocationDirective or
any required class from the service's engine/core modules makes the relevant test
fail — strategy-service/config_reloaders.py reads directive fields by attribute name
(directive.archetype_id, directive.source, directive.valid_until, etc.).

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — task -007
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from unified_api_contracts import (
    ArchetypeAllocationDirective,
    ComboStrategyType,
    StrategyPnlStreamEvent,
)
from unified_api_contracts.internal import CommoditySignal, RegimeState

# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _workspace_root() -> Path:
    """tests/<file>.py → tests/ → repo root → workspace root."""
    return Path(__file__).resolve().parents[2]


def _tas_root() -> Path:
    return _workspace_root() / "trading-agent-service" / "trading_agent_service"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _exported_names(source_path: Path) -> set[str]:
    """Return all top-level names declared in a module via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                exported = alias.asname if alias.asname else alias.name
                names.add(exported)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                exported = alias.asname if alias.asname else alias.name.split(".")[0]
                names.add(exported)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def _pydantic_fields(source_path: Path, class_name: str) -> set[str]:
    """Return the annotated field names declared in a Pydantic model class via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            fields: set[str] = set()
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    name = stmt.target.id
                    if not name.startswith("_"):
                        fields.add(name)
            return fields
    return set()


# ---------------------------------------------------------------------------
# Expected contracts
# ---------------------------------------------------------------------------

# Public classes that must remain in trading_agent_service/engine/orchestrator.py.
# strategy-service and execution-service expect MicroLoopOrchestrator as the
# runtime loop runner; removing it breaks the service's startup contract.
EXPECTED_ENGINE_CLASSES: frozenset[str] = frozenset(
    [
        "MicroLoopOrchestrator",
    ]
)

# Public classes/methods that must remain in trading_agent_service/core/allocation_directive_loop.py.
# strategy-service's StrategyDirectiveReloader receives directives via AllocationDirectiveLoop;
# the on_pnl_stream_event hook is the live-data entry point strategy-service fires against.
EXPECTED_DIRECTIVE_LOOP_SYMBOLS: frozenset[str] = frozenset(
    [
        "AllocationDirectiveLoop",
        "on_pnl_stream_event",
        "emit_directives",
    ]
)

# ArchetypeAllocationDirective fields consumed by strategy-service/config_reloaders.py.
# StrategyDirectiveReloader reads these fields by attribute name:
# - archetype_id: used as the dict key
# - allocation_weight: read by the portfolio allocator
# - enabled: gates archetype execution
# - param_overrides: per-archetype parameter customizations
# - valid_from, valid_until: TTL expiry check (directive.valid_until <= now)
# - source: surfaced in lifecycle logs for attribution
# - available_at: per-row write-time timestamp (prevents look-ahead in replay)
EXPECTED_DIRECTIVE_FIELDS: frozenset[str] = frozenset(
    [
        "archetype_id",
        "allocation_weight",
        "enabled",
        "param_overrides",
        "valid_from",
        "valid_until",
        "source",
        "available_at",
    ]
)


# ---------------------------------------------------------------------------
# Sibling guard (skip in per-repo CI; fail LOUDLY in full-workspace SIT)
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    tas_sibling = _workspace_root() / "trading-agent-service"
    if not tas_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: trading-agent-service not present at {tas_sibling}; "
            "cross-repo trading-agent-service invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_trading_agent_engine_orchestrator_stable() -> None:
    """MicroLoopOrchestrator class exists in trading_agent_service/engine/orchestrator.py.

    Skips in per-repo CI (no trading-agent-service sibling); runs in full-workspace SIT.
    Fails CLOSED if MicroLoopOrchestrator disappears — execution-service and the service
    entrypoint depend on it as the runtime loop runner that starts all 7 micro-loops.
    """
    _skip_if_absent()

    orchestrator_py = _tas_root() / "engine" / "orchestrator.py"
    assert orchestrator_py.is_file(), f"trading-agent-service engine/orchestrator.py missing at {orchestrator_py}"

    names = _exported_names(orchestrator_py)
    missing = sorted(EXPECTED_ENGINE_CLASSES - names)
    assert not missing, (
        f"trading_agent_service/engine/orchestrator.py is MISSING the following classes:\n  {missing}\n\n"
        "Removing MicroLoopOrchestrator is a BREAKING CHANGE — it is the runtime loop manager "
        "instantiated by the service entrypoint."
    )


def test_trading_agent_directive_loop_stable() -> None:
    """AllocationDirectiveLoop and its key hooks exist in core/allocation_directive_loop.py.

    strategy-service's StrategyDirectiveReloader receives ArchetypeAllocationDirective
    objects via AllocationDirectiveLoop.emit_directives().  The on_pnl_stream_event
    hook is the live entry point that triggers directive emission.  Removing any of
    these is a cross-repo BREAKING CHANGE.
    """
    _skip_if_absent()

    directive_loop_py = _tas_root() / "core" / "allocation_directive_loop.py"
    assert directive_loop_py.is_file(), (
        f"trading-agent-service core/allocation_directive_loop.py missing at {directive_loop_py}"
    )

    names = _exported_names(directive_loop_py)
    missing = sorted(EXPECTED_DIRECTIVE_LOOP_SYMBOLS - names)
    assert not missing, (
        f"trading_agent_service/core/allocation_directive_loop.py is MISSING the following symbols:\n  {missing}\n\n"
        "These are consumed by strategy-service's StrategyDirectiveReloader — removing them "
        "breaks the live directive pipeline."
    )


def test_trading_agent_directive_fields_stable() -> None:
    """ArchetypeAllocationDirective Pydantic fields match the consumer contract in strategy-service.

    strategy-service/config_reloaders.py reads ArchetypeAllocationDirective fields
    by attribute name (directive.archetype_id, directive.valid_until, etc.).  Removing
    any field silently breaks the directive deserialization + TTL expiry logic in
    StrategyDirectiveReloader.
    """
    _skip_if_absent()

    strategy_directives_py = (
        _workspace_root()
        / "unified-api-contracts"
        / "unified_api_contracts"
        / "internal"
        / "strategy_directives.py"
    )
    assert strategy_directives_py.is_file(), (
        f"UAC strategy_directives.py missing at {strategy_directives_py}"
    )

    fields = _pydantic_fields(strategy_directives_py, "ArchetypeAllocationDirective")
    missing = sorted(EXPECTED_DIRECTIVE_FIELDS - fields)
    assert not missing, (
        f"ArchetypeAllocationDirective is MISSING fields that strategy-service reads by attribute name:\n"
        f"  {missing}\n\n"
        "strategy-service/config_reloaders.py StrategyDirectiveReloader accesses these fields "
        "directly — removing them silently breaks directive TTL expiry and lifecycle logging."
    )


def test_trading_agent_uac_canonical_types_importable() -> None:
    """UAC exports the canonical types that trading-agent-service and consumers import.

    Confirms ArchetypeAllocationDirective, StrategyPnlStreamEvent, ComboStrategyType,
    CommoditySignal, and RegimeState are importable and carry the expected contract fields.
    """
    _skip_if_absent()

    # ArchetypeAllocationDirective must carry the fields strategy-service reads
    directive_fields = set(ArchetypeAllocationDirective.model_fields.keys())
    for field in EXPECTED_DIRECTIVE_FIELDS:
        assert field in directive_fields, (
            f"ArchetypeAllocationDirective.model_fields is MISSING '{field}' — "
            "strategy-service reads this field by attribute name from directive objects."
        )

    # StrategyPnlStreamEvent must be importable (allocation_directive_loop.py subscribes to it)
    assert hasattr(StrategyPnlStreamEvent, "model_fields"), (
        "StrategyPnlStreamEvent must be a Pydantic model — "
        "AllocationDirectiveLoop subscribes to it as an event from strategy-service."
    )

    # ComboStrategyType must be importable (trading-agent strategy spec uses it)
    assert ComboStrategyType is not None, (
        "ComboStrategyType must be importable from unified_api_contracts — "
        "trading-agent-service strategy specs reference it."
    )

    # CommoditySignal and RegimeState must be importable (L2 signal loop + ranker consume them)
    assert CommoditySignal is not None, (
        "CommoditySignal must be importable from unified_api_contracts.internal — "
        "trading-agent-service L2 signal loop and ranker consume it."
    )
    assert RegimeState is not None, (
        "RegimeState must be importable from unified_api_contracts.internal — "
        "trading-agent-service app/strategy/spec.py references it."
    )

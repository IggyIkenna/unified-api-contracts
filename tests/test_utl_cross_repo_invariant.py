"""Cross-repo invariant: unified-trading-library public API surface.

Validates that every public symbol other repos import from ``unified_trading_library``
is still declared/exported in its ``__init__.py`` (and sub-module ``__init__`` files).
Uses static AST analysis — no UTL installation in UAC's venv required.

This invariant runs in the full-workspace SIT only (sibling check guards per-repo CI).
Negative-control contract: removing any symbol in EXPECTED_PUBLIC_SYMBOLS from
``unified_trading_library/__init__.py`` makes this test fail — that IS the guard.

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md § Phase 1 (UTL)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Workspace helper
# ---------------------------------------------------------------------------


def _workspace_root() -> Path:
    """tests/<file>.py → tests/ → repo root → workspace root."""
    return Path(__file__).resolve().parents[2]


def _utl_root() -> Path:
    return _workspace_root() / "unified-trading-library" / "unified_trading_library"


def _collected_names(init_path: Path) -> set[str]:
    """Return the set of names declared/exported in a module via AST."""
    src = init_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(init_path))
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


# ---------------------------------------------------------------------------
# Cross-repo invariant: expected public symbols
# ---------------------------------------------------------------------------

# Symbols confirmed consumed by ≥2 sibling repos (MTDS, features-service, instruments-service, strategy-service).
# Removing any of these from unified_trading_library/__init__.py is a breaking cross-repo change
# and MUST be caught here before SIT validates and the LDR→main gate trusts it.
EXPECTED_PUBLIC_SYMBOLS: frozenset[str] = frozenset(
    [
        # Core batch pipeline / manifest
        "BatchPayload",
        "ManifestWriter",
        "ManifestConsolidatorStaleError",
        "ParquetSchemaEnforcer",
        "StreamingParquetWriter",
        "read_availability_index",
        # Config / cloud interface
        "BaseConfig",
        "UnifiedCloudConfig",
        "get_storage_client",
        "get_project_id",
        "resolve_bucket_name",
        # Service infrastructure
        "GracefulShutdownHandler",
        "make_health_router",
        "ServiceBootstrap",
        "ApiKeyReloader",
        # Domain / validation
        "DomainValidationService",
        "validate_data_type_schema",
        # Feature service base
        "BaseFeatureCalculator",
        "BaseFeatureServiceV2",
        "FeatureCalculator",
        "FeatureCalculatorRegistry",
        # Shard-level failure routing
        "PerLeafFailureRouter",
        # Event spine re-exported at top level
        "setup_events",
    ]
)

# Symbols in unified_trading_library/streaming/__init__.py (EventTransport facade).
# MTDS + features-service + MDPS import these to use the live=batch event-log spine.
EXPECTED_STREAMING_SYMBOLS: frozenset[str] = frozenset(
    [
        "EventTransport",
        "InMemoryTransport",
        "PubSubTransport",
        "publish",
        "read",
        "get_transport",
    ]
)

# Symbols in unified_trading_library/events/__init__.py consumed by many services.
EXPECTED_EVENTS_SYMBOLS: frozenset[str] = frozenset(
    [
        "setup_events",
        "emit_pipeline_heartbeat",
    ]
)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def test_utl_public_api_surface_stable() -> None:
    """All expected public symbols are declared in unified_trading_library/__init__.py.

    Skips in per-repo CI (no UTL sibling); runs in full-workspace SIT where the sibling is
    assembled. Fails CLOSED if any expected symbol disappears from the UTL public surface —
    that's the cross-repo breaking change this invariant exists to catch.
    """
    workspace = _workspace_root()
    utl_sibling = workspace / "unified-trading-library"
    if not utl_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: unified-trading-library not present at {utl_sibling}; "
            "cross-repo UTL invariant runs in full-workspace SIT only"
        )

    utl_init = _utl_root() / "__init__.py"
    assert utl_init.is_file(), f"UTL __init__.py missing at {utl_init}"

    exported = _collected_names(utl_init)

    missing = sorted(EXPECTED_PUBLIC_SYMBOLS - exported)
    assert not missing, (
        f"unified_trading_library/__init__.py is MISSING the following public symbols "
        f"that consuming sibling repos depend on:\n  {missing}\n\n"
        "Removing or renaming these is a cross-repo BREAKING CHANGE — add the "
        "renamed/moved symbol back as a re-export or update the consuming repos first."
    )


def test_utl_streaming_facade_stable() -> None:
    """EventTransport facade symbols are present in unified_trading_library/streaming/__init__.py.

    MTDS, MDPS, and features-service import EventTransport/InMemoryTransport/publish/read from
    this sub-module to use the live=batch event-log spine. Removal is a breaking cross-repo change.
    """
    workspace = _workspace_root()
    if not (workspace / "unified-trading-library").is_dir():
        pytest.skip("per-repo CI: unified-trading-library sibling absent")

    streaming_init = _utl_root() / "streaming" / "__init__.py"
    assert streaming_init.is_file(), f"UTL streaming __init__.py missing at {streaming_init}"

    exported = _collected_names(streaming_init)
    missing = sorted(EXPECTED_STREAMING_SYMBOLS - exported)
    assert not missing, (
        f"unified_trading_library/streaming/__init__.py is MISSING: {missing}\n"
        "These are live=batch EventTransport facade symbols consumed by MTDS/MDPS/features-service."
    )


def test_utl_events_module_stable() -> None:
    """setup_events + emit_pipeline_heartbeat are present in unified_trading_library/events/__init__.py.

    Nearly every service calls setup_events() at startup. Removal breaks all service boots.
    """
    workspace = _workspace_root()
    if not (workspace / "unified-trading-library").is_dir():
        pytest.skip("per-repo CI: unified-trading-library sibling absent")

    events_init = _utl_root() / "events" / "__init__.py"
    assert events_init.is_file(), f"UTL events __init__.py missing at {events_init}"

    exported = _collected_names(events_init)
    missing = sorted(EXPECTED_EVENTS_SYMBOLS - exported)
    assert not missing, (
        f"unified_trading_library/events/__init__.py is MISSING: {missing}\n"
        "setup_events is required at boot by every service that uses the event spine."
    )

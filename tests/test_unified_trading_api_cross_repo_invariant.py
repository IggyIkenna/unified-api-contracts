"""Cross-repo invariant: unified-trading-api public API contract matches consumers.

Validates that the unified-trading-api's registered route modules and route prefixes
are stable — i.e., a module removal or prefix rename that would break the UI
or client consumers is caught before SIT validates the promote.

Uses static AST analysis of unified_trading_api/main.py (not installed in UAC venv).

Negative-control contract: removing a route module import from main.py, or removing
its ``include_router`` call, makes these tests fail — that IS the guard for a
cross-repo breaking change to the API contract.

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — task -026
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _workspace_root() -> Path:
    """tests/<file>.py → tests/ → repo root → workspace root."""
    return Path(__file__).resolve().parents[2]


def _uta_root() -> Path:
    return _workspace_root() / "unified-trading-api" / "unified_trading_api"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _imported_route_modules(main_py: Path) -> set[str]:
    """Return the set of route module names imported in main.py via AST.

    Looks for ``from unified_trading_api.routes import ..., ...`` patterns.
    """
    src = main_py.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(main_py))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and "routes" in node.module
        ):
            for alias in node.names:
                modules.add(alias.asname if alias.asname else alias.name)
    return modules


def _registered_prefixes(main_py: Path) -> set[str]:
    """Return the set of route prefixes registered via include_router in main.py.

    Collects ``prefix=`` keyword argument values from all ``include_router(...)`` calls.
    Routes registered without a prefix (e.g., the health router) are excluded.
    """
    src = main_py.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(main_py))
    prefixes: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (
            isinstance(node.func, ast.Attribute) and node.func.attr == "include_router"
        ):
            continue
        for kw in node.keywords:
            if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                prefixes.add(str(kw.value.value))
    return prefixes


# ---------------------------------------------------------------------------
# Expected contracts (consumers confirmed to depend on these)
# ---------------------------------------------------------------------------

# Route modules that must remain importable from unified_trading_api.routes.
# The UI (unified-trading-system-ui) and client consumers hit these API surfaces.
# Removing or renaming a module here is a cross-repo breaking change.
EXPECTED_ROUTE_MODULES: frozenset[str] = frozenset(
    [
        "positions",
        "execution",
        "market_data",
        "ml",
        "reporting",
        "risk",
        "instruments",
        "alerts",
        "config",
        "users",
        "health",
        "audit",
        "admin",
        "registry",
        "strategy_performance",
        "strategy_subscriptions",
        "derivatives",
        "events",
        "deployment",
        "service_status",
        "trading_analytics",
        "calendar",
        "catalogue",
        "sports",
        "compliance",
        "documents",
    ]
)

# Route prefixes that must remain wired via include_router.
# These are the stable URL paths the UI and clients use.
EXPECTED_ROUTE_PREFIXES: frozenset[str] = frozenset(
    [
        "/positions",
        "/execution",
        "/market-data",
        "/ml",
        "/reporting",
        "/risk",
        "/instruments",
        "/alerts",
        "/config",
        "/users",
        "/admin",
        "/api/v1/registry",
        "/analytics",
        "/derivatives",
        "/events",
        "/deployment",
        "/service-status",
        "/calendar",
        "/catalogue",
        "/compliance",
        "/chat",
        "/documents",
        "/defi/basis",
        "/defi/lending",
        "/defi/liquidation",
        "/defi/lp",
    ]
)


# ---------------------------------------------------------------------------
# Sibling guard
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    uta_sibling = _workspace_root() / "unified-trading-api"
    if not uta_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: unified-trading-api not present at {uta_sibling}; "
            "cross-repo invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_unified_trading_api_route_modules_present() -> None:
    """All expected route modules are still imported in unified_trading_api/main.py.

    Skips in per-repo CI; runs in full-workspace SIT.
    Fails CLOSED if any expected module import disappears — that is the cross-repo
    breaking change this invariant exists to catch (the UI hits these API surfaces
    at runtime; a missing module means a 404 / import error at boot).
    """
    _skip_if_absent()

    main_py = _uta_root() / "main.py"
    assert main_py.is_file(), f"unified_trading_api/main.py missing at {main_py}"

    imported = _imported_route_modules(main_py)
    missing = sorted(EXPECTED_ROUTE_MODULES - imported)
    assert not missing, (
        f"unified_trading_api/main.py is no longer importing route modules "
        f"that UI/client consumers depend on:\n  {missing}\n\n"
        "Removing these imports is a cross-repo BREAKING CHANGE — the corresponding "
        "API routes will 404 at boot. Re-add the import or update consumers first."
    )


def test_unified_trading_api_route_module_files_exist() -> None:
    """All expected route module files exist on disk in unified_trading_api/routes/.

    Guards against a module being renamed or moved without updating main.py — an
    import that resolves at the checked path MUST have a file at that path.
    """
    _skip_if_absent()

    routes_dir = _uta_root() / "routes"
    assert routes_dir.is_dir(), f"unified_trading_api/routes/ missing at {routes_dir}"

    missing_files: list[str] = []
    for module in sorted(EXPECTED_ROUTE_MODULES):
        if not (routes_dir / f"{module}.py").is_file():
            missing_files.append(f"routes/{module}.py")

    assert not missing_files, (
        "unified_trading_api/routes/ is MISSING expected route module files:\n"
        + "\n".join(f"  {f}" for f in missing_files)
        + "\n\nThese files are required for the API to boot and serve the UI."
    )


def test_unified_trading_api_route_prefixes_wired() -> None:
    """All expected route prefixes are registered via include_router in main.py.

    Catches a prefix rename or removal that would silently break the UI's
    hard-coded API paths (e.g., ``/positions``, ``/execution``, ``/ml``).
    """
    _skip_if_absent()

    main_py = _uta_root() / "main.py"
    assert main_py.is_file(), f"unified_trading_api/main.py missing at {main_py}"

    registered = _registered_prefixes(main_py)
    missing = sorted(EXPECTED_ROUTE_PREFIXES - registered)
    assert not missing, (
        f"unified_trading_api/main.py is MISSING the following route prefixes "
        f"from include_router calls:\n  {missing}\n\n"
        "These URL paths are consumed by the unified-trading-system-ui and external "
        "clients. Removing or renaming them is a cross-repo BREAKING CHANGE."
    )

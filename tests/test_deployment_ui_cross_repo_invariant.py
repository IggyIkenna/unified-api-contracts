"""Cross-repo invariant: deployment-ui API-contract consumption vs deployment-api.

Two layers of validation:

1. deployment-api surface (AST on deployment_api/main.py): route modules and prefixes
   that deployment-ui consumes are still registered. A removal / prefix rename breaks
   deployment-ui's hard-coded API paths silently.

2. deployment-ui TypeScript source (text search on src/api/*.ts): the UI's own API
   client files reference the correct route paths and key interfaces. A drift between
   what the UI sends and what deployment-api serves causes silent 404s.

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — task -027 / Phase 1
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


def _dapi_root() -> Path:
    return _workspace_root() / "deployment-api" / "deployment_api"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _imported_route_modules(main_py: Path) -> set[str]:
    """Return the set of route module names imported in main.py via AST.

    Looks for ``from .routes import ..., ...`` patterns.
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
    Routers registered without a prefix (or with their own internal prefix) are excluded.
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
# Expected contracts (deployment-ui confirmed to depend on these)
# ---------------------------------------------------------------------------

# Route modules that must remain importable from deployment_api.routes.
# The deployment-ui calls these API surfaces at runtime; a missing module means
# a 404 / import error at boot.
EXPECTED_ROUTE_MODULES: frozenset[str] = frozenset(
    [
        "backfill_launch",
        "builds",
        "builds_history",
        "capabilities",
        "checklist",
        "cloud_builds",
        "config",
        "cost_daily",
        "data_status",
        "deploy_events_sse",
        "deployments",
        "deployments_inventory",
        "epics",
        "execution_backtest_launch",
        "fleet",
        "fleet_reconciliation",
        "health_overview",
        "log_stream",
        "ml_experiment_launch",
        "promote",
        "repo_ci",
        "repo_readiness",
        "risk_routes",
        "scenarios",
        "service_status",
        "services",
        "strategy_backtest_launch",
        "strategy_runs",
        "subscriptions",
        "treasury_routes",
        "unified_alerts",
        "user_management",
        "vm_deployments",
        "vm_events",
        "vm_health",
    ]
)

# Route prefixes that must remain wired via include_router.
# These are the stable URL paths that deployment-ui and other consumers use.
# Routers with their own internal prefix (fleet, repo_ci, cloud_builds,
# strategy_shard, log_stream, deploy_events_sse, etc.) are not listed here —
# they set prefix on the APIRouter itself, not in the include_router call.
EXPECTED_ROUTE_PREFIXES: frozenset[str] = frozenset(
    [
        "/api/services",
        "/api/config",
        "/api/checklists",
        "/api/epics",
        "/api/data-status",
        "/api/service-status",
        "/api/capabilities",
        "/api/builds",
        "/api/user-management",
        "/api/backfill",
        "/api/ml/experiment",
        "/api/strategy/backtest",
        "/api/execution/backtest",
        "/api/vm",
        "/api/repos",
        "/api/scenarios",
        "/api/risk",
        "/api/treasury",
    ]
)


# ---------------------------------------------------------------------------
# Sibling guard
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    dapi_sibling = _workspace_root() / "deployment-api"
    if not dapi_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: deployment-api not present at {dapi_sibling}; "
            "cross-repo invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_deployment_api_route_modules_present() -> None:
    """All expected route modules are still imported in deployment_api/main.py.

    Skips in per-repo CI; runs in full-workspace SIT.
    Fails CLOSED if any expected module import disappears — that is the cross-repo
    breaking change this invariant exists to catch (the deployment-ui hits these API
    surfaces at runtime; a missing module means a 404 / import error at boot).
    """
    _skip_if_absent()

    main_py = _dapi_root() / "main.py"
    assert main_py.is_file(), f"deployment_api/main.py missing at {main_py}"

    imported = _imported_route_modules(main_py)
    missing = sorted(EXPECTED_ROUTE_MODULES - imported)
    assert not missing, (
        f"deployment_api/main.py is no longer importing route modules "
        f"that deployment-ui consumers depend on:\n  {missing}\n\n"
        "Removing these imports is a cross-repo BREAKING CHANGE — the corresponding "
        "API routes will 404 at boot. Re-add the import or update consumers first."
    )


def test_deployment_api_route_module_files_exist() -> None:
    """All expected route module files exist on disk in deployment_api/routes/.

    Guards against a module being renamed or moved without updating main.py — an
    import that resolves at the checked path MUST have a file at that path.
    """
    _skip_if_absent()

    routes_dir = _dapi_root() / "routes"
    assert routes_dir.is_dir(), f"deployment_api/routes/ missing at {routes_dir}"

    missing_files: list[str] = []
    for module in sorted(EXPECTED_ROUTE_MODULES):
        module_file = routes_dir / f"{module}.py"
        module_pkg = routes_dir / module / "__init__.py"
        if not module_file.is_file() and not module_pkg.is_file():
            missing_files.append(f"routes/{module}.py (or routes/{module}/__init__.py)")

    assert not missing_files, (
        "deployment_api/routes/ is MISSING expected route module files:\n"
        + "\n".join(f"  {f}" for f in missing_files)
        + "\n\nThese files are required for the API to boot and serve the deployment-ui."
    )


def test_deployment_api_route_prefixes_wired() -> None:
    """All expected route prefixes are registered via include_router in main.py.

    Catches a prefix rename or removal that would silently break the deployment-ui's
    hard-coded API paths (e.g., ``/api/services``, ``/api/data-status``, ``/api/epics``).
    """
    _skip_if_absent()

    main_py = _dapi_root() / "main.py"
    assert main_py.is_file(), f"deployment_api/main.py missing at {main_py}"

    registered = _registered_prefixes(main_py)
    missing = sorted(EXPECTED_ROUTE_PREFIXES - registered)
    assert not missing, (
        f"deployment_api/main.py is MISSING the following route prefixes "
        f"from include_router calls:\n  {missing}\n\n"
        "These URL paths are consumed by the deployment-ui and external clients. "
        "Removing or renaming them is a cross-repo BREAKING CHANGE."
    )


# ---------------------------------------------------------------------------
# Layer 2 — deployment-ui TypeScript source self-check
# ---------------------------------------------------------------------------


def _ui_root() -> Path:
    return _workspace_root() / "deployment-ui"


def _skip_if_ui_absent() -> None:
    ui_sibling = _workspace_root() / "deployment-ui"
    if not ui_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: deployment-ui not present at {ui_sibling}; "
            "cross-repo deployment-ui source invariant runs in full-workspace SIT only"
        )


def _all_contain(source_path: Path, needles: list[str]) -> list[str]:
    """Return any needles missing from source_path."""
    text = source_path.read_text(encoding="utf-8")
    return [n for n in needles if n not in text]


def test_deployment_ui_deployment_api_client_routes_stable() -> None:
    """src/api/deploymentApi.ts references the deployment-api route paths it consumes.

    /api/services, /api/deployments, and /api/builds/ are the three primary API
    surfaces the deployment UI's dashboard calls. If these path strings disappear from
    deploymentApi.ts (drift from the deployment-api server routes), the dashboard
    silently 404s on every service-status and deploy-history request.
    """
    _skip_if_ui_absent()

    deployment_api_ts = _ui_root() / "src" / "api" / "deploymentApi.ts"
    assert deployment_api_ts.is_file(), (
        f"deployment-ui src/api/deploymentApi.ts missing at {deployment_api_ts}.\n\n"
        "deploymentApi.ts is the primary deployment-api consumption client — "
        "removing it drops all service-status, deploy-history, and VM observability."
    )

    required = ["/api/services", "/api/deployments", "/api/builds/"]
    missing = _all_contain(deployment_api_ts, required)
    assert not missing, (
        f"deployment-ui src/api/deploymentApi.ts is MISSING route references:\n"
        f"  {missing}\n\n"
        "/api/services / /api/deployments / /api/builds/ are the deployment-api "
        "endpoints the dashboard depends on — drift here causes silent 404s."
    )


def test_deployment_ui_repo_readiness_client_route_stable() -> None:
    """src/api/repoReadiness.ts references /api/repos/deploy-ready.

    The repo-readiness check is the gate the deployment-ui shows before allowing
    a deploy. If the route path drifts from what deployment-api serves, the
    readiness panel silently fails and users see stale / missing readiness state.
    """
    _skip_if_ui_absent()

    readiness_ts = _ui_root() / "src" / "api" / "repoReadiness.ts"
    assert readiness_ts.is_file(), (
        f"deployment-ui src/api/repoReadiness.ts missing at {readiness_ts}.\n\n"
        "repoReadiness.ts is the deploy-readiness gate client — removing it "
        "drops the readiness check from the deployment panel."
    )

    required = ["/api/repos/deploy-ready"]
    missing = _all_contain(readiness_ts, required)
    assert not missing, (
        f"deployment-ui src/api/repoReadiness.ts is MISSING route reference:\n"
        f"  {missing}\n\n"
        "/api/repos/deploy-ready is served by deployment-api repo_readiness router — "
        "removing this reference silently breaks the deploy-readiness gate."
    )


def test_deployment_ui_client_api_present() -> None:
    """src/api/client.ts is present — the client-management API surface.

    client.ts is the API client for client-facing data (client listing, etc.)
    that the deployment console uses. Removing it drops the client-management
    surface from the UI without any import errors at the component level.
    """
    _skip_if_ui_absent()

    client_ts = _ui_root() / "src" / "api" / "client.ts"
    assert client_ts.is_file(), (
        f"deployment-ui src/api/client.ts missing at {client_ts}.\n\n"
        "client.ts is the client-management API client — removing it drops "
        "client-data fetching from the deployment console."
    )

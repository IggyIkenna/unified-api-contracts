"""Cross-repo invariant: deployment-service Python package surface + HTTP API contract.

Validates that deployment-service's key surfaces remain stable for its consumers:
- deployment-api's deployments_inventory.py imports `classify_deployment_target`,
  `UnclassifiedDeploymentError` from deployment_service.deployment_classification and
  `CLOUD_RUN_JOBS` from deployment_service.cloud_run_job_registry — all by name.
- deployment-api's deployments_inventory.py imports `ACTIVE_PREFIX`, `ARCHIVE_PREFIX`,
  `DEFAULT_BUCKET`, `DeploymentRegistryEntry`, `vm_run_log_rolling_uri` from
  unified_trading_library.deployment_registry (relocated from deployment_service.
  deployments_registry — deployment-service@b665123e / unified-trading-library@5926c6f0).
- deployment-api's deployment_service_client.py calls:
  POST /api/v1/shards/calculate, POST /api/v1/deployments, GET /api/v1/data-status,
  POST /api/v1/vm-jobs/cancel, POST /api/v1/vm-jobs/status-batch,
  POST /api/v1/quota/acquire, POST /api/v1/quota/release,
  POST /api/v1/cloud-run/status-batch — all by path string.
- deployment-api's backfill_launch.py reads VM_PREFIX_TO_BUCKET from
  deployment-service/scripts/vm/vm_zombie_watchdog.py — referenced by file path.

Uses static AST analysis (deployment-service is not installed in UAC venv).

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — task -010
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


def _ds_root() -> Path:
    return _workspace_root() / "deployment-service" / "deployment_service"


def _ds_scripts_vm() -> Path:
    return _workspace_root() / "deployment-service" / "scripts" / "vm"


def _utl_root() -> Path:
    return _workspace_root() / "unified-trading-library" / "unified_trading_library"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _function_names(source_path: Path) -> set[str]:
    """Return names of all top-level function definitions in a module via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    return {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _class_names(source_path: Path) -> set[str]:
    """Return all class names declared in a module via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}


def _module_level_assign_names(source_path: Path) -> set[str]:
    """Return module-level assignment targets (e.g. CLOUD_RUN_JOBS = ...) via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _module_level_bound_names(source_path: Path) -> set[str]:
    """Module-level names bound by assignment OR ``from X import Y`` re-export.

    A consumer referencing ``module.NAME`` is satisfied whether NAME is defined
    locally or re-exported via import — both bind a module-level attribute. Used
    for surfaces (e.g. ``vm_zombie_watchdog.VM_PREFIX_TO_BUCKET``) whose SSOT may
    move into a package module while the original module keeps a back-compat
    re-export.
    """
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    names = _module_level_assign_names(source_path)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _route_paths(source_path: Path) -> set[str]:
    """Return HTTP path strings in route decorators (@router.get/post/etc) via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    paths: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr in ("get", "post", "put", "delete", "patch")
                    and decorator.args
                    and isinstance(decorator.args[0], ast.Constant)
                ):
                    paths.add(str(decorator.args[0].value))
    return paths


def _include_router_calls(source_path: Path) -> set[str]:
    """Return attribute names passed to app.include_router(X) via AST.

    Handles the pattern ``app.include_router(state.router)`` → returns "state.router".
    """
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    routers: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "include_router"
            and node.args
        ):
            arg = node.args[0]
            if isinstance(arg, ast.Attribute) and isinstance(arg.value, ast.Name):
                routers.add(f"{arg.value.id}.{arg.attr}")
    return routers


# ---------------------------------------------------------------------------
# Expected contracts
# ---------------------------------------------------------------------------

# deployment-api's deployments_inventory.py imports these by name.
EXPECTED_CLASSIFICATION_FUNCTIONS: frozenset[str] = frozenset(["classify_deployment_target"])
EXPECTED_CLASSIFICATION_CLASSES: frozenset[str] = frozenset(["UnclassifiedDeploymentError"])

# deployment-api's deployments_inventory.py imports these from deployments_registry.
EXPECTED_REGISTRY_NAMES: frozenset[str] = frozenset(
    [
        "ACTIVE_PREFIX",
        "ARCHIVE_PREFIX",
        "DEFAULT_BUCKET",
        "DeploymentRegistryEntry",
        "vm_run_log_rolling_uri",
    ]
)

# deployment-api reads CLOUD_RUN_JOBS from cloud_run_job_registry by name.
EXPECTED_CLOUD_RUN_REGISTRY_NAMES: frozenset[str] = frozenset(["CLOUD_RUN_JOBS"])

# deployment-api's main.py must include these routers.
EXPECTED_INCLUDED_ROUTERS: frozenset[str] = frozenset(["state.router", "orchestration.router", "ml_experiments.router"])

# deployment-api's deployment_service_client.py calls these routes by path.
EXPECTED_STATE_ROUTES: frozenset[str] = frozenset(
    [
        "/shards/calculate",
        "/deployments",
        "/data-status",
        "/vm-jobs/cancel",
        "/vm-jobs/status-batch",
        "/quota/acquire",
        "/quota/release",
        "/cloud-run/status-batch",
    ]
)

# deployment-api/backfill_launch.py reads this by file path.
EXPECTED_WATCHDOG_NAMES: frozenset[str] = frozenset(["VM_PREFIX_TO_BUCKET"])


# ---------------------------------------------------------------------------
# Sibling guard
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    ds_sibling = _workspace_root() / "deployment-service"
    if not ds_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: deployment-service not present at {ds_sibling}; "
            "cross-repo deployment-service invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_deployment_service_classification_surface_stable() -> None:
    """classify_deployment_target + UnclassifiedDeploymentError are stable in deployment_classification.py.

    deployment-api's deployments_inventory.py imports both by name:
        from deployment_service.deployment_classification import (
            UnclassifiedDeploymentError, classify_deployment_target
        )
    Removing either breaks inventory classification silently at import time.
    """
    _skip_if_absent()

    classification_py = _ds_root() / "deployment_classification.py"
    assert classification_py.is_file(), (
        f"deployment_service/deployment_classification.py missing at {classification_py}"
    )

    fns = _function_names(classification_py)
    missing_fns = sorted(EXPECTED_CLASSIFICATION_FUNCTIONS - fns)
    assert not missing_fns, (
        f"deployment_classification.py is MISSING functions that deployment-api imports:\n"
        f"  {missing_fns}\n\n"
        "deployment-api deployments_inventory.py imports classify_deployment_target — "
        "removing it breaks all Cloud Run and VM inventory classification."
    )

    classes = _class_names(classification_py)
    missing_cls = sorted(EXPECTED_CLASSIFICATION_CLASSES - classes)
    assert not missing_cls, (
        f"deployment_classification.py is MISSING classes that deployment-api imports:\n"
        f"  {missing_cls}\n\n"
        "deployment-api deployments_inventory.py imports UnclassifiedDeploymentError — "
        "removing it breaks error-handling in the inventory flow."
    )


def test_deployment_service_registry_surface_stable() -> None:
    """deployment_registry.py names that deployment-api imports by name are stable.

    Relocated from ``deployment_service.deployments_registry`` to
    ``unified_trading_library.deployment_registry`` (Phase 9 of
    utl_uac_reuse_consolidation_remediation_2026_06_10 — deployment-service@b665123e /
    unified-trading-library@5926c6f0) — it depended only on UTL primitives, no
    service-specific logic. deployment-api's deployments_inventory.py now imports:
        from unified_trading_library import (
            ACTIVE_PREFIX, ARCHIVE_PREFIX, DEFAULT_BUCKET,
            DeploymentRegistryEntry, vm_run_log_rolling_uri,
        )
    Removing any of these breaks the deployment registry read path.
    """
    utl_sibling = _workspace_root() / "unified-trading-library"
    if not utl_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: unified-trading-library not present at {utl_sibling}; "
            "cross-repo deployment-registry invariant runs in full-workspace SIT only"
        )

    registry_py = _utl_root() / "deployment_registry.py"
    assert registry_py.is_file(), f"unified_trading_library/deployment_registry.py missing at {registry_py}"

    names = _module_level_assign_names(registry_py) | _function_names(registry_py) | _class_names(registry_py)
    missing = sorted(EXPECTED_REGISTRY_NAMES - names)
    assert not missing, (
        f"deployment_registry.py is MISSING names that deployment-api imports:\n"
        f"  {missing}\n\n"
        "deployment-api deployments_inventory.py reads ACTIVE_PREFIX, ARCHIVE_PREFIX, "
        "DEFAULT_BUCKET, DeploymentRegistryEntry, vm_run_log_rolling_uri by name — "
        "removing any breaks the registry/GCS path derivation."
    )


def test_deployment_service_cloud_run_job_registry_stable() -> None:
    """CLOUD_RUN_JOBS in cloud_run_job_registry.py is stable.

    deployment-api's deployments_inventory.py imports:
        from deployment_service.cloud_run_job_registry import CLOUD_RUN_JOBS
    Removing CLOUD_RUN_JOBS breaks the Cloud Run inventory row generation.
    """
    _skip_if_absent()

    crj_py = _ds_root() / "cloud_run_job_registry.py"
    assert crj_py.is_file(), f"deployment_service/cloud_run_job_registry.py missing at {crj_py}"

    names = _module_level_assign_names(crj_py)
    missing = sorted(EXPECTED_CLOUD_RUN_REGISTRY_NAMES - names)
    assert not missing, (
        f"cloud_run_job_registry.py is MISSING names that deployment-api imports:\n"
        f"  {missing}\n\n"
        "deployment-api deployments_inventory.py iterates CLOUD_RUN_JOBS to build the "
        "Cloud Run deployment inventory — removing it silently empties the inventory."
    )


def test_deployment_service_api_routers_stable() -> None:
    """deployment-service/api/main.py registers state, orchestration, and ml_experiments routers.

    deployment-api's HTTP client calls /api/v1/ endpoints served by these routers.
    Removing any router registration makes deployment-api's HTTP calls return 404.
    """
    _skip_if_absent()

    main_py = _ds_root() / "api" / "main.py"
    assert main_py.is_file(), f"deployment_service/api/main.py missing at {main_py}"

    routers = _include_router_calls(main_py)
    missing = sorted(EXPECTED_INCLUDED_ROUTERS - routers)
    assert not missing, (
        f"deployment-service api/main.py is MISSING include_router calls:\n"
        f"  {missing}\n\n"
        "deployment-api deployment_service_client.py calls /shards/calculate, "
        "/deployments, /data-status, etc. — all served by state.router; "
        "orchestration.router and ml_experiments.router serve additional surfaces."
    )


def test_deployment_service_state_routes_stable() -> None:
    """State route paths that deployment-api's HTTP client calls are stable.

    deployment-api's deployment_service_client.py calls:
        /api/v1/shards/calculate, /api/v1/deployments, /api/v1/data-status,
        /api/v1/vm-jobs/cancel, /api/v1/vm-jobs/status-batch,
        /api/v1/quota/acquire, /api/v1/quota/release, /api/v1/cloud-run/status-batch
    Removing any route returns 404 to deployment-api's client at runtime.
    """
    _skip_if_absent()

    state_py = _ds_root() / "api" / "routes" / "state.py"
    assert state_py.is_file(), f"deployment_service/api/routes/state.py missing at {state_py}"

    routes = _route_paths(state_py)
    missing = sorted(EXPECTED_STATE_ROUTES - routes)
    assert not missing, (
        f"deployment-service state.py is MISSING route handlers that deployment-api calls:\n"
        f"  {missing}\n\n"
        "deployment-api deployment_service_client.py calls these routes by hard-coded path "
        "strings — removing any returns 404 and breaks deployment creation/sharding/status."
    )


def test_deployment_service_vm_zombie_watchdog_stable() -> None:
    """VM_PREFIX_TO_BUCKET is reachable as a module-level name in vm_zombie_watchdog.py.

    deployment-api's backfill_launch.py references this dict by file path:
        deployment-service/scripts/vm/vm_zombie_watchdog.py:VM_PREFIX_TO_BUCKET
    The name must be reachable as ``vm_zombie_watchdog.VM_PREFIX_TO_BUCKET``.

    The dict's SSOT moved into the deployment_service PACKAGE
    (``deployment_service/vm_prefix_registry.py``) on 2026-07-13 so it ships in the
    wheel + is importable from the deployment-api image where the fleet monitors
    run; the watchdog script now re-exports it via ``from
    deployment_service.vm_prefix_registry import VM_PREFIX_TO_BUCKET``. Hence this
    accepts the name whether it is locally assigned or re-exported by import.
    """
    _skip_if_absent()

    watchdog_py = _ds_scripts_vm() / "vm_zombie_watchdog.py"
    assert watchdog_py.is_file(), f"deployment-service/scripts/vm/vm_zombie_watchdog.py missing at {watchdog_py}"

    names = _module_level_bound_names(watchdog_py)
    missing = sorted(EXPECTED_WATCHDOG_NAMES - names)
    assert not missing, (
        f"vm_zombie_watchdog.py is MISSING module-level names that deployment-api references:\n"
        f"  {missing}\n\n"
        "deployment-api backfill_launch.py validates launcher prefixes against "
        "VM_PREFIX_TO_BUCKET at launch time — removing it (or its re-export from "
        "deployment_service.vm_prefix_registry) breaks the validation guard."
    )

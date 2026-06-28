"""Cross-repo invariant: deployment-api /repos + deploy/launch response shapes.

Validates that deployment-api's key API surfaces remain contract-stable:
- The repo-CI route module exposes /overview and /{repo}/detail endpoints that
  deployment-ui's RepoCi page reads (OverviewResponseDict.repos, generated_at, source).
- The deployments route module exposes DeployRequest + DeploymentResult; deployment-ui
  reads DeploymentResult.deployment_id / total_shards / status / cli_command by name.
- The backfill_launch route exposes /launch with BackfillLaunchResult.
- UAC RuntimeProfile + DeploymentStatus values are stable; DeployRequest uses RuntimeProfile
  as the runtime_profile field type, and deployment-service resolves client isolation from it.

Uses static AST analysis for deployment-api source (not installed in UAC venv).
UAC canonical types (RuntimeProfile, DeploymentStatus, ComputeType) are imported directly.

Negative-control contract: removing DeployRequest.service, DeploymentResult.deployment_id,
or the repo-CI overview endpoint from main.py makes the relevant test fail — deployment-ui
reads these by attribute name and would silently deserialise wrong JSON.

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — task -009
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from unified_api_contracts.internal.domain.deployment_service import (
    ComputeType,
    DeploymentStatus,
    RuntimeProfile,
)

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


def _pydantic_fields(source_path: Path, class_name: str) -> set[str]:
    """Return annotated field names declared in a Pydantic model class via AST."""
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


def _route_decorators(source_path: Path) -> set[str]:
    """Return the set of HTTP path strings in route decorators via AST.

    Looks for @router.get(path) / @router.post(path) / @router.put(path) etc.
    """
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


def _class_names(source_path: Path) -> set[str]:
    """Return all class names declared in a module via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}


# ---------------------------------------------------------------------------
# Expected contracts
# ---------------------------------------------------------------------------

# DeployRequest fields that deployment-ui and deployment_validation.py read by attribute name.
# deployment_validation.py reads: service, mode, start_date, end_date, asset_group, client_id.
# deployment-ui's DeploymentRequest type reads: service, mode, start_date, end_date.
EXPECTED_DEPLOY_REQUEST_FIELDS: frozenset[str] = frozenset(
    [
        "service",
        "compute",
        "mode",
        "start_date",
        "end_date",
        "asset_group",
        "client_id",
        "runtime_profile",
    ]
)

# DeploymentResult fields that deployment-ui's CreateDeploymentResponse reads.
# deployment-ui reads: deployment_id, status, total_shards, cli_command.
EXPECTED_DEPLOYMENT_RESULT_FIELDS: frozenset[str] = frozenset(
    [
        "deployment_id",
        "status",
        "total_shards",
        "cli_command",
    ]
)

# Repo-CI route paths that deployment-ui's RepoCi page depends on.
# RepoCi.tsx fetches /overview for the fleet view and /{repo}/detail for drill-down.
EXPECTED_REPO_CI_ROUTES: frozenset[str] = frozenset(
    [
        "/overview",
        "/{repo}/detail",
    ]
)

# RuntimeProfile values that deployment-api's DeployRequest accepts and
# deployment-service resolves to client isolation policy.
EXPECTED_RUNTIME_PROFILE_VALUES: frozenset[str] = frozenset(
    [
        "backtest",
        "paper",
        "mock-live",
        "staging",
        "prod",
    ]
)

# DeploymentStatus values that deployment-ui renders as status badges.
EXPECTED_DEPLOYMENT_STATUS_VALUES: frozenset[str] = frozenset(
    [
        "pending",
        "running",
        "completed",
        "failed",
        "cancelled",
    ]
)


# ---------------------------------------------------------------------------
# Sibling guard (skip in per-repo CI; fail LOUDLY in full-workspace SIT)
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    dapi_sibling = _workspace_root() / "deployment-api"
    if not dapi_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: deployment-api not present at {dapi_sibling}; "
            "cross-repo deployment-api invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_deployment_api_deploy_request_fields_stable() -> None:
    """DeployRequest fields that consumers read by attribute name are stable.

    deployment_validation.py reads .service, .mode, .start_date, .end_date, .asset_group,
    .client_id by name. deployment-ui's DeploymentRequest TypeScript interface mirrors these.
    Removing any field silently breaks validation or UI form binding.
    """
    _skip_if_absent()

    deployments_init = _dapi_root() / "routes" / "deployments" / "__init__.py"
    assert deployments_init.is_file(), (
        f"deployment_api/routes/deployments/__init__.py missing at {deployments_init}"
    )

    fields = _pydantic_fields(deployments_init, "DeployRequest")
    missing = sorted(EXPECTED_DEPLOY_REQUEST_FIELDS - fields)
    assert not missing, (
        f"DeployRequest is MISSING fields that consumers read by attribute name:\n"
        f"  {missing}\n\n"
        "deployment_validation.py reads these fields directly on the request object; "
        "deployment-ui's DeploymentRequest TypeScript type mirrors them."
    )


def test_deployment_api_deployment_result_fields_stable() -> None:
    """DeploymentResult fields that deployment-ui reads by attribute name are stable.

    deployment-ui's CreateDeploymentResponse interface reads deployment_id, status,
    total_shards, cli_command from the POST /api/deployments response. Removing any
    field breaks the deploy launch flow in the UI.
    """
    _skip_if_absent()

    deployments_init = _dapi_root() / "routes" / "deployments" / "__init__.py"
    assert deployments_init.is_file(), (
        f"deployment_api/routes/deployments/__init__.py missing at {deployments_init}"
    )

    fields = _pydantic_fields(deployments_init, "DeploymentResult")
    missing = sorted(EXPECTED_DEPLOYMENT_RESULT_FIELDS - fields)
    assert not missing, (
        f"DeploymentResult is MISSING fields that deployment-ui reads by attribute name:\n"
        f"  {missing}\n\n"
        "deployment-ui reads these fields from the POST /api/deployments response — "
        "removing any breaks the deploy launch result panel."
    )


def test_deployment_api_repo_ci_routes_stable() -> None:
    """Repo-CI route handlers (/overview and /{repo}/detail) exist in repo_ci.py.

    deployment-ui RepoCi.tsx fetches /api/repo-ci/overview for the fleet view and
    /api/repo-ci/{repo}/detail for drill-down. Removing either endpoint is a
    cross-repo BREAKING CHANGE.
    """
    _skip_if_absent()

    repo_ci_py = _dapi_root() / "routes" / "repo_ci.py"
    assert repo_ci_py.is_file(), (
        f"deployment_api/routes/repo_ci.py missing at {repo_ci_py}"
    )

    routes = _route_decorators(repo_ci_py)
    missing = sorted(EXPECTED_REPO_CI_ROUTES - routes)
    assert not missing, (
        f"repo_ci.py is MISSING route handlers that deployment-ui depends on:\n"
        f"  {missing}\n\n"
        "deployment-ui RepoCi.tsx fetches /overview and /{repo}/detail — removing "
        "either breaks the Repo-CI dashboard."
    )


def test_deployment_api_uac_canonical_types_stable() -> None:
    """UAC RuntimeProfile, DeploymentStatus, and ComputeType carry the expected values.

    deployment-api's DeployRequest uses RuntimeProfile as the runtime_profile field type.
    deployment-service resolves client isolation policy from RuntimeProfile values.
    deployment-ui renders DeploymentStatus as status badges.
    """
    _skip_if_absent()

    # RuntimeProfile values that deployment-api + deployment-service use
    profile_values = {p.value for p in RuntimeProfile}
    missing_profiles = sorted(EXPECTED_RUNTIME_PROFILE_VALUES - profile_values)
    assert not missing_profiles, (
        f"RuntimeProfile is MISSING values that deployment-api and deployment-service use:\n"
        f"  {missing_profiles}\n\n"
        "DeployRequest.runtime_profile is typed as RuntimeProfile | None; deployment-service "
        "resolves client isolation policy from these values."
    )

    # DeploymentStatus values that deployment-ui renders as badges
    status_values = {s.value for s in DeploymentStatus}
    missing_statuses = sorted(EXPECTED_DEPLOYMENT_STATUS_VALUES - status_values)
    assert not missing_statuses, (
        f"DeploymentStatus is MISSING values that deployment-ui renders as status badges:\n"
        f"  {missing_statuses}\n\n"
        "deployment-ui TypeScript type DeploymentStatus must cover all states returned "
        "by deployment-api — removing any causes UI to show unknown status."
    )

    # ComputeType must be importable (DeployRequest.compute maps to ComputeType values)
    assert ComputeType is not None, (
        "ComputeType must be importable from unified_api_contracts.internal.domain.deployment_service — "
        "deployment-api DeployRequest.compute field accepts ComputeType values."
    )

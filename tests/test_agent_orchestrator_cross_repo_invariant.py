"""Cross-repo invariant: agent-orchestrator role-registry / dispatch contract.

Validates that agent-orchestrator's key API surfaces remain stable:
- server/server.py registers the critical router modules (slots_worker, state, backlog,
  roles) — removing any silently drops a complete orchestration API surface.
- server/routes/slots_worker.py exposes the slot worker lifecycle API: boot, heartbeat,
  progress, done, blocked, messages. All slot workers call these endpoints on every run;
  removing any breaks the entire worker dispatch loop.
- server/routes/roles.py exposes GET /api/roles — the role-registry read surface that
  the dashboard and backlog dispatch use to enumerate available worker roles.
- server/routes/state.py exposes GET /api/state and GET /api/healthz — the orchestrator
  state feed and health check consumed by the dashboard and fleet watchdog.
- server/role_registry.py defines RoleSpec with the dispatch contract fields:
  role, model, skills, triggers. These fields drive the auto-spawn and dispatch logic;
  removing or renaming any breaks role-based dispatch.
- server/auth.py provides JWT auth infrastructure (HS256/ES256 dual-algo). Its presence
  is a safety invariant — removing it exposes every authenticated route.

Uses static AST analysis for agent-orchestrator source (not installed in UAC venv).

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — task -015
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


def _ao_root() -> Path:
    return _workspace_root() / "agent-orchestrator" / "server"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _route_paths(source_path: Path) -> set[str]:
    """Return HTTP path strings in route decorators via AST."""
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


def _include_router_names(source_path: Path) -> set[str]:
    """Return names passed to any .include_router(...) call via AST.

    Handles ``app.include_router(module.router)`` → "module.router" and
    ``app.include_router(variable)`` → "variable".
    """
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "include_router"
            and node.args
        ):
            arg = node.args[0]
            if isinstance(arg, ast.Name):
                names.add(arg.id)
            elif isinstance(arg, ast.Attribute) and isinstance(arg.value, ast.Name):
                names.add(f"{arg.value.id}.{arg.attr}")
    return names


def _class_names(source_path: Path) -> set[str]:
    """Return top-level class names defined in the module via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    }


def _dataclass_field_names(source_path: Path, class_name: str) -> set[str]:
    """Return annotated field names of a specific class in the module via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    fields: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.add(item.target.id)
    return fields


# ---------------------------------------------------------------------------
# Expected contracts
# ---------------------------------------------------------------------------

# Critical router modules registered in server/server.py.
# Each module's router exposes a complete API surface — removing any silently
# drops all routes in that module without import errors.
EXPECTED_REGISTERED_ROUTERS: frozenset[str] = frozenset(
    [
        "_slots_worker_routes.router",
        "_state_routes.router",
        "_backlog_routes.router",
        "_roles_routes.router",
    ]
)

# Slot worker lifecycle routes in slots_worker.py.
# Slot workers call boot→heartbeat→progress→done on every task run.
# Blocked + messages are the bidirectional communication channels.
EXPECTED_SLOT_WORKER_ROUTES: frozenset[str] = frozenset(
    [
        "/api/slots/{slot_id}/boot",
        "/api/slots/{slot_id}/heartbeat",
        "/api/slots/{slot_id}/progress",
        "/api/slots/{slot_id}/done",
        "/api/slots/{slot_id}/blocked",
        "/api/slots/{slot_id}/messages",
    ]
)

# State/health routes in state.py.
EXPECTED_STATE_ROUTES: frozenset[str] = frozenset(
    ["/api/state", "/api/healthz"]
)

# RoleSpec dispatch fields — these drive auto-spawn and role-based dispatch.
EXPECTED_ROLE_SPEC_FIELDS: frozenset[str] = frozenset(
    ["role", "model", "skills", "triggers"]
)


# ---------------------------------------------------------------------------
# Sibling guard
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    ao_sibling = _workspace_root() / "agent-orchestrator"
    if not ao_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: agent-orchestrator not present at {ao_sibling}; "
            "cross-repo agent-orchestrator invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_agent_orchestrator_critical_routers_registered() -> None:
    """server/server.py registers all critical router modules.

    Four router modules (slots_worker, state, backlog, roles) supply the complete
    orchestration API. Removing any silently drops all routes in that module —
    returning 404 to slot workers, the dashboard, or the backlog dispatch loop.
    """
    _skip_if_absent()

    server_py = _ao_root() / "server.py"
    assert server_py.is_file(), f"agent-orchestrator server/server.py missing at {server_py}"

    registered = _include_router_names(server_py)
    missing = sorted(EXPECTED_REGISTERED_ROUTERS - registered)
    assert not missing, (
        f"agent-orchestrator server/server.py is MISSING include_router registrations:\n"
        f"  {missing}\n\n"
        "Critical router modules (slots_worker, state, backlog, roles) must all be "
        "registered — removing any drops a complete orchestration API surface."
    )


def test_agent_orchestrator_slot_worker_routes_stable() -> None:
    """Slot worker lifecycle routes (boot, heartbeat, progress, done, blocked, messages) are stable.

    All slot workers call POST /api/slots/{slot_id}/boot on startup, heartbeat during
    work, progress to report intermediate results, done on completion, and blocked when
    waiting for operator input. GET /api/slots/{slot_id}/messages receives operator
    replies. Removing any breaks the entire worker dispatch loop.
    """
    _skip_if_absent()

    slots_py = _ao_root() / "routes" / "slots_worker.py"
    assert slots_py.is_file(), (
        f"agent-orchestrator server/routes/slots_worker.py missing at {slots_py}"
    )

    routes = _route_paths(slots_py)
    missing = sorted(EXPECTED_SLOT_WORKER_ROUTES - routes)
    assert not missing, (
        f"agent-orchestrator routes/slots_worker.py is MISSING route handlers:\n"
        f"  {missing}\n\n"
        "All six slot worker lifecycle routes must be present — removing any breaks "
        "the boot→heartbeat→progress→done worker loop and operator messaging."
    )


def test_agent_orchestrator_roles_route_stable() -> None:
    """GET /api/roles is stable in routes/roles.py.

    The dashboard and backlog dispatch logic call GET /api/roles to enumerate
    available worker roles and their dispatch parameters. Removing this route
    breaks role-based dispatch and the dashboard role panel.
    """
    _skip_if_absent()

    roles_py = _ao_root() / "routes" / "roles.py"
    assert roles_py.is_file(), (
        f"agent-orchestrator server/routes/roles.py missing at {roles_py}"
    )

    routes = _route_paths(roles_py)
    assert "/api/roles" in routes, (
        "routes/roles.py is MISSING GET /api/roles route handler.\n\n"
        "Dashboard and backlog dispatch call GET /api/roles to enumerate worker roles "
        "— removing it breaks role-based dispatch and the dashboard role panel."
    )


def test_agent_orchestrator_state_routes_stable() -> None:
    """GET /api/state and GET /api/healthz are stable in routes/state.py.

    The dashboard calls GET /api/state to display orchestrator state. Fleet watchdogs
    and health checks call GET /api/healthz to verify the orchestrator is alive.
    """
    _skip_if_absent()

    state_py = _ao_root() / "routes" / "state.py"
    assert state_py.is_file(), (
        f"agent-orchestrator server/routes/state.py missing at {state_py}"
    )

    routes = _route_paths(state_py)
    missing = sorted(EXPECTED_STATE_ROUTES - routes)
    assert not missing, (
        f"routes/state.py is MISSING route handlers that dashboard/watchdog depends on:\n"
        f"  {missing}\n\n"
        "GET /api/state (dashboard) and GET /api/healthz (fleet watchdog) must be present."
    )


def test_agent_orchestrator_role_spec_dispatch_fields_stable() -> None:
    """RoleSpec in server/role_registry.py has all required dispatch fields.

    The auto-spawn and role-based dispatch logic reads RoleSpec.role, .model, .skills,
    and .triggers to select the appropriate worker and compute tier. Removing or renaming
    any field breaks the dispatch algorithm without triggering import errors.
    """
    _skip_if_absent()

    registry_py = _ao_root() / "role_registry.py"
    assert registry_py.is_file(), (
        f"agent-orchestrator server/role_registry.py missing at {registry_py}"
    )

    assert "RoleSpec" in _class_names(registry_py), (
        "RoleSpec class not found in server/role_registry.py.\n\n"
        "RoleSpec is the dispatch contract — auto-spawn reads it to select worker role and model."
    )

    fields = _dataclass_field_names(registry_py, "RoleSpec")
    missing = sorted(EXPECTED_ROLE_SPEC_FIELDS - fields)
    assert not missing, (
        f"RoleSpec is MISSING dispatch fields:\n"
        f"  {missing}\n\n"
        "RoleSpec.role, .model, .skills, .triggers drive role-based dispatch — "
        "removing any field breaks auto-spawn without import errors."
    )


def test_agent_orchestrator_auth_module_present() -> None:
    """server/auth.py JWT auth module is present.

    JWT auth (HS256/ES256 dual-algo) gates every authenticated slot worker and
    dashboard route. Removing auth.py exposes the entire orchestration API without
    import errors — the auth dependency would silently disappear at module import time.
    """
    _skip_if_absent()

    auth_py = _ao_root() / "auth.py"
    assert auth_py.is_file(), (
        f"agent-orchestrator server/auth.py missing at {auth_py}.\n\n"
        "JWT auth (HS256/ES256) gates all authenticated routes — removing auth.py "
        "exposes the entire orchestration API without import errors."
    )

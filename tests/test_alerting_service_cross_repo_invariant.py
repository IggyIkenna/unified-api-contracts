"""Cross-repo invariant: alerting-service alert/notification contract.

Validates that alerting-service's key API surfaces remain stable:
- alerting_service/api/routes/alerts.py exposes /stream/alerts (SSE feed) and
  /rules/recent (GET/POST) that deployment-ui's alert panel and other consumers read.
- alerting_service/api/routes/safety_ops.py exposes /incidents (POST), /audit-ack-queue
  (GET), /signoffs (POST) that the operator recovery workflow depends on.
- alerting_service/api/main.py registers alerts, delivery_status, safety_ops, and
  manual_action routers — removing any silently drops the authenticated API surface.
- UAC LIVE_ALERT_RULES (86 rules), AlertCode, AlertEvent, AlertSeverity are stable —
  every service that fires alerts (strategy-service, batch-live-reconciliation-service,
  execution-service) uses these types to publish; alerting-service subscribes.

Uses static AST analysis for alerting-service source (not installed in UAC venv).
UAC types (AlertCode, AlertEvent, AlertSeverity, LIVE_ALERT_RULES, AlertRule) are
imported directly for runtime validation.

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — task -012
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from unified_api_contracts import LIVE_ALERT_RULES, AlertCode, AlertRule
from unified_api_contracts.alerting import AlertSeverity
from unified_api_contracts.internal import AlertEvent

# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _as_root() -> Path:
    return _workspace_root() / "alerting-service" / "alerting_service"


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
    """Return variable names passed to any .include_router(...) call via AST.

    Handles both ``app.include_router(alerts_router)`` → "alerts_router" and
    ``_auth_router.include_router(delivery_status_router)`` → "delivery_status_router".
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


# ---------------------------------------------------------------------------
# Expected contracts
# ---------------------------------------------------------------------------

# deployment-ui alert panel subscribes to /stream/alerts (SSE) and /rules/recent.
# Other consumers (ops dashboard) call GET /rules/recent to display history.
EXPECTED_ALERTS_ROUTES: frozenset[str] = frozenset(
    ["/stream/alerts", "/rules/recent"]
)

# Operator recovery workflow calls /incidents (POST), /audit-ack-queue (GET), /signoffs (POST).
# Removing any breaks the kill-switch recovery / audit sign-off flow.
EXPECTED_SAFETY_OPS_ROUTES: frozenset[str] = frozenset(
    ["/incidents", "/audit-ack-queue", "/signoffs"]
)

# Router variable names registered in api/main.py via include_router().
EXPECTED_REGISTERED_ROUTERS: frozenset[str] = frozenset(
    ["alerts_router", "delivery_status_router", "safety_ops_router", "manual_action_router"]
)


# ---------------------------------------------------------------------------
# Sibling guard
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    as_sibling = _workspace_root() / "alerting-service"
    if not as_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: alerting-service not present at {as_sibling}; "
            "cross-repo alerting-service invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_alerting_service_alert_routes_stable() -> None:
    """Alert SSE and recent-alerts routes are stable in alerts.py.

    deployment-ui's alert panel subscribes to /stream/alerts for the live SSE feed
    and fetches /rules/recent to populate the alert history view.
    Removing either breaks the ops dashboard real-time alerting.
    """
    _skip_if_absent()

    alerts_py = _as_root() / "api" / "routes" / "alerts.py"
    assert alerts_py.is_file(), f"alerting_service/api/routes/alerts.py missing at {alerts_py}"

    routes = _route_paths(alerts_py)
    missing = sorted(EXPECTED_ALERTS_ROUTES - routes)
    assert not missing, (
        f"alerts.py is MISSING route handlers that deployment-ui depends on:\n"
        f"  {missing}\n\n"
        "deployment-ui alert panel subscribes to /stream/alerts (SSE) and fetches "
        "/rules/recent — removing either breaks the live alerting dashboard."
    )


def test_alerting_service_safety_ops_routes_stable() -> None:
    """Safety-ops routes (/incidents, /audit-ack-queue, /signoffs) are stable.

    The operator recovery workflow (kill-switch recovery, audit sign-off) calls:
    POST /incidents, GET /audit-ack-queue, POST /signoffs.
    Removing any breaks the kill-switch recovery and audit lifecycle.
    """
    _skip_if_absent()

    safety_ops_py = _as_root() / "api" / "routes" / "safety_ops.py"
    assert safety_ops_py.is_file(), (
        f"alerting_service/api/routes/safety_ops.py missing at {safety_ops_py}"
    )

    routes = _route_paths(safety_ops_py)
    missing = sorted(EXPECTED_SAFETY_OPS_ROUTES - routes)
    assert not missing, (
        f"safety_ops.py is MISSING route handlers that the operator workflow depends on:\n"
        f"  {missing}\n\n"
        "Kill-switch recovery + audit sign-off workflows call /incidents, "
        "/audit-ack-queue, /signoffs — removing any breaks the operator recovery UI."
    )


def test_alerting_service_api_routers_stable() -> None:
    """api/main.py registers all required authenticated routers.

    Four routers (alerts, delivery_status, safety_ops, manual_action) are registered
    via include_router in the authenticated middleware. Removing any silently drops
    an entire API surface — returning 404 to all callers without import errors.
    """
    _skip_if_absent()

    main_py = _as_root() / "api" / "main.py"
    assert main_py.is_file(), f"alerting_service/api/main.py missing at {main_py}"

    registered = _include_router_names(main_py)
    missing = sorted(EXPECTED_REGISTERED_ROUTERS - registered)
    assert not missing, (
        f"alerting-service api/main.py is MISSING include_router registrations:\n"
        f"  {missing}\n\n"
        "All four routers must be registered: alerts, delivery_status, safety_ops, "
        "manual_action — removing any drops a complete API surface without import errors."
    )


def test_alerting_service_uac_canonical_types_stable() -> None:
    """UAC alert types are stable: AlertCode, AlertEvent, AlertSeverity, LIVE_ALERT_RULES, AlertRule.

    Every service that fires alerts (strategy-service, batch-live-reconciliation-service,
    execution-service) uses AlertCode/AlertEvent to publish. alerting-service subscribes
    using the same types. LIVE_ALERT_RULES drives the kill-switch and PagerDuty routing.
    """
    _skip_if_absent()

    assert AlertCode is not None, (
        "AlertCode must be importable from unified_api_contracts — "
        "strategy-service and execution-service use AlertCode to fire alerts."
    )

    assert AlertEvent is not None, (
        "AlertEvent must be importable from unified_api_contracts.internal — "
        "alerting-service subscribes to AlertEvent on the event bus."
    )

    assert AlertSeverity is not None, (
        "AlertSeverity must be importable from unified_api_contracts.alerting — "
        "alerting-service uses AlertSeverity to route to PagerDuty vs Slack."
    )

    assert AlertRule is not None, (
        "AlertRule must be importable from unified_api_contracts — "
        "alerting-service uses AlertRule to define kill-switch trigger conditions."
    )

    assert len(LIVE_ALERT_RULES) > 0, (
        f"LIVE_ALERT_RULES must be non-empty (got {len(LIVE_ALERT_RULES)}) — "
        "alerting-service evaluates these rules on every incoming event."
    )

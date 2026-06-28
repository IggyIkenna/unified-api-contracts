"""Cross-repo invariant: fund-administration-service fund-admin contract.

Validates that fund-administration-service's lifecycle API surfaces remain stable:
- Subscription lifecycle: POST /subscriptions, GET /subscriptions/{id}, and
  /approve + /reject + /settle transitions. client-reporting-api and allocators_router
  consume subscription state; removing any transition endpoint silently breaks the
  subscription workflow.
- Redemption lifecycle: POST /redemptions, GET /redemptions/{id}, and
  /approve + /reject + /process + /settle transitions. Removing any breaks the
  redemption workflow used by the fund admin operator panel.
- Fund allocation: GET /funds/{fund_id}/allocations, POST /rebalance, GET /nav/history.
  Removing any breaks the portfolio allocation view and NAV history reporting.
- UAC fund-admin domain types are stable: AllocatorSubscription, AllocatorRedemption,
  FundAllocation, FundNAVSnapshot, SubscriptionStatus, RedemptionStatus — these types
  are the SSOT contract; client-reporting-api and the fund-admin operator panel both
  consume them.

The routes use app.add_api_route() (not decorator-based) — the AST helper reads
string literals passed as the first positional argument to add_api_route() calls.

Client-funds isolation invariant: fund-administration-service MUST NOT import
TransferCoordinator or cross-client transfer utilities — fund flows are always
per-allocator + per-fund-id, never cross-client.

Uses static AST analysis for fund-administration-service source (not installed in UAC venv).
UAC types are imported directly for runtime validation.

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — task -014
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from unified_api_contracts import (
    AllocatorRedemption,
    AllocatorSubscription,
    FundAllocation,
    FundNAVSnapshot,
    RedemptionStatus,
    SubscriptionStatus,
)

# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _fas_root() -> Path:
    return _workspace_root() / "fund-administration-service" / "fund_administration_service"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _add_api_route_paths(source_path: Path) -> set[str]:
    """Return path strings from add_api_route(path, ...) calls via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    paths: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_api_route"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            paths.add(str(node.args[0].value))
    return paths


def _import_names(source_path: Path) -> set[str]:
    """Return all names imported in the module via AST (import + from-import)."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ImportFrom, ast.Import)):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


# ---------------------------------------------------------------------------
# Expected contracts
# ---------------------------------------------------------------------------

# Subscription lifecycle — allocators subscribe funds via these routes.
# POST /subscriptions creates the request; /approve + /reject + /settle complete it.
EXPECTED_SUBSCRIPTION_ROUTES: frozenset[str] = frozenset(
    [
        "/subscriptions",
        "/subscriptions/{subscription_id}",
        "/subscriptions/{subscription_id}/approve",
        "/subscriptions/{subscription_id}/reject",
        "/subscriptions/{subscription_id}/settle",
    ]
)

# Redemption lifecycle — allocators redeem via these routes.
# /process is the fund-admin step that executes the actual redemption wire.
EXPECTED_REDEMPTION_ROUTES: frozenset[str] = frozenset(
    [
        "/redemptions",
        "/redemptions/{redemption_id}",
        "/redemptions/{redemption_id}/approve",
        "/redemptions/{redemption_id}/reject",
        "/redemptions/{redemption_id}/process",
        "/redemptions/{redemption_id}/settle",
    ]
)

# Fund allocation — portfolio allocation view + NAV history reads.
EXPECTED_ALLOCATION_ROUTES: frozenset[str] = frozenset(
    [
        "/funds/{fund_id}/allocations",
        "/funds/{fund_id}/allocations/rebalance",
        "/funds/{fund_id}/nav/history",
    ]
)

# Cross-client isolation: these symbols must NOT appear in fund-administration-service.
# Fund flows are always per-allocator + per-fund, never cross-client rebalance.
BANNED_CROSS_CLIENT_SYMBOLS: frozenset[str] = frozenset(
    ["TransferCoordinator", "CrossClientTransferForbiddenError"]
)


# ---------------------------------------------------------------------------
# Sibling guard
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    fas_sibling = _workspace_root() / "fund-administration-service"
    if not fas_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: fund-administration-service not present at {fas_sibling}; "
            "cross-repo fund-administration-service invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_fund_administration_service_subscription_routes_stable() -> None:
    """Subscription lifecycle routes are stable in api/main.py.

    The complete subscription lifecycle (create → approve/reject → settle) is
    registered via add_api_route in _register_subscription_routes(). Removing any
    transition endpoint breaks the allocator subscription workflow.
    """
    _skip_if_absent()

    main_py = _fas_root() / "api" / "main.py"
    assert main_py.is_file(), f"fund_administration_service/api/main.py missing at {main_py}"

    routes = _add_api_route_paths(main_py)
    missing = sorted(EXPECTED_SUBSCRIPTION_ROUTES - routes)
    assert not missing, (
        f"fund-administration-service api/main.py is MISSING subscription route registrations:\n"
        f"  {missing}\n\n"
        "All five subscription lifecycle routes must be present — removing any breaks "
        "the allocator subscription workflow (create→approve/reject→settle)."
    )


def test_fund_administration_service_redemption_routes_stable() -> None:
    """Redemption lifecycle routes are stable in api/main.py.

    The complete redemption lifecycle (create → approve/reject → process → settle)
    is registered via add_api_route. /process is the wire-execution step — removing
    it blocks the fund-admin operator from completing redemptions.
    """
    _skip_if_absent()

    main_py = _fas_root() / "api" / "main.py"
    assert main_py.is_file(), f"fund_administration_service/api/main.py missing at {main_py}"

    routes = _add_api_route_paths(main_py)
    missing = sorted(EXPECTED_REDEMPTION_ROUTES - routes)
    assert not missing, (
        f"fund-administration-service api/main.py is MISSING redemption route registrations:\n"
        f"  {missing}\n\n"
        "All six redemption lifecycle routes must be present — removing any breaks "
        "the redemption workflow (create→approve/reject→process→settle)."
    )


def test_fund_administration_service_allocation_routes_stable() -> None:
    """Fund allocation routes are stable in api/main.py.

    /allocations lists current fund allocations, /rebalance triggers the capital
    rebalance, /nav/history provides the NAV time-series for reporting.
    client-reporting-api reads these to populate the fund allocation view.
    """
    _skip_if_absent()

    main_py = _fas_root() / "api" / "main.py"
    assert main_py.is_file(), f"fund_administration_service/api/main.py missing at {main_py}"

    routes = _add_api_route_paths(main_py)
    missing = sorted(EXPECTED_ALLOCATION_ROUTES - routes)
    assert not missing, (
        f"fund-administration-service api/main.py is MISSING allocation route registrations:\n"
        f"  {missing}\n\n"
        "Fund allocation routes (/allocations, /rebalance, /nav/history) must be present — "
        "removing any breaks the portfolio allocation view and NAV history reporting."
    )


def test_fund_administration_service_uac_domain_types_stable() -> None:
    """UAC fund-admin domain types are stable: AllocatorSubscription, AllocatorRedemption,
    FundAllocation, FundNAVSnapshot, SubscriptionStatus, RedemptionStatus.

    These types are the contract between fund-administration-service and its consumers
    (client-reporting-api, the allocators router, and the fund-admin operator panel).
    Every request body and response type in the service API is a UAC-defined model.
    """
    _skip_if_absent()

    assert AllocatorSubscription is not None, (
        "AllocatorSubscription must be importable from unified_api_contracts — "
        "fund-administration-service uses it as the subscription domain type."
    )

    assert AllocatorRedemption is not None, (
        "AllocatorRedemption must be importable from unified_api_contracts — "
        "fund-administration-service uses it as the redemption domain type."
    )

    assert FundAllocation is not None, (
        "FundAllocation must be importable from unified_api_contracts — "
        "fund-administration-service uses it as the allocation domain type."
    )

    assert FundNAVSnapshot is not None, (
        "FundNAVSnapshot must be importable from unified_api_contracts — "
        "fund-administration-service uses it to record NAV strikes on approve."
    )

    assert SubscriptionStatus is not None, (
        "SubscriptionStatus must be importable from unified_api_contracts — "
        "subscription state machine transitions use SubscriptionStatus values."
    )

    assert RedemptionStatus is not None, (
        "RedemptionStatus must be importable from unified_api_contracts — "
        "redemption state machine transitions use RedemptionStatus values."
    )


def test_fund_administration_service_no_cross_client_transfer() -> None:
    """fund-administration-service does not import cross-client transfer utilities.

    Client-funds isolation (codex/04-architecture/client-funds-isolation.md): funds
    NEVER move between clients. fund-administration-service processes per-allocator
    fund flows only. Importing TransferCoordinator would risk cross-client fund movement.
    """
    _skip_if_absent()

    main_py = _fas_root() / "api" / "main.py"
    assert main_py.is_file(), f"fund_administration_service/api/main.py missing at {main_py}"

    imported = _import_names(main_py)
    violations = sorted(BANNED_CROSS_CLIENT_SYMBOLS & imported)
    assert not violations, (
        f"fund-administration-service api/main.py imports cross-client transfer symbols:\n"
        f"  {violations}\n\n"
        "Client-funds isolation: funds NEVER move between clients. "
        "fund-administration-service must not use TransferCoordinator or "
        "CrossClientTransferForbiddenError — those belong to per-client-isolated transfer flows."
    )

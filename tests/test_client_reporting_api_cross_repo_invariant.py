"""Cross-repo invariant: client-reporting-api reporting contract.

Validates that client-reporting-api's key reporting surfaces remain stable:
- api/main.py registers the core client-data routers (clients, trades, pnl, performance, reports)
  — removing any silently drops a complete reporting surface returning 404 to all consumers.
- api/routes/clients.py router prefix /api/v1/clients is stable — unified-trading-system-ui
  fetches client list and client detail via this prefix.
- api/routes/trades.py router prefix /api/v1/trades is stable — the trade blotter depends on it.
- api/routes/pnl.py exposes /pnl and /performance that the PnL panel reads.
- api/routes/performance.py exposes /summary, /positions, /balances, /coin-breakdown that the
  portfolio performance panel reads.
- UAC core reporting types (LedgerRow, PositionLedgerRow, EventType, TradeFillRecord) are stable
  — the daily-ledger-digest, portfolio-metrics, recon-view, and ledger-views cores all depend on
  these types.

Uses static AST analysis for client-reporting-api source (not installed in UAC venv).
UAC types are imported directly for runtime validation.

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — task -013
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from unified_api_contracts import EventType, LedgerRow, PositionLedgerRow
from unified_api_contracts.internal import TradeFillRecord

# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _cra_root() -> Path:
    return _workspace_root() / "client-reporting-api" / "client_reporting_api"


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

    Handles both ``app.include_router(clients_router)`` → "clients_router" and
    ``_auth_router.include_router(module.router)`` → "module.router".
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


def _api_router_prefix(source_path: Path) -> str | None:
    """Return the prefix= argument of the first APIRouter(...) call via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "APIRouter"
        ):
            for kw in node.keywords:
                if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                    return str(kw.value.value)
    return None


# ---------------------------------------------------------------------------
# Expected contracts
# ---------------------------------------------------------------------------

# Core routers registered in api/main.py via include_router.
# Removing any silently drops a complete reporting API surface.
EXPECTED_REGISTERED_ROUTERS: frozenset[str] = frozenset(
    ["clients_router", "trades_router", "pnl_router", "performance_router", "reports_router"]
)

# unified-trading-system-ui reads /pnl (daily summary) and /performance (metrics view).
EXPECTED_PNL_ROUTES: frozenset[str] = frozenset(["/pnl", "/performance"])

# unified-trading-system-ui portfolio view reads all four performance sub-routes.
EXPECTED_PERFORMANCE_ROUTES: frozenset[str] = frozenset(
    ["/summary", "/positions", "/balances", "/coin-breakdown"]
)


# ---------------------------------------------------------------------------
# Sibling guard
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    cra_sibling = _workspace_root() / "client-reporting-api"
    if not cra_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: client-reporting-api not present at {cra_sibling}; "
            "cross-repo client-reporting-api invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_client_reporting_api_routers_stable() -> None:
    """api/main.py registers all required authenticated routers.

    Five routers (clients, trades, pnl, performance, reports) supply the core client
    reporting surfaces. Removing any silently drops an entire API surface returning 404
    to all callers without import errors.
    """
    _skip_if_absent()

    main_py = _cra_root() / "api" / "main.py"
    assert main_py.is_file(), f"client_reporting_api/api/main.py missing at {main_py}"

    registered = _include_router_names(main_py)
    missing = sorted(EXPECTED_REGISTERED_ROUTERS - registered)
    assert not missing, (
        f"client-reporting-api api/main.py is MISSING include_router registrations:\n"
        f"  {missing}\n\n"
        "All five core routers must be registered: clients, trades, pnl, performance, reports"
        " — removing any drops a complete reporting API surface without import errors."
    )


def test_client_reporting_api_clients_router_prefix_stable() -> None:
    """clients.py APIRouter prefix /api/v1/clients is stable.

    unified-trading-system-ui fetches the client list and client detail via
    /api/v1/clients (list) and /api/v1/clients/{client_id} (detail).
    Changing the prefix silently redirects all client requests to 404.
    """
    _skip_if_absent()

    clients_py = _cra_root() / "api" / "routes" / "clients.py"
    assert clients_py.is_file(), (
        f"client_reporting_api/api/routes/clients.py missing at {clients_py}"
    )

    prefix = _api_router_prefix(clients_py)
    assert prefix == "/api/v1/clients", (
        f"clients.py APIRouter prefix changed: got {prefix!r}, expected '/api/v1/clients'.\n\n"
        "unified-trading-system-ui depends on GET /api/v1/clients and "
        "GET /api/v1/clients/{{client_id}} for the client list and detail views."
    )


def test_client_reporting_api_trades_router_prefix_stable() -> None:
    """trades.py APIRouter prefix /api/v1/trades is stable.

    unified-trading-system-ui's trade blotter fetches GET /api/v1/trades for the
    trade history. Changing the prefix silently breaks the blotter without import errors.
    """
    _skip_if_absent()

    trades_py = _cra_root() / "api" / "routes" / "trades.py"
    assert trades_py.is_file(), (
        f"client_reporting_api/api/routes/trades.py missing at {trades_py}"
    )

    prefix = _api_router_prefix(trades_py)
    assert prefix == "/api/v1/trades", (
        f"trades.py APIRouter prefix changed: got {prefix!r}, expected '/api/v1/trades'.\n\n"
        "unified-trading-system-ui depends on GET /api/v1/trades for the trade blotter."
    )


def test_client_reporting_api_pnl_routes_stable() -> None:
    """/pnl and /performance routes are stable in pnl.py.

    unified-trading-system-ui's PnL panel fetches /pnl for the daily PnL summary
    and /performance for the performance metrics view. Removing either breaks the
    portfolio PnL display.
    """
    _skip_if_absent()

    pnl_py = _cra_root() / "api" / "routes" / "pnl.py"
    assert pnl_py.is_file(), f"client_reporting_api/api/routes/pnl.py missing at {pnl_py}"

    routes = _route_paths(pnl_py)
    missing = sorted(EXPECTED_PNL_ROUTES - routes)
    assert not missing, (
        f"pnl.py is MISSING route handlers that unified-trading-system-ui depends on:\n"
        f"  {missing}\n\n"
        "unified-trading-system-ui PnL panel reads /pnl and /performance — "
        "removing either breaks the portfolio PnL view."
    )


def test_client_reporting_api_performance_routes_stable() -> None:
    """Performance routes (/summary, /positions, /balances, /coin-breakdown) are stable.

    unified-trading-system-ui's portfolio view reads all four performance sub-routes to
    render the performance summary, positions table, balance breakdown, and coin allocation.
    """
    _skip_if_absent()

    performance_py = _cra_root() / "api" / "routes" / "performance.py"
    assert performance_py.is_file(), (
        f"client_reporting_api/api/routes/performance.py missing at {performance_py}"
    )

    routes = _route_paths(performance_py)
    missing = sorted(EXPECTED_PERFORMANCE_ROUTES - routes)
    assert not missing, (
        f"performance.py is MISSING route handlers that unified-trading-system-ui depends on:\n"
        f"  {missing}\n\n"
        "unified-trading-system-ui portfolio view reads /summary, /positions, /balances, "
        "/coin-breakdown — removing any breaks the portfolio performance panel."
    )


def test_client_reporting_api_uac_core_types_stable() -> None:
    """UAC core reporting types are stable: LedgerRow, PositionLedgerRow, EventType, TradeFillRecord.

    LedgerRow + PositionLedgerRow + EventType drive the daily-ledger-digest, portfolio-metrics,
    and ledger-views cores. TradeFillRecord drives the recon-view and trade history endpoint.
    """
    _skip_if_absent()

    assert LedgerRow is not None, (
        "LedgerRow must be importable from unified_api_contracts — "
        "client-reporting-api core uses LedgerRow to build daily ledger digests and PnL views."
    )

    assert PositionLedgerRow is not None, (
        "PositionLedgerRow must be importable from unified_api_contracts — "
        "portfolio-metrics uses PositionLedgerRow for per-position calculations."
    )

    assert EventType is not None, (
        "EventType must be importable from unified_api_contracts — "
        "ledger-strategy and ledger-views filter LedgerRow events by EventType."
    )

    assert TradeFillRecord is not None, (
        "TradeFillRecord must be importable from unified_api_contracts.internal — "
        "recon-view and ledger-views depend on TradeFillRecord for the trade history."
    )

"""Cross-repo invariant: unified-trading-system-ui API-contract consumption.

Validates that unified-trading-system-ui's key API client surfaces remain stable:
- lib/api/types.ts defines PaginatedResponse — the shared paginated response shape
  that unified-trading-api returns for all list endpoints. Removing or renaming it
  breaks the extractData helper and every list view in the UI.
- lib/api/deployment-launch-client.ts defines LaunchResult and the launch param
  interfaces (MlExperimentParams, StrategyBacktestParams) that the launch UI sends
  to deployment-api POST /api/deploy/*/launch. These are the API-contract consumption
  types; if they drift from the deployment-api schema, launches silently fail.
- lib/api/promote-client.ts references POST /api/promote/{strategyId}/{manifestId}
  and POST .../demote — these are the promote/demote endpoints served by
  unified-trading-api. If the route path changes in either repo, promotes silently fail.
- lib/api/safety-ops-proxy.ts exists — the safety-ops surface (kill-switch + audit
  sign-off) that alerting-service exposes and the UI consumes.

Uses text-search analysis on TypeScript source files (not Python AST — UI source is TS).

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — task -016
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ui_root() -> Path:
    return _workspace_root() / "unified-trading-system-ui"


# ---------------------------------------------------------------------------
# Text-search helpers
# ---------------------------------------------------------------------------


def _contains(source_path: Path, needle: str) -> bool:
    """Return True if needle appears anywhere in source_path."""
    return needle in source_path.read_text(encoding="utf-8")


def _all_contain(source_path: Path, needles: list[str]) -> list[str]:
    """Return any needles missing from source_path."""
    text = source_path.read_text(encoding="utf-8")
    return [n for n in needles if n not in text]


# ---------------------------------------------------------------------------
# Sibling guard
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    ui_sibling = _workspace_root() / "unified-trading-system-ui"
    if not ui_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: unified-trading-system-ui not present at {ui_sibling}; "
            "cross-repo unified-trading-system-ui invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_unified_trading_system_ui_paginated_response_stable() -> None:
    """lib/api/types.ts defines PaginatedResponse with the standard shape fields.

    PaginatedResponse is the shared API-contract type for all unified-trading-api list
    endpoints. The extractData helper and every list view (positions, trades, instruments)
    depend on the data, pagination, mode, as_of fields. Removing or renaming any field
    silently drops list data from the UI without TypeScript errors at call sites.
    """
    _skip_if_absent()

    types_ts = _ui_root() / "lib" / "api" / "types.ts"
    assert types_ts.is_file(), (
        f"unified-trading-system-ui lib/api/types.ts missing at {types_ts}"
    )

    required = ["PaginatedResponse", "data:", "pagination:", "has_next:", "as_of"]
    missing = _all_contain(types_ts, required)
    assert not missing, (
        f"lib/api/types.ts is MISSING PaginatedResponse contract elements:\n"
        f"  {missing}\n\n"
        "PaginatedResponse is the API-contract consumption type for all unified-trading-api"
        " list endpoints — removing any field silently drops list data from every list view."
    )


def test_unified_trading_system_ui_launch_client_stable() -> None:
    """lib/api/deployment-launch-client.ts defines LaunchResult + launch param interfaces.

    LaunchResult and MlExperimentParams/StrategyBacktestParams are the API-contract
    consumption types for deployment-api POST /api/deploy/*/launch. The launch panel
    constructs request bodies from these interfaces; if they drift from the deployment-api
    schema, launch requests silently fail or carry wrong payloads.
    """
    _skip_if_absent()

    launch_ts = _ui_root() / "lib" / "api" / "deployment-launch-client.ts"
    assert launch_ts.is_file(), (
        f"unified-trading-system-ui lib/api/deployment-launch-client.ts missing at {launch_ts}"
    )

    required = [
        "LaunchResult",
        "MlExperimentParams",
        "StrategyBacktestParams",
        "/api/deploy/",
    ]
    missing = _all_contain(launch_ts, required)
    assert not missing, (
        f"lib/api/deployment-launch-client.ts is MISSING API-contract elements:\n"
        f"  {missing}\n\n"
        "LaunchResult + MlExperimentParams + StrategyBacktestParams are the deployment-api"
        " launch contract — removing any breaks the launch panel request construction."
    )


def test_unified_trading_system_ui_promote_client_route_stable() -> None:
    """lib/api/promote-client.ts references /api/promote route served by unified-trading-api.

    POST /api/promote/{strategyId}/{manifestId} and .../demote are the promote/demote
    endpoints. The promote workflow (paper→live_early) calls these; if the route path
    drifts between the UI client and the unified-trading-api server, promotes silently
    fail with 404 instead of surfacing a TypeScript error.
    """
    _skip_if_absent()

    promote_ts = _ui_root() / "lib" / "api" / "promote-client.ts"
    assert promote_ts.is_file(), (
        f"unified-trading-system-ui lib/api/promote-client.ts missing at {promote_ts}"
    )

    required = ["/api/promote/", "/demote"]
    missing = _all_contain(promote_ts, required)
    assert not missing, (
        f"lib/api/promote-client.ts is MISSING promote route references:\n"
        f"  {missing}\n\n"
        "/api/promote/ and /demote are the unified-trading-api promote/demote endpoints —"
        " removing either reference silently breaks the promote workflow."
    )


def test_unified_trading_system_ui_safety_ops_proxy_present() -> None:
    """lib/api/safety-ops-proxy.ts is present.

    The safety-ops surface (kill-switch activation and audit sign-off) is consumed by
    the UI via safety-ops-proxy.ts, which proxies to alerting-service's /incidents and
    /signoffs endpoints. Removing this module drops the kill-switch and audit sign-off
    UI controls without any import errors at the component level.
    """
    _skip_if_absent()

    safety_ts = _ui_root() / "lib" / "api" / "safety-ops-proxy.ts"
    assert safety_ts.is_file(), (
        f"unified-trading-system-ui lib/api/safety-ops-proxy.ts missing at {safety_ts}.\n\n"
        "safety-ops-proxy.ts proxies to alerting-service /incidents + /signoffs — "
        "removing it drops the kill-switch and audit sign-off UI controls."
    )

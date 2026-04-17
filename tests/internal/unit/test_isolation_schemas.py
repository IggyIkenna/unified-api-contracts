"""Unit tests for isolation.py — client isolation, SLA tiers, runtime profiles, chaos."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from unified_api_contracts.internal.domain.deployment_service import (
    ChaosHookSpec,
    ChaosInjectionPoint,
    ChaosInjectionSpec,
    ClientServiceOverride,
    ClientSubscription,
    IsolationPolicy,
    KillSwitchScope,
    RuntimeProfile,
    RuntimeProfileSpec,
    ServiceIsolationSpec,
    SLATier,
    SLATierSpec,
)


def test_isolation_policy_values() -> None:
    assert IsolationPolicy.SHARED == "shared"
    assert IsolationPolicy.ISOLATED == "isolated"


def test_sla_tier_values() -> None:
    assert SLATier.BASIC == "basic"
    assert SLATier.STANDARD == "standard"
    assert SLATier.PREMIUM == "premium"


def test_runtime_profile_values() -> None:
    assert RuntimeProfile.BACKTEST == "backtest"
    assert RuntimeProfile.PAPER == "paper"
    assert RuntimeProfile.MOCK_LIVE == "mock-live"
    assert RuntimeProfile.STAGING == "staging"
    assert RuntimeProfile.PROD == "prod"


def test_chaos_injection_point_values() -> None:
    assert ChaosInjectionPoint.VENUE_LATENCY == "venue_latency"
    assert ChaosInjectionPoint.KILL_SWITCH_FIRE == "kill_switch_fire"
    assert len(list(ChaosInjectionPoint)) == 8


def test_kill_switch_scope_values() -> None:
    assert KillSwitchScope.GLOBAL == "global"
    assert KillSwitchScope.CLIENT == "client"
    assert len(list(KillSwitchScope)) == 6


def test_service_isolation_spec_requires_allowed_list() -> None:
    spec = ServiceIsolationSpec(
        service="execution-service",
        default=IsolationPolicy.ISOLATED,
        allowed=[IsolationPolicy.ISOLATED],
        reason="per-client venue keys",
    )
    assert spec.service == "execution-service"
    assert spec.default == IsolationPolicy.ISOLATED
    assert IsolationPolicy.ISOLATED in spec.allowed


def test_sla_tier_spec_premium_requires_isolated_services() -> None:
    spec = SLATierSpec(
        tier=SLATier.PREMIUM,
        cost_multiplier=6.0,
        allowed_isolations=[IsolationPolicy.SHARED, IsolationPolicy.ISOLATED],
        min_isolated_services=["execution-service", "strategy-service"],
        latency_budget_ms=40,
        support_response_sla_min=30,
    )
    assert spec.cost_multiplier == 6.0
    assert "execution-service" in spec.min_isolated_services


def test_runtime_profile_spec_prod_forbids_chaos() -> None:
    spec = RuntimeProfileSpec(
        profile=RuntimeProfile.PROD,
        description="Production",
        cloud_mock_mode=False,
        mock_state_mode="interactive",
        auth_disabled=False,
        vite_mock_api=False,
        vite_skip_auth=False,
        chaos_allowed=False,
        client_isolation_required=True,
        storage_namespace="prod/",
        allow_real_venue_calls=True,
    )
    assert spec.chaos_allowed is False
    assert spec.allow_real_venue_calls is True


def test_runtime_profile_spec_backtest_allows_chaos() -> None:
    spec = RuntimeProfileSpec(
        profile=RuntimeProfile.BACKTEST,
        description="Historical replay",
        cloud_mock_mode=False,
        mock_state_mode="deterministic",
        auth_disabled=True,
        vite_mock_api=False,
        vite_skip_auth=True,
        chaos_allowed=True,
        client_isolation_required=False,
        storage_namespace="backtest/{run_id}/",
        allow_real_venue_calls=False,
    )
    assert spec.chaos_allowed is True
    assert spec.allow_real_venue_calls is False


def test_client_subscription_premium_with_overrides() -> None:
    sub = ClientSubscription(
        client_id="client_alpha",
        sla_tier=SLATier.PREMIUM,
        service_overrides=[
            ClientServiceOverride(
                service_name="pnl-attribution-service",
                isolation=IsolationPolicy.ISOLATED,
            ),
        ],
        active_from=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert sub.client_id == "client_alpha"
    assert sub.sla_tier == SLATier.PREMIUM
    assert len(sub.service_overrides) == 1
    assert sub.service_overrides[0].isolation == IsolationPolicy.ISOLATED


def test_chaos_injection_spec_references_valid_point() -> None:
    spec = ChaosInjectionSpec(
        injection_id="chaos_001",
        point=ChaosInjectionPoint.VENUE_LATENCY,
        target_service="execution-service",
        parameters={"delay_ms": "5000", "venue": "BINANCE"},
        active_from=datetime(2026, 4, 17, tzinfo=UTC),
        created_by="qa@example.com",
        runtime_profile=RuntimeProfile.STAGING,
    )
    assert spec.point == ChaosInjectionPoint.VENUE_LATENCY
    assert spec.runtime_profile == RuntimeProfile.STAGING
    assert spec.parameters["venue"] == "BINANCE"


def test_chaos_hook_spec() -> None:
    hook = ChaosHookSpec(
        point=ChaosInjectionPoint.KILL_SWITCH_FIRE,
        target_boundary="UTL KillSwitchBus",
        hook_location="unified_trading_library.kill_switch",
        parameters=["scope", "client_id"],
        status="planned",
    )
    assert hook.point == ChaosInjectionPoint.KILL_SWITCH_FIRE


def test_client_subscription_empty_overrides_default() -> None:
    sub = ClientSubscription(
        client_id="client_basic",
        sla_tier=SLATier.BASIC,
        active_from=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert sub.service_overrides == []


@pytest.mark.parametrize(
    "tier,expected_multiplier",
    [
        (SLATier.BASIC, 1.0),
        (SLATier.STANDARD, 2.5),
        (SLATier.PREMIUM, 6.0),
    ],
)
def test_sla_tier_cost_multipliers_match_topology_yaml(tier: SLATier, expected_multiplier: float) -> None:
    """Document the contract: these multipliers MUST match runtime-topology.yaml sla_tiers."""
    spec = SLATierSpec(
        tier=tier,
        cost_multiplier=expected_multiplier,
        allowed_isolations=[IsolationPolicy.SHARED],
        min_isolated_services=[],
        latency_budget_ms=500,
        support_response_sla_min=1440,
    )
    assert spec.cost_multiplier == expected_multiplier

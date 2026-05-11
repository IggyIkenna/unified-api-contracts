"""CeFi scenario seeds — 2 :class:`ScenarioOverlay` instances.

Per Day-1 design fragments at
``unified-trading-pm/plans/active/scratch_scenarios_day1/01_cefi_venue_circuit_breaker_trip.md``
+ ``07_cefi_funding_spike_10x.md``.

Both target `ARBITRAGE_PRICE_DISPERSION` primarily; `carry_staked_basis` is
the hedge-leg secondary archetype.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from ...canonical.crosscutting.alerting.codes import AlertCode
from ...canonical.crosscutting.circuit_breaker import BreakerAction, CircuitBreakerId
from ...canonical.crosscutting.risk_rule import RiskRuleConsequence
from ...canonical.crosscutting.scenario_overlay import (
    OutcomeCategory,
    PriceShift,
    RejectFills,
    ScenarioApplicabilityFilter,
    ScenarioCategory,
    ScenarioOutcomeAssertion,
    ScenarioOverlay,
    ScenarioOverlayLayer,
    register_scenario,
)

# ---------------------------------------------------------------------------
# cefi_venue_circuit_breaker_trip — per-venue trading halt
# ---------------------------------------------------------------------------

CEFI_VENUE_CIRCUIT_BREAKER_TRIP = ScenarioOverlay(
    scenario_id="cefi_venue_circuit_breaker_trip",
    category=ScenarioCategory.VENUE_OUTAGE,
    layer=ScenarioOverlayLayer.ORDER,
    asset_groups=frozenset({"cefi"}),
    applies_to=ScenarioApplicabilityFilter(
        venues=frozenset({"bybit", "deribit", "binance", "okx", "hyperliquid", "aster"}),
        archetypes=frozenset({"ARBITRAGE_PRICE_DISPERSION", "carry_staked_basis"}),
    ),
    mutation_spec=RejectFills(
        reject_rate=Decimal("1.0"),
        duration_seconds=300,
        reject_reason="VenueHalted",
    ),
    expected_outcomes=(
        ScenarioOutcomeAssertion(
            archetype="ARBITRAGE_PRICE_DISPERSION",
            category=OutcomeCategory.RISK_BREAKER_TRIPPED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.VENUE_OUTAGE_SECONDS,
            breaker_action=BreakerAction.CANCEL_OPEN,
            alert_codes=frozenset({AlertCode.KILL_SWITCH_VENUE_DISCONNECT, AlertCode.CIRCUIT_BREAKER_OPEN}),
            expected_within_seconds=90,
        ),
        ScenarioOutcomeAssertion(
            archetype="ARBITRAGE_PRICE_DISPERSION",
            category=OutcomeCategory.RISK_BREAKER_TRIPPED,
            breaker_id=CircuitBreakerId.HEDGE_GAP_NOTIONAL_USD,
            breaker_action=BreakerAction.SCALE_DOWN,
            alert_codes=frozenset({AlertCode.CIRCUIT_BREAKER_OPEN}),
            expected_within_seconds=120,
        ),
    ),
    description=(
        "Per-venue trading halt across 6 CeFi perp venues; "
        "hedge-leg cancel + cross-venue inventory rebalance assertions."
    ),
    real_world_referent=(
        "Binance 2024-04 CPI halt; Bybit 2024-12 BTC perp pause; "
        "OKX 2025-02 WS-only outage; Hyperliquid 2024-10 BSC cascade."
    ),
)

# ---------------------------------------------------------------------------
# cefi_funding_spike_10x — perp funding-rate jump
# ---------------------------------------------------------------------------

CEFI_FUNDING_SPIKE_10X = ScenarioOverlay(
    scenario_id="cefi_funding_spike_10x",
    category=ScenarioCategory.PRICE_SHOCK,
    layer=ScenarioOverlayLayer.FEATURE,
    asset_groups=frozenset({"cefi"}),
    applies_to=ScenarioApplicabilityFilter(
        venues=frozenset({"bybit", "deribit", "binance", "okx", "hyperliquid", "aster"}),
        archetypes=frozenset({"ARBITRAGE_PRICE_DISPERSION", "carry_staked_basis"}),
        data_types=frozenset({"funding_rate"}),
    ),
    mutation_spec=PriceShift(
        target_value_bps=Decimal("100"),
        baseline_bps=Decimal("10"),
        duration_seconds=28800,
        recovery_curve="step",
    ),
    expected_outcomes=(
        ScenarioOutcomeAssertion(
            archetype="ARBITRAGE_PRICE_DISPERSION",
            category=OutcomeCategory.RISK_BREAKER_TRIPPED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.FUNDING_RATE_FLIP_BPS,
            breaker_action=BreakerAction.BLOCK_NEW,
            alert_codes=frozenset({AlertCode.RISK_RULE_BLOCKED, AlertCode.CIRCUIT_BREAKER_OPEN}),
            expected_within_seconds=60,
        ),
        ScenarioOutcomeAssertion(
            archetype="carry_staked_basis",
            category=OutcomeCategory.STRATEGY_SCALED_DOWN,
            consequence=RiskRuleConsequence.SCALE_DOWN,
            alert_codes=frozenset({AlertCode.RISK_RULE_SCALED_DOWN}),
            expected_within_seconds=60,
        ),
    ),
    description=(
        "Perp funding rate spikes 10x over one funding period (8h); "
        "inverts funding-arb basis profit + erodes carry hedge."
    ),
    real_world_referent=(
        "Bybit ETHUSDT 2024-04-12 (FTX aftermath); "
        "Hyperliquid 2025-01 memecoin storm; Binance BTCUSDT 2022-11-08 (FTX drain)."
    ),
)


SCENARIOS: Final[tuple[ScenarioOverlay, ...]] = (
    CEFI_VENUE_CIRCUIT_BREAKER_TRIP,
    CEFI_FUNDING_SPIKE_10X,
)

# Register all into the module-level SCENARIO_REGISTRY at import time.
for _scenario in SCENARIOS:
    register_scenario(_scenario)

"""CeFi scenario seeds — 3 :class:`ScenarioOverlay` instances.

Per Day-1 design fragments at
``unified-trading-pm/plans/active/scratch_scenarios_day1/01_cefi_venue_circuit_breaker_trip.md``
+ ``07_cefi_funding_spike_10x.md`` + ``13_execution_slippage_spike.md`` (CeFi
book-thinning sub-variant; the DEX-pool-drain sub-variant registers in
``defi.py`` as `defi_execution_slippage_spike_pool_drain`).

Target `ARBITRAGE_PRICE_DISPERSION` primarily; `carry_staked_basis` is
the hedge-leg secondary archetype.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from ...canonical.crosscutting.alerting.codes import AlertCode
from ...canonical.crosscutting.circuit_breaker import BreakerAction, CircuitBreakerId
from ...canonical.crosscutting.risk_rule import RiskRuleConsequence
from ...canonical.crosscutting.scenario_overlay import (
    BookSpoof,
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


# ---------------------------------------------------------------------------
# cefi_execution_slippage_spike_book_thinning — CeFi book-thinning execution slippage
# ---------------------------------------------------------------------------
# CeFi sub-variant of Day-1 fragment 13_execution_slippage_spike.md (the
# DEX-pool-drain sub-variant registers in defi.py). No dedicated
# `CEFI_BOOK_THIN`-style breaker exists yet — `SPREAD_BLOWOUT_BPS` ("Quoted
# bid-ask spread >= threshold bps, illiquidity / venue degradation") is an
# exact conceptual match and is the closest-fit substitution, per the same
# convention used for the DEX twin.

CEFI_EXECUTION_SLIPPAGE_SPIKE_BOOK_THINNING = ScenarioOverlay(
    scenario_id="cefi_execution_slippage_spike_book_thinning",
    category=ScenarioCategory.PRICE_SHOCK,
    layer=ScenarioOverlayLayer.ORDER,
    asset_groups=frozenset({"cefi"}),
    applies_to=ScenarioApplicabilityFilter(
        venues=frozenset({"bybit", "binance", "deribit", "okx", "hyperliquid", "aster"}),
        archetypes=frozenset({"ARBITRAGE_PRICE_DISPERSION", "carry_staked_basis"}),
    ),
    mutation_spec=BookSpoof(
        book_depth_scale=Decimal("0.2"),
        duration_seconds=60,
        imbalance_target=Decimal("-0.5"),
    ),
    expected_outcomes=(
        ScenarioOutcomeAssertion(
            archetype="ARBITRAGE_PRICE_DISPERSION",
            category=OutcomeCategory.RISK_BREAKER_TRIPPED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.SPREAD_BLOWOUT_BPS,
            breaker_action=BreakerAction.CANCEL_OPEN,
            alert_codes=frozenset({AlertCode.CIRCUIT_BREAKER_OPEN, AlertCode.RISK_RULE_BLOCKED}),
            expected_within_seconds=5,
        ),
        ScenarioOutcomeAssertion(
            archetype="carry_staked_basis",
            category=OutcomeCategory.RISK_BREAKER_TRIPPED,
            breaker_id=CircuitBreakerId.SPREAD_BLOWOUT_BPS,
            breaker_action=BreakerAction.SCALE_DOWN,
            consequence=RiskRuleConsequence.SCALE_DOWN,
            alert_codes=frozenset({AlertCode.RISK_RULE_SCALED_DOWN}),
            expected_within_seconds=60,
        ),
    ),
    description=(
        "Top-of-book spread widens 20x baseline and top-5 depth collapses 80% for 60s across "
        "6 CeFi perp venues; market-order fills walk the thinned book on the way to a fill."
    ),
    real_world_referent=(
        "Binance BTCUSDT-perp 2024-04 CPI-print book thinning (spread 0.3bps->35bps, ~28bps realised slippage); "
        "Bybit ETHUSDT-perp 2024-12 halt-recovery (50-120bps in the first ~90s post-resume)."
    ),
    composes_with=frozenset({"cefi_venue_circuit_breaker_trip", "cross_asset_flash_crash"}),
)


SCENARIOS: Final[tuple[ScenarioOverlay, ...]] = (
    CEFI_VENUE_CIRCUIT_BREAKER_TRIP,
    CEFI_FUNDING_SPIKE_10X,
    CEFI_EXECUTION_SLIPPAGE_SPIKE_BOOK_THINNING,
)

# Register all into the module-level SCENARIO_REGISTRY at import time.
for _scenario in SCENARIOS:
    register_scenario(_scenario)

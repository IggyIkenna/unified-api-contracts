"""Cross-asset scenario seeds — 3 :class:`ScenarioOverlay` instances.

Per Day-1 design fragments at
``unified-trading-pm/plans/active/scratch_scenarios_day1/08_cross_asset_flash_crash.md``
+ ``09_cross_asset_basis_blowout.md`` + ``13_execution_slippage_spike.md``.

The first two target BOTH cutover archetypes (`carry_staked_basis` +
`ARBITRAGE_PRICE_DISPERSION`) — cross-asset events affect every position.
Asset groups span `cefi` + `defi` (primary correlated event; DeFi spot legs
lag by 30-180s on Ethereum mainnet per block time).

FOLLOW-UP gap (execution_slippage_spike, per the closest-fit-existing-enum
substitution pattern established in ``defi.py``'s own header): the source
design fragment's `EXECUTION_QUALITY`/`LIQUIDITY_DRAIN`/`BOOK_THINNING`
categories, `EXECUTION_SLIPPAGE_EXCEEDED`/`CEFI_BOOK_THIN` alert codes, and
per-archetype `max_slippage_bps` thresholds don't exist yet in UAC — mapped
to the closest existing `ScenarioCategory`/`AlertCode`/`CircuitBreakerId`
below (`VENUE_OUTAGE` per the same substitution `DEFI_LIQUIDITY_DRAIN_LENDING_POOL`
already uses for a liquidity-drain shape; `SPREAD_BLOWOUT_BPS` — "quoted
bid-ask spread >= threshold bps (illiquidity/venue degradation)" — is an
exact fit for both the DEX pool-drain and CeFi book-thinning variants).
`Drift`/`Hyperliquid-spot` DEX protocols named in the source fragment aren't
registered `_ADAPTERS` keys anywhere in this workspace (confirmed via
`market-tick-data-service`'s `VENUE_REGISTRY`/`PLANNED_VENUES`) — omitted
from `protocols` rather than invented; only the 3 confirmed-registered DEX
protocols (Uniswap V3 / Curve / Balancer) are declared.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from ...canonical.crosscutting.alerting.codes import AlertCode
from ...canonical.crosscutting.circuit_breaker import BreakerAction, CircuitBreakerId
from ...canonical.crosscutting.kill_switch import KillSwitchId
from ...canonical.crosscutting.risk_rule import RiskRuleConsequence
from ...canonical.crosscutting.scenario_overlay import (
    BookSpoof,
    OutcomeCategory,
    PriceShift,
    ScenarioApplicabilityFilter,
    ScenarioCategory,
    ScenarioOutcomeAssertion,
    ScenarioOverlay,
    ScenarioOverlayLayer,
    register_scenario,
)

# ---------------------------------------------------------------------------
# cross_asset_flash_crash — multi-venue cascade
# ---------------------------------------------------------------------------

CROSS_ASSET_FLASH_CRASH = ScenarioOverlay(
    scenario_id="cross_asset_flash_crash",
    category=ScenarioCategory.CROSS_ASSET,
    layer=ScenarioOverlayLayer.RAW_TICK,
    asset_groups=frozenset({"cefi", "defi"}),
    applies_to=ScenarioApplicabilityFilter(
        instruments=frozenset({"BTC-PERP", "ETH-PERP", "SOL-PERP"}),
        venues=frozenset({"bybit", "deribit", "binance", "okx", "hyperliquid", "aster"}),
        archetypes=frozenset({"carry_staked_basis", "ARBITRAGE_PRICE_DISPERSION"}),
    ),
    mutation_spec=BookSpoof(
        book_depth_scale=Decimal("0.3"),
        duration_seconds=180,
        imbalance_target=Decimal("-0.8"),
    ),
    expected_outcomes=(
        ScenarioOutcomeAssertion(
            archetype="ARBITRAGE_PRICE_DISPERSION",
            category=OutcomeCategory.KILL_SWITCH_ARMED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.DRAWDOWN_DAILY_BPS,
            breaker_action=BreakerAction.KILL_ALL,
            kill_switch_id=KillSwitchId.KILL_PER_ARCHETYPE_ARBITRAGE_PRICE_DISPERSION,
            alert_codes=frozenset(
                {
                    AlertCode.CIRCUIT_BREAKER_OPEN,
                    AlertCode.RISK_RULE_BLOCKED,
                    AlertCode.KILL_SWITCH_PORTFOLIO_DRAWDOWN,
                },
            ),
            expected_within_seconds=30,
        ),
        ScenarioOutcomeAssertion(
            archetype="carry_staked_basis",
            category=OutcomeCategory.KILL_SWITCH_ARMED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.DRAWDOWN_DAILY_BPS,
            breaker_action=BreakerAction.KILL_ALL,
            kill_switch_id=KillSwitchId.KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS,
            alert_codes=frozenset(
                {
                    AlertCode.CIRCUIT_BREAKER_OPEN,
                    AlertCode.KILL_SWITCH_PORTFOLIO_DRAWDOWN,
                },
            ),
            expected_within_seconds=30,
        ),
    ),
    description=(
        "Flash crash -1500bps across BTC/ETH/SOL perps in 3min; "
        "liquidation cascade; book-depth drops to 30%; DeFi spot lags 30-180s."
    ),
    real_world_referent=(
        "2020-03-12 BTC -50% in 2h; 2022-11-08 FTX disclosure; "
        "2024-08-05 JPY carry unwind; 2024-12-19 ETH whale liquidation."
    ),
)

# ---------------------------------------------------------------------------
# cross_asset_basis_blowout_perp_spot — perp-spot basis explosion
# ---------------------------------------------------------------------------

CROSS_ASSET_BASIS_BLOWOUT_PERP_SPOT = ScenarioOverlay(
    scenario_id="cross_asset_basis_blowout_perp_spot",
    category=ScenarioCategory.PRICE_SHOCK,
    layer=ScenarioOverlayLayer.FEATURE,
    asset_groups=frozenset({"cefi", "defi"}),
    applies_to=ScenarioApplicabilityFilter(
        instruments=frozenset({"BTC", "ETH", "SOL"}),
        venues=frozenset({"bybit", "deribit", "binance", "okx", "hyperliquid", "aster"}),
        archetypes=frozenset({"ARBITRAGE_PRICE_DISPERSION", "carry_staked_basis"}),
        data_types=frozenset({"basis_curve", "mid_price"}),
    ),
    mutation_spec=PriceShift(
        target_value_bps=Decimal("500"),
        baseline_bps=Decimal("20"),
        duration_seconds=7200,
        recovery_curve="linear",
    ),
    expected_outcomes=(
        ScenarioOutcomeAssertion(
            archetype="ARBITRAGE_PRICE_DISPERSION",
            category=OutcomeCategory.STRATEGY_SCALED_DOWN,
            consequence=RiskRuleConsequence.SCALE_DOWN,
            breaker_id=CircuitBreakerId.BASIS_INVERSION_BPS,
            breaker_action=BreakerAction.SCALE_DOWN,
            alert_codes=frozenset({AlertCode.RISK_RULE_SCALED_DOWN}),
            expected_within_seconds=30,
        ),
        ScenarioOutcomeAssertion(
            archetype="ARBITRAGE_PRICE_DISPERSION",
            category=OutcomeCategory.KILL_SWITCH_ARMED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.DRAWDOWN_DAILY_BPS,
            breaker_action=BreakerAction.KILL_ALL,
            kill_switch_id=KillSwitchId.KILL_PER_ARCHETYPE_ARBITRAGE_PRICE_DISPERSION,
            alert_codes=frozenset({AlertCode.RISK_RULE_BLOCKED, AlertCode.KILL_SWITCH_PORTFOLIO_DRAWDOWN}),
            expected_within_seconds=60,
        ),
        ScenarioOutcomeAssertion(
            archetype="carry_staked_basis",
            category=OutcomeCategory.KILL_SWITCH_ARMED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.DRAWDOWN_DAILY_BPS,
            breaker_action=BreakerAction.KILL_ALL,
            kill_switch_id=KillSwitchId.KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS,
            alert_codes=frozenset({AlertCode.CIRCUIT_BREAKER_OPEN}),
            expected_within_seconds=60,
        ),
    ),
    description="Perp trades 500bps above/below spot for 2h; entry sized then adverse widening blows up MTM.",
    real_world_referent=(
        "Bitfinex 2021-01-04 BTC +8%; stETH-ETH 2022-06-15 -7%; "
        "ETH staking 2024-03 pre-Shanghai; Hyperliquid 2025-02 memecoin."
    ),
)


# ---------------------------------------------------------------------------
# execution_slippage_spike — DEX pool-drain / CeFi book-thinning fill slippage
# ---------------------------------------------------------------------------

EXECUTION_SLIPPAGE_SPIKE = ScenarioOverlay(
    scenario_id="execution_slippage_spike",
    category=ScenarioCategory.VENUE_OUTAGE,
    layer=ScenarioOverlayLayer.ORDER,
    asset_groups=frozenset({"cefi", "defi"}),
    applies_to=ScenarioApplicabilityFilter(
        chains=frozenset({"ethereum", "arbitrum"}),
        protocols=frozenset({"uniswap_v3", "curve", "balancer"}),
        venues=frozenset({"bybit", "binance", "deribit", "okx", "hyperliquid", "aster"}),
        archetypes=frozenset({"carry_staked_basis", "ARBITRAGE_PRICE_DISPERSION", "LEVERAGED_FUNDING_ARB"}),
    ),
    mutation_spec=BookSpoof(
        book_depth_scale=Decimal("0.25"),
        duration_seconds=300,
        imbalance_target=Decimal("0"),
    ),
    expected_outcomes=(
        ScenarioOutcomeAssertion(
            archetype="carry_staked_basis",
            category=OutcomeCategory.RISK_BREAKER_TRIPPED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.SPREAD_BLOWOUT_BPS,
            breaker_action=BreakerAction.BLOCK_NEW,
            alert_codes=frozenset({AlertCode.CIRCUIT_BREAKER_OPEN, AlertCode.RISK_RULE_BLOCKED}),
            expected_within_seconds=5,
        ),
        ScenarioOutcomeAssertion(
            archetype="ARBITRAGE_PRICE_DISPERSION",
            category=OutcomeCategory.STRATEGY_SCALED_DOWN,
            consequence=RiskRuleConsequence.SCALE_DOWN,
            breaker_id=CircuitBreakerId.SPREAD_BLOWOUT_BPS,
            breaker_action=BreakerAction.SCALE_DOWN,
            alert_codes=frozenset({AlertCode.RISK_RULE_SCALED_DOWN}),
            expected_within_seconds=5,
        ),
        ScenarioOutcomeAssertion(
            archetype="LEVERAGED_FUNDING_ARB",
            category=OutcomeCategory.ORDER_REJECTED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.SPREAD_BLOWOUT_BPS,
            breaker_action=BreakerAction.BLOCK_NEW,
            alert_codes=frozenset({AlertCode.RISK_RULE_BLOCKED}),
            expected_within_seconds=5,
        ),
    ),
    description=(
        "Order fill price diverges from intended mid — DEX pool-drain (75% same-side "
        "liquidity withdrawn) or CeFi book-thinning (spread blowout + top-N depth collapse); "
        "auto-response pauses new entries per (venue, instrument) within 5s."
    ),
    real_world_referent=(
        "Uniswap V3 wstETH/ETH 2024-09 reorg-tail (240bps vs ~8bps expected); "
        "Curve crvUSD/USDC depeg-tail 2024-08 (80-300bps tail swaps); "
        "Binance BTCUSDT-perp 2024-04 CPI-print book thinning (~28bps on 200 BTC hedge flow); "
        "Bybit 2024-12 ETHUSDT-perp halt-recovery (50-120bps first ~90s)."
    ),
    composes_with=frozenset({"defi_liquidity_drain_lending_pool", "defi_oracle_deviation_30sigma"}),
)


SCENARIOS: Final[tuple[ScenarioOverlay, ...]] = (
    CROSS_ASSET_FLASH_CRASH,
    CROSS_ASSET_BASIS_BLOWOUT_PERP_SPOT,
    EXECUTION_SLIPPAGE_SPIKE,
)

for _scenario in SCENARIOS:
    register_scenario(_scenario)

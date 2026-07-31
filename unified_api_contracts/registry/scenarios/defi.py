"""DeFi scenario seeds — 8 :class:`ScenarioOverlay` instances.

Per Day-1 design fragments at
``unified-trading-pm/plans/active/scratch_scenarios_day1/02..06+10*.md``
+ ``16_lst_unstake_queue_blowup.md``.

Primary archetype target: `carry_staked_basis` (Solana LST yield + deleverage
path); `ARBITRAGE_PRICE_DISPERSION` is secondary for any DeFi-leg variants.

FOLLOW-UP gaps carried from Day-1 fragments — closest-fit existing
`CircuitBreakerId` substituted where a per-scenario dedicated breaker
doesn't yet exist (e.g. `LENDING_POOL_UNAVAILABLE_SECONDS` ↦
`LIQUIDATION_CASCADE_RISK`; `ORACLE_STALENESS_SECONDS` ↦
`ORACLE_DEVIATION_BPS`). DR plan Phase 1.A/Phase 4 owns the breaker
extensions per the cross-side ping at PM@3daea56a.

`lst_unstake_queue_blowup` gap: the fragment's own PRIMARY mechanism is a
per-LST `unstake_days_remaining` feature (needs a UAC
`LST_WITHDRAWAL_THROUGHPUT_BASELINES` registry the fragment itself marks
`DEFERRED-TO-PHASE-2-IMPL`) — modeled here via `LatencyInject` (added
redemption delay), the same mutation type `defi_mempool_congestion_
inclusion_delay` already uses for an analogous "added delay to a
settlement/redemption pipeline" mechanism. `LENDING_POOL_UNAVAILABLE_SECONDS`
substitutes for the fragment's undefined queue-lockup breaker (same
"prevented from acting on this position" shape as its existing Aave/Morpho
use). Only the 12 LST/LRT tokens confirmed in UAC's real
`LST_TOKEN_TO_PROTOCOL_ASSET` registry are declared — the fragment's
frxETH/sfrxETH (Frax), Sanctum LSTs, and LBTC (Lombard) aren't onboarded
there yet, so they're omitted rather than invented.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from ...canonical.crosscutting.alerting.codes import AlertCode
from ...canonical.crosscutting.circuit_breaker import BreakerAction, CircuitBreakerId
from ...canonical.crosscutting.kill_switch import KillSwitchId
from ...canonical.crosscutting.risk_rule import RiskRuleConsequence
from ...canonical.crosscutting.scenario_overlay import (
    GasSurge,
    LatencyInject,
    ManifestPhantom,
    OracleDeviate,
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
# defi_chain_rpc_outage_solana — chain-level RPC outage
# ---------------------------------------------------------------------------

DEFI_CHAIN_RPC_OUTAGE_SOLANA = ScenarioOverlay(
    scenario_id="defi_chain_rpc_outage_solana",
    category=ScenarioCategory.VENUE_OUTAGE,
    layer=ScenarioOverlayLayer.RAW_TICK,
    asset_groups=frozenset({"defi"}),
    applies_to=ScenarioApplicabilityFilter(
        chains=frozenset({"solana"}),
        archetypes=frozenset({"carry_staked_basis", "ARBITRAGE_PRICE_DISPERSION"}),
        protocols=frozenset({"marinade", "jito", "sanctum"}),
    ),
    mutation_spec=LatencyInject(
        added_latency_seconds=Decimal("9999"),
        duration_seconds=1800,
        recovery_curve="exponential_decay",
    ),
    expected_outcomes=(
        ScenarioOutcomeAssertion(
            archetype="carry_staked_basis",
            category=OutcomeCategory.RISK_BREAKER_TRIPPED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.RPC_OUTAGE_SECONDS,
            breaker_action=BreakerAction.BLOCK_NEW,
            kill_switch_id=KillSwitchId.KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS,
            alert_codes=frozenset({AlertCode.TICK_STALENESS, AlertCode.CIRCUIT_BREAKER_OPEN}),
            expected_within_seconds=60,
        ),
    ),
    description="Solana chain RPC outage — all endpoints 503; slot height freezes; Pyth Solana feeds stale.",
    real_world_referent="Solana 2022-09-30 (4h); Solana 2024-02-06 (5h); pre-validator-client-v2 cascading failures.",
)

# ---------------------------------------------------------------------------
# defi_liquidity_drain_lending_pool — Aave/Morpho utilization spike → borrow cap
# ---------------------------------------------------------------------------

DEFI_LIQUIDITY_DRAIN_LENDING_POOL = ScenarioOverlay(
    scenario_id="defi_liquidity_drain_lending_pool",
    category=ScenarioCategory.VENUE_OUTAGE,
    layer=ScenarioOverlayLayer.FEATURE,
    asset_groups=frozenset({"defi"}),
    applies_to=ScenarioApplicabilityFilter(
        chains=frozenset({"ethereum", "arbitrum"}),
        protocols=frozenset({"aave_v3", "morpho"}),
        archetypes=frozenset({"carry_staked_basis"}),
        instruments=frozenset({"USDC", "USDT"}),
    ),
    mutation_spec=ManifestPhantom(
        target_capture_status="captured",
        target_value=Decimal("0.99"),
    ),
    expected_outcomes=(
        ScenarioOutcomeAssertion(
            archetype="carry_staked_basis",
            category=OutcomeCategory.ORDER_REJECTED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.LIQUIDATION_CASCADE_RISK,
            breaker_action=BreakerAction.BLOCK_NEW,
            alert_codes=frozenset({AlertCode.CIRCUIT_BREAKER_OPEN}),
            expected_within_seconds=90,
        ),
        ScenarioOutcomeAssertion(
            archetype="carry_staked_basis",
            category=OutcomeCategory.STRATEGY_SCALED_DOWN,
            consequence=RiskRuleConsequence.SCALE_DOWN,
            kill_switch_id=KillSwitchId.KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS,
            expected_within_seconds=120,
        ),
    ),
    description=("Aave/Morpho utilization spikes to 99% on (pool, asset); borrow tx rejected with BorrowCapExceeded."),
    real_world_referent=(
        "Aave 2023-11 BUSD utilization to CRV cascade; Morpho 2024-03 governance pause; Aave V3 2024-Q4 ETH borrow cap."
    ),
    composes_with=frozenset({"defi_oracle_deviation_30sigma", "defi_stablecoin_depeg"}),
)

# ---------------------------------------------------------------------------
# defi_oracle_deviation_30sigma — wild-print + stale-hold variants
# ---------------------------------------------------------------------------

DEFI_ORACLE_DEVIATION_30SIGMA = ScenarioOverlay(
    scenario_id="defi_oracle_deviation_30sigma",
    category=ScenarioCategory.STALENESS,
    layer=ScenarioOverlayLayer.RAW_TICK,
    asset_groups=frozenset({"defi"}),
    applies_to=ScenarioApplicabilityFilter(
        chains=frozenset({"solana", "ethereum", "arbitrum"}),
        archetypes=frozenset({"carry_staked_basis", "ARBITRAGE_PRICE_DISPERSION"}),
    ),
    mutation_spec=OracleDeviate(
        deviation_sigma=Decimal("30"),
        deviation_duration_heartbeats=1,
        oracle_id="pyth_solana_usdc",
    ),
    expected_outcomes=(
        ScenarioOutcomeAssertion(
            archetype="carry_staked_basis",
            category=OutcomeCategory.RISK_BREAKER_TRIPPED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.ORACLE_DEVIATION_BPS,
            breaker_action=BreakerAction.CANCEL_OPEN,
            alert_codes=frozenset({AlertCode.CIRCUIT_BREAKER_OPEN, AlertCode.TICK_STALENESS}),
            expected_within_seconds=30,
        ),
        ScenarioOutcomeAssertion(
            archetype="ARBITRAGE_PRICE_DISPERSION",
            category=OutcomeCategory.RISK_BREAKER_TRIPPED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.ORACLE_DEVIATION_BPS,
            breaker_action=BreakerAction.CANCEL_OPEN,
            expected_within_seconds=30,
        ),
    ),
    description=(
        "Oracle wild-print (30 sigma deviation); wild_print + stale_hold "
        "variants test peg-deviation + staleness breakers."
    ),
    real_world_referent="Chainlink LUNA 2022-05 zero-print; GMX-V1 AVAX 2022-09; Pyth 2024-Q1 heartbeat lag.",
)

# ---------------------------------------------------------------------------
# defi_gas_surge_50x — Ethereum gas price spike
# ---------------------------------------------------------------------------

DEFI_GAS_SURGE_50X = ScenarioOverlay(
    scenario_id="defi_gas_surge_50x",
    category=ScenarioCategory.PRICE_SHOCK,
    layer=ScenarioOverlayLayer.FEATURE,
    asset_groups=frozenset({"defi"}),
    applies_to=ScenarioApplicabilityFilter(
        chains=frozenset({"ethereum", "arbitrum", "optimism", "base"}),
        archetypes=frozenset({"carry_staked_basis", "ARBITRAGE_PRICE_DISPERSION"}),
    ),
    mutation_spec=GasSurge(
        surge_multiplier=Decimal("50"),
        baseline_gwei=Decimal("30"),
        surge_duration_seconds=600,
        recovery_curve="linear",
    ),
    expected_outcomes=(
        ScenarioOutcomeAssertion(
            archetype="carry_staked_basis",
            category=OutcomeCategory.RISK_BREAKER_TRIPPED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.GAS_PRICE_SURGE_GWEI,
            breaker_action=BreakerAction.BLOCK_NEW,
            alert_codes=frozenset({AlertCode.CIRCUIT_BREAKER_OPEN, AlertCode.RISK_RULE_BLOCKED}),
            expected_within_seconds=10,
        ),
        ScenarioOutcomeAssertion(
            archetype="ARBITRAGE_PRICE_DISPERSION",
            category=OutcomeCategory.STRATEGY_SCALED_DOWN,
            consequence=RiskRuleConsequence.SCALE_DOWN,
            alert_codes=frozenset({AlertCode.RISK_RULE_SCALED_DOWN}),
            expected_within_seconds=10,
        ),
    ),
    description=(
        "Ethereum mainnet gas spikes to 1500 gwei (50x baseline); "
        "rebalance economics inverted; gas-budget rule fires BLOCK."
    ),
    real_world_referent="Ethereum 2021-05 NFT mint wars; 2022-Q4 LUNA collapse; 2024-Q1 memecoin priority-fee storms.",
)

# ---------------------------------------------------------------------------
# defi_mempool_congestion_inclusion_delay — tx-inclusion latency + MEV sandwich
# ---------------------------------------------------------------------------

DEFI_MEMPOOL_CONGESTION_INCLUSION_DELAY = ScenarioOverlay(
    scenario_id="defi_mempool_congestion_inclusion_delay",
    category=ScenarioCategory.OPERATIONAL,
    layer=ScenarioOverlayLayer.ORDER,
    asset_groups=frozenset({"defi"}),
    applies_to=ScenarioApplicabilityFilter(
        chains=frozenset({"ethereum", "arbitrum", "optimism", "base"}),
        archetypes=frozenset({"carry_staked_basis", "ARBITRAGE_PRICE_DISPERSION"}),
    ),
    mutation_spec=LatencyInject(
        added_latency_seconds=Decimal("180"),
        duration_seconds=600,
        recovery_curve="linear",
    ),
    expected_outcomes=(
        ScenarioOutcomeAssertion(
            archetype="ARBITRAGE_PRICE_DISPERSION",
            category=OutcomeCategory.RISK_BREAKER_TRIPPED,
            breaker_id=CircuitBreakerId.FILL_LATENCY_BREACH_MS,
            breaker_action=BreakerAction.SCALE_DOWN,
            consequence=RiskRuleConsequence.SCALE_DOWN,
            alert_codes=frozenset({AlertCode.RISK_RULE_SCALED_DOWN}),
            expected_within_seconds=60,
        ),
    ),
    description="Mempool congestion to inclusion latency spike to MEV sandwich risk + cancel-tx race.",
    real_world_referent=(
        "Ethereum 2023-Q4 sandwich-bot domination; Arbitrum 2024-Q1 sequencer outage with mempool backlog."
    ),
    composes_with=frozenset({"defi_gas_surge_50x"}),
)

# ---------------------------------------------------------------------------
# defi_stablecoin_depeg — USDC/USDT/DAI/USDE de-peg
# ---------------------------------------------------------------------------

DEFI_STABLECOIN_DEPEG = ScenarioOverlay(
    scenario_id="defi_stablecoin_depeg",
    category=ScenarioCategory.PRICE_SHOCK,
    layer=ScenarioOverlayLayer.RAW_TICK,
    asset_groups=frozenset({"defi"}),
    applies_to=ScenarioApplicabilityFilter(
        instruments=frozenset({"USDC", "USDT", "DAI", "USDE"}),
        chains=frozenset({"ethereum", "arbitrum", "optimism", "base", "solana"}),
        archetypes=frozenset({"carry_staked_basis", "ARBITRAGE_PRICE_DISPERSION"}),
    ),
    mutation_spec=PriceShift(
        target_value_bps=Decimal("-1300"),
        baseline_bps=Decimal("0"),
        duration_seconds=86400,
        recovery_curve="exponential_decay",
    ),
    expected_outcomes=(
        ScenarioOutcomeAssertion(
            archetype="carry_staked_basis",
            category=OutcomeCategory.KILL_SWITCH_ARMED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.DRAWDOWN_DAILY_BPS,
            breaker_action=BreakerAction.KILL_ALL,
            kill_switch_id=KillSwitchId.KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS,
            alert_codes=frozenset({AlertCode.CIRCUIT_BREAKER_OPEN, AlertCode.KILL_SWITCH_PORTFOLIO_DRAWDOWN}),
            expected_within_seconds=60,
        ),
    ),
    description=(
        "Stablecoin de-peg ($0.87 catastrophic tier); LST yield numeraire "
        "unstable; deleverage USDC borrow leg structurally unfavorable."
    ),
    real_world_referent=(
        "USDC 2023-03-11 ($0.87 SVB); UST 2022-05-09 ($0.00 death spiral); PYUSD 2024-07; USDE 2024-Q4 Ethena unwind."
    ),
    composes_with=frozenset({"defi_liquidity_drain_lending_pool", "defi_oracle_deviation_30sigma"}),
)


# ---------------------------------------------------------------------------
# defi_lst_depeg_steth_5pct — LST/ETH peg break (5% below par)
# ---------------------------------------------------------------------------

DEFI_LST_DEPEG_STETH_5PCT = ScenarioOverlay(
    scenario_id="defi_lst_depeg_steth_5pct",
    category=ScenarioCategory.PRICE_SHOCK,
    layer=ScenarioOverlayLayer.RAW_TICK,
    asset_groups=frozenset({"defi"}),
    applies_to=ScenarioApplicabilityFilter(
        instruments=frozenset({"stETH", "wstETH", "rETH", "cbETH", "JitoSOL", "mSOL"}),
        chains=frozenset({"ethereum", "solana"}),
        archetypes=frozenset({"carry_staked_basis"}),
    ),
    mutation_spec=PriceShift(
        target_value_bps=Decimal("-500"),
        baseline_bps=Decimal("0"),
        duration_seconds=3600,
        recovery_curve="exponential_decay",
    ),
    expected_outcomes=(
        ScenarioOutcomeAssertion(
            archetype="carry_staked_basis",
            category=OutcomeCategory.RISK_BREAKER_TRIPPED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.LST_DEPEG_MODERATE,
            breaker_action=BreakerAction.CANCEL_OPEN,
            alert_codes=frozenset({AlertCode.CIRCUIT_BREAKER_OPEN}),
            expected_within_seconds=30,
        ),
    ),
    description=(
        "LST/ETH peg break: stETH/wstETH (and rETH/cbETH/JitoSOL/mSOL by parametrisation) "
        "priced 5% below ETH par. LST_DEPEG_MODERATE breaker (>=500bps) fires CANCEL_OPEN "
        "within 30s (D.2 ladder calibration). Prior to the LST depeg ladder, this scenario "
        "routed via the generic DRAWDOWN_DAILY_BPS breaker."
    ),
    real_world_referent=(
        "stETH 2022-06 Celsius/3AC redemption freeze ($0.9377 min vs ETH); "
        "rETH 2024-04 Pendle rebalancing; JitoSOL/mSOL Solana validator slashing events."
    ),
    composes_with=frozenset({"defi_oracle_deviation_30sigma", "defi_liquidity_drain_lending_pool"}),
)


# ---------------------------------------------------------------------------
# defi_lst_unstake_queue_blowup — LST/LRT withdrawal queue duration spike
# ---------------------------------------------------------------------------

DEFI_LST_UNSTAKE_QUEUE_BLOWUP = ScenarioOverlay(
    scenario_id="defi_lst_unstake_queue_blowup",
    category=ScenarioCategory.VENUE_OUTAGE,
    layer=ScenarioOverlayLayer.RAW_TICK,
    asset_groups=frozenset({"defi"}),
    applies_to=ScenarioApplicabilityFilter(
        chains=frozenset({"ethereum", "solana"}),
        instruments=frozenset(
            {
                "stETH",
                "wstETH",
                "weETH",
                "rETH",
                "ezETH",
                "rsETH",
                "mETH",
                "ETHx",
                "cbETH",
                "osETH",
                "jitoSOL",
                "mSOL",
            }
        ),
        archetypes=frozenset({"carry_staked_basis", "LEVERAGED_FUNDING_ARB"}),
    ),
    mutation_spec=LatencyInject(
        added_latency_seconds=Decimal("2592000"),  # 30 days — hits the fragment's CRITICAL threshold
        duration_seconds=86400,
        recovery_curve="linear",
    ),
    expected_outcomes=(
        ScenarioOutcomeAssertion(
            archetype="carry_staked_basis",
            category=OutcomeCategory.RISK_BREAKER_TRIPPED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.LENDING_POOL_UNAVAILABLE_SECONDS,
            breaker_action=BreakerAction.BLOCK_NEW,
            alert_codes=frozenset({AlertCode.CIRCUIT_BREAKER_OPEN}),
            expected_within_seconds=90,
        ),
        ScenarioOutcomeAssertion(
            archetype="LEVERAGED_FUNDING_ARB",
            category=OutcomeCategory.ORDER_REJECTED,
            consequence=RiskRuleConsequence.BLOCK,
            breaker_id=CircuitBreakerId.LENDING_POOL_UNAVAILABLE_SECONDS,
            breaker_action=BreakerAction.BLOCK_NEW,
            alert_codes=frozenset({AlertCode.RISK_RULE_BLOCKED}),
            expected_within_seconds=90,
        ),
    ),
    description=(
        "LST/LRT redemption window grows from days to weeks/months (Ethereum exit queue / "
        "EigenLayer redelegation delay / Lido buffer drained); the staked leg becomes "
        "involuntarily illiquid — new entries on this LST are blocked until the queue clears."
    ),
    real_world_referent=(
        "Ethereum withdrawal queue 2024-07 mass-exit (~17d peak vs ~6d steady-state); "
        "EigenLayer 2024-10 delegated-withdrawal delay raised 7d->14d; "
        "Renzo ezETH 2024-04 no-native-redemption depeg; Solana jitoSOL/mSOL queue "
        "stretch during 2024-Q1 MEV-bundle high-priority-fee windows."
    ),
    composes_with=frozenset(
        {"defi_liquidity_drain_lending_pool", "defi_lst_depeg_steth_5pct", "defi_stablecoin_depeg"}
    ),
)


SCENARIOS: Final[tuple[ScenarioOverlay, ...]] = (
    DEFI_CHAIN_RPC_OUTAGE_SOLANA,
    DEFI_LIQUIDITY_DRAIN_LENDING_POOL,
    DEFI_ORACLE_DEVIATION_30SIGMA,
    DEFI_GAS_SURGE_50X,
    DEFI_MEMPOOL_CONGESTION_INCLUSION_DELAY,
    DEFI_STABLECOIN_DEPEG,
    DEFI_LST_DEPEG_STETH_5PCT,
    DEFI_LST_UNSTAKE_QUEUE_BLOWUP,
)

for _scenario in SCENARIOS:
    register_scenario(_scenario)

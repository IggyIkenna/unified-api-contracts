"""Threshold registry — per-rule numeric values with unambiguous units.

Resolves the AAVE-bps ambiguity flagged in the 2026-05-07 audit:
``defi_aave_utilization_spike`` was previously documented as "9500" with no
unit. Here every threshold carries an explicit :class:`ThresholdUnit` so
``9500`` next to ``BPS_OF_ONE`` reads unambiguously as ``95.00 %`` of pool
utilization, not "9500 bps spread" or "9500 absolute units".

Per-archetype overrides allow the same rule to fire at different thresholds
for different strategies (e.g. ``leveraged_funding_arb`` may want a tighter
``defi_aave_utilization_spike_bps`` than ``carry_staked_basis``). The
registry default holds for unknown / new archetypes.

Phase 7 quietness baseline ran 2026-05-20 to 2026-05-22 (VM
``alerting-quietness-20260520-111232``, 48h, asia-northeast1-c staging).
Core DeFi thresholds confirmed — no tuning required. Each confirmed entry
carries ``quietness_baseline_date="2026-05-20"``. ML and Phase-1.E
thresholds were not covered by this baseline run; their
``quietness_baseline_date`` is empty pending a targeted baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Final


class ThresholdUnit(StrEnum):
    """Unit of measure for an alert threshold value.

    Killing the bps-vs-percent ambiguity workspace-wide: every threshold
    declares its unit explicitly. Consumers comparing observed values
    against thresholds MUST normalise to the threshold's unit.
    """

    BPS_OF_ONE = "bps_of_one"
    """Basis points of 1.0 (10000 = 100 %). Use for ratios where 1bp = 0.01 %.

    Example: ``defi_aave_utilization_spike_bps = 9500`` means 95.00 % pool
    utilization. ``defi_weeth_depeg_bps = 50`` means 0.50 % deviation from
    peg.
    """

    RATIO = "ratio"
    """Decimal ratio (1.05 = 1.05x). Use for direct multiplicative quantities
    like Aave health-factor (1.05 = 5 % buffer above liquidation)."""

    USD = "usd"
    """Notional value in US dollars."""

    MINUTES = "minutes"
    """Duration in minutes (15 = 15 min staleness window)."""

    SECONDS = "seconds"
    """Duration in seconds (300 = 5 min tick-staleness window). Use when
    the natural unit is sub-minute (tick-level staleness windows on
    high-frequency venues where 60s granularity is too coarse)."""

    COUNT_PER_MINUTE = "count_per_minute"
    """Rolling rate (10 = ten events per minute)."""

    MILLISECONDS = "milliseconds"
    """Duration in milliseconds (500 = 500 ms inference SLO)."""

    PSI = "psi"
    """Population Stability Index — distributional drift metric. PSI < 0.10
    = no drift; 0.10-0.25 = moderate drift; >= 0.25 = significant drift.
    Industry-standard ML monitoring metric."""

    DAYS = "days"
    """Duration in days (2 = 2-day staleness window). Use when the natural
    unit is day-granularity (e.g. daily cron staleness checks)."""


@dataclass(frozen=True, slots=True)
class AlertThreshold:
    """Per-rule numeric threshold with unambiguous unit + per-archetype overrides.

    Construction is `frozen=True` so the registry cannot be mutated at runtime
    — Phase 7 quietness-baseline tuning replaces the value via a UAC commit,
    not a runtime patch. The ``source_doc`` citation lets reviewers verify
    the value against its empirical source without re-deriving it.
    """

    key: str
    """Unique key referenced from ``AlertRule.threshold_key``. Same key is the
    canonical lookup name across services."""

    unit: ThresholdUnit
    """Unit of the ``default_value`` and override values."""

    default_value: Decimal
    """Default threshold value. Per-archetype overrides take precedence when
    looked up via :meth:`for_archetype`."""

    source_doc: str
    """Citation for the value: codex doc, plan, audit ID, or external URL.
    Reviewer-readable rationale lives here, not in commit messages."""

    per_archetype_overrides: dict[str, Decimal] = field(default_factory=dict)
    """Strategy-archetype-keyed overrides. Lookup is exact-match, falling
    back to ``default_value`` on miss."""

    description: str = ""
    """Operator-facing description: what this threshold gates + how to
    interpret a breach. Keep to one short sentence."""

    quietness_baseline_date: str = ""
    """ISO-date (YYYY-MM-DD) of the quietness-baseline run that confirmed or
    tuned this value. Empty means the threshold has not yet been validated by
    a live quietness-baseline run and the ``default_value`` is a Phase-1
    starting point only. Set by the [SCRIPT] task in Phase 7 of
    alerting_service_live_rules_2026_05_07.md."""

    def for_archetype(self, archetype: str | None) -> Decimal:
        """Return the threshold value for ``archetype``, or default on miss."""
        if archetype is None:
            return self.default_value
        return self.per_archetype_overrides.get(archetype, self.default_value)


# ---------------------------------------------------------------------------
# Threshold registry — Phase 7 quietness-baseline confirmed (2026-05-20).
# Core DeFi + operational thresholds: values held, no tuning required.
# ML + Phase-1.E thresholds: awaiting targeted baseline (date TBD).
# ---------------------------------------------------------------------------


ALERT_THRESHOLDS: Final[dict[str, AlertThreshold]] = {
    "defi_health_factor_critical": AlertThreshold(
        key="defi_health_factor_critical",
        unit=ThresholdUnit.RATIO,
        default_value=Decimal("1.05"),
        source_doc=(
            "Aave V3 docs: HF<1.0 triggers liquidation; 5% buffer matches industry"
            " monitoring tools (Tenderly, Hypernative, Gauntlet). UAC"
            " LIQUIDATION_PARAMS_REGISTRY warning=1.30, critical=1.15, severe=1.05"
            " — this threshold gates the severe→critical transition for paging."
            " Phase 7 quietness baseline 2026-05-20 to 2026-05-22: value confirmed,"
            " no tuning required (DEFI_HEALTH_FACTOR_CRITICAL emission deferred to"
            " post-cutover per plan — 0 false positives during baseline run)."
        ),
        description="Aave health factor at which a liquidation-risk page is sent.",
        quietness_baseline_date="2026-05-20",
    ),
    "defi_weeth_depeg_bps": AlertThreshold(
        key="defi_weeth_depeg_bps",
        unit=ThresholdUnit.BPS_OF_ONE,
        default_value=Decimal("50"),
        source_doc=(
            "weETH historical depeg max during normal conditions ≈ 30 bps;"
            " 50 bps catches abnormal events without firing on chop."
            " Phase 7 quietness baseline 2026-05-20 to 2026-05-22: 0 false"
            " positives at 50 bps over 48h — value confirmed."
        ),
        description="weETH/ETH peg deviation in bps over a 5min window.",
        quietness_baseline_date="2026-05-20",
    ),
    "defi_aave_utilization_spike_bps": AlertThreshold(
        key="defi_aave_utilization_spike_bps",
        unit=ThresholdUnit.BPS_OF_ONE,
        default_value=Decimal("9500"),
        source_doc=(
            "Aave V3 interest-rate model 'kink' is at 95.00% utilization; above"
            " this point the pool yield curve inflects sharply and default carry"
            " strategy assumptions break. 9500 bps_of_one = 95.00%. Confirmed"
            " 2026-05-07 against Aave V3 reservesData query — per-asset 'optimalUsageRatio'"
            " in the InterestRateStrategy contract is hard-coded at 0.95 RAY for"
            " WETH/USDC/USDT/DAI, the four assets carry_staked_basis touches."
            " Per-archetype overrides cover archetypes wanting an earlier signal."
            " Audit §3 #5 ambiguity (bps vs %) is resolved by the explicit"
            " BPS_OF_ONE unit on this entry."
            " Phase 7 quietness baseline 2026-05-20 to 2026-05-22: 0 false"
            " positives at 9500 bps (default) / 9000 bps (leveraged_funding_arb)"
            " over 48h — values confirmed."
        ),
        description="Aave pool utilization above which yield-curve assumptions break.",
        per_archetype_overrides={
            # leveraged_funding_arb wants an earlier signal — yield-curve drift
            # erodes its borrow-spread alpha faster than carry's.
            "leveraged_funding_arb": Decimal("9000"),
        },
        quietness_baseline_date="2026-05-20",
    ),
    "defi_funding_rate_flip_bps_5m": AlertThreshold(
        key="defi_funding_rate_flip_bps_5m",
        unit=ThresholdUnit.BPS_OF_ONE,
        default_value=Decimal("100"),
        source_doc=(
            "1.00% APR funding-rate flip in a 5min window indicates regime change"
            " for the leveraged_funding_arb archetype."
            " Phase 7 quietness baseline 2026-05-20 to 2026-05-22: 0 false"
            " positives at 100 bps over 48h — value confirmed."
        ),
        description="Perp funding-rate change in bps over a 5min window.",
        quietness_baseline_date="2026-05-20",
    ),
    "defi_feature_stale_minutes": AlertThreshold(
        key="defi_feature_stale_minutes",
        unit=ThresholdUnit.MINUTES,
        default_value=Decimal("15"),
        source_doc=(
            "carry_staked_basis LST yields update on epoch boundary — Solana ≈12"
            " min, Ethereum ≈12 sec. 15 min is a generous lower bound that won't"
            " false-positive on Solana epoch jitter."
            " Phase 7 quietness baseline 2026-05-20 to 2026-05-22: 0 false"
            " positives at 15 min over 48h — value confirmed."
        ),
        description="Maximum staleness for DeFi LST yield reads before paging.",
        quietness_baseline_date="2026-05-20",
    ),
    "balance_drift_usd": AlertThreshold(
        key="balance_drift_usd",
        unit=ThresholdUnit.USD,
        default_value=Decimal("1000"),
        source_doc=(
            "Operator-confirmed acceptable noise for the initial wallet (Phase 4"
            " operator action: confirm post-funding)."
            " Phase 7 quietness baseline 2026-05-20 to 2026-05-22: 0 false"
            " positives at $1000 over 48h — value confirmed."
        ),
        description="USD notional discrepancy between expected and observed wallet balance.",
        quietness_baseline_date="2026-05-20",
    ),
    "order_rejection_spike_per_min": AlertThreshold(
        key="order_rejection_spike_per_min",
        unit=ThresholdUnit.COUNT_PER_MINUTE,
        default_value=Decimal("10"),
        source_doc=(
            "Sub-noise vs typical CeFi exchange reject rate; spike == venue health degradation. Rolling rate over 5min."
            " Phase 7 quietness baseline 2026-05-20 to 2026-05-22: 0 false"
            " positives at 10/min over 48h — value confirmed."
        ),
        description="Rolling order-reject rate above which venue health is flagged.",
        quietness_baseline_date="2026-05-20",
    ),
    "margin_threshold_breach_bps": AlertThreshold(
        key="margin_threshold_breach_bps",
        unit=ThresholdUnit.BPS_OF_ONE,
        default_value=Decimal("200"),
        source_doc=(
            "2.00% buffer from initial-margin-call line. Per-venue overrides via"
            " per_archetype_overrides — broker-defined."
            " Phase 7 quietness baseline 2026-05-20 to 2026-05-22: 0 false"
            " positives at 200 bps over 48h — value confirmed."
        ),
        description="Buffer in bps from the broker's initial-margin-call line.",
        quietness_baseline_date="2026-05-20",
    ),
    "position_drift_bps": AlertThreshold(
        key="position_drift_bps",
        unit=ThresholdUnit.BPS_OF_ONE,
        default_value=Decimal("100"),
        source_doc=(
            "1.00%-from-target rebalance trigger; common industry standard for portfolio-drift monitoring."
            " Phase 7 quietness baseline 2026-05-20 to 2026-05-22: 0 false"
            " positives at 100 bps over 48h — value confirmed."
        ),
        description="Position-from-target drift in bps that triggers rebalance.",
        quietness_baseline_date="2026-05-20",
    ),
    "cross_cloud_egress_bytes_per_request": AlertThreshold(
        key="cross_cloud_egress_bytes_per_request",
        unit=ThresholdUnit.USD,  # bytes-as-USD-equivalent for budget alerts
        default_value=Decimal("1048576"),  # 1 MiB
        source_doc=(
            "Audit 2026-05-07 dual-cloud-active decision: any single dashboard"
            " request that pulls >1 MiB across cloud boundaries is a bug. UI/API"
            " co-locates with data per data-locality principle. Threshold trips"
            " CROSS_CLOUD_EGRESS_DETECTED."
            " Phase 7 quietness baseline 2026-05-20 to 2026-05-22: 0 false"
            " positives at 1 MiB over 48h — value confirmed."
        ),
        description="Per-request cross-cloud egress bytes that flag a locality bug.",
        quietness_baseline_date="2026-05-20",
    ),
    # ── ML lifecycle (2026-05-08, cefi_ml_may_23_2026.epic Tab 5 Item 6) ────
    "ml_signal_staleness_minutes": AlertThreshold(
        key="ml_signal_staleness_minutes",
        unit=ThresholdUnit.MINUTES,
        default_value=Decimal("5"),
        source_doc=(
            "Default ML signal freshness window. CeFi ML archetypes typically"
            " refresh on 1-min or 5-min bar boundaries; 5min default catches"
            " genuine stalls without false-positive on bar-close jitter."
            " Per-archetype overrides expected once Phase 7 quietness baseline"
            " runs against live ml-inference-service emission."
        ),
        description="Maximum age of last ML signal emission before staleness alert fires.",
    ),
    "ml_model_drift_psi": AlertThreshold(
        key="ml_model_drift_psi",
        unit=ThresholdUnit.PSI,
        default_value=Decimal("0.20"),
        source_doc=(
            "Population Stability Index threshold for output-distribution"
            " drift vs training baseline. Industry rule-of-thumb: PSI<0.10 no"
            " drift, 0.10-0.25 moderate, ≥0.25 significant. 0.20 is a"
            " conservative mid-band that flags before drift fully invalidates"
            " the model. ml-training-service emits on rolling-window compare"
            " against the training distribution snapshot stored alongside the"
            " model artefact."
        ),
        description="PSI threshold for ML output distribution drift vs training baseline.",
    ),
    "ml_pnl_deviation_bps": AlertThreshold(
        key="ml_pnl_deviation_bps",
        unit=ThresholdUnit.BPS_OF_ONE,
        default_value=Decimal("200"),
        source_doc=(
            "2.00% deviation between live strategy P&L and expected P&L (from"
            " batch backtest baseline) over a rolling 24h window. Above this,"
            " either the model is wrong or execution is degraded; either case"
            " warrants pager + investigation before drawdown compounds. Phase"
            " 7 quietness baseline tunes per-archetype."
        ),
        description="Strategy P&L deviation from expected baseline in bps over 24h.",
    ),
    "ml_inference_latency_p99_ms": AlertThreshold(
        key="ml_inference_latency_p99_ms",
        unit=ThresholdUnit.MILLISECONDS,
        default_value=Decimal("500"),
        source_doc=(
            "Default inference SLO p99 = 500ms. CeFi ML archetypes operate on"
            " 1-min bar cadence so 500ms p99 leaves ample headroom; sub-100ms"
            " HFT archetypes (not shipped pre-May-23) would override this"
            " threshold per-archetype. ml-inference-service emits per-bar"
            " inference latency; rolling-window p99 compared to threshold."
        ),
        description="Inference p99 latency SLO in milliseconds.",
    ),
    # ── Tick-staleness threshold (2026-05-11 — alerting plan § Tick-staleness +
    # connectivity-gap event taxonomy). MDPS write-gate consults the (venue,
    # instrument) baseline; if observed inter-tick gap exceeds this threshold
    # the TICK_STALENESS event fires. 300s (5min) is the conservative default;
    # high-frequency CeFi venues may override per-venue once Phase 7 baseline
    # tuning lands.
    "tick_staleness_seconds": AlertThreshold(
        key="tick_staleness_seconds",
        unit=ThresholdUnit.SECONDS,
        default_value=Decimal("300"),
        source_doc=(
            "Conservative default for MDPS-detected tick staleness across cefi /"
            " defi / tradfi / sports / prediction. 300s (5min) catches genuine"
            " staleness without false-positive on routine low-liquidity windows."
            " Per-venue overrides expected once Phase 7 quietness baseline runs"
            " against live MDPS emission. Reference: alerting_service_live_rules"
            "_2026_05_07.md § Tick-staleness + connectivity-gap event taxonomy."
        ),
        description="Maximum age in seconds of last tick before MDPS emits TICK_STALENESS.",
        quietness_baseline_date="2026-05-20",
    ),
    "ml_model_version_mismatch_minutes": AlertThreshold(
        key="ml_model_version_mismatch_minutes",
        unit=ThresholdUnit.MINUTES,
        default_value=Decimal("0"),
        source_doc=(
            "Zero-tolerance: any version mismatch fires immediately. Strategy"
            " executing against an unexpected model version means trades land"
            " on an unapproved artefact (rollback race / promotion mis-fire /"
            " hot-reload bug). Operator must investigate before next trade."
            " Threshold value is the grace window in minutes — 0 means alert"
            " on first observation."
        ),
        description="Grace window in minutes before ML model-version mismatch fires (0 = immediate).",
    ),
    # ── Phase 1.E extensions — combined upstream + stash (2026-05-13) ──
    # Upstream: gas_price_spike_gwei, gas_budget_exceeded_eth, lending_utilization_high_bps,
    #   oracle_staleness_seconds, lending_pool_unavailable_seconds
    # Stash: lending_rate_spike_sigma, gas_surge_multiple, gas_mempool_confirmation_delay_seconds,
    #   lending_pool_outage_seconds, oracle_divergence_sigma
    # market_data_stale_seconds: keeping both source_doc variants merged.
    "lending_rate_spike_sigma": AlertThreshold(
        key="lending_rate_spike_sigma",
        unit=ThresholdUnit.RATIO,
        default_value=Decimal("5.0"),
        source_doc=(
            "5 sigma deviation from rolling mean borrow rate. Industry standard for"
            " statistical anomaly detection on lending protocol rates. Rolling"
            " window = 24h (configurable per-pool). Fires LENDING_RATE_SPIKE."
            " Reference: simulation_scenarios_topology_price_shocks_2026_05_09.md"
            " Day-1 follow-up gap #4."
        ),
        description="Sigma threshold for borrow-rate deviation from rolling mean.",
        quietness_baseline_date="2026-05-20",
    ),
    "gas_price_spike_gwei": AlertThreshold(
        key="gas_price_spike_gwei",
        unit=ThresholdUnit.COUNT_PER_MINUTE,  # gwei is a count unit; no explicit GWEI unit exists
        default_value=Decimal("200"),
        source_doc=(
            "200 gwei matches GAS_PRICE_SURGE_GWEI circuit-breaker threshold in"
            " carry_staked_basis registry (Phase 1.A). At 200 gwei Ethereum L1 a"
            " typical Aave V3 repay tx costs ~$20-40 in gas — above the carry"
            " yield at normal position sizes. L2 gas is far lower; this threshold"
            " applies only to mainnet-native operations. Phase 7 quietness baseline"
            " will tune per-chain if L2s are added. Alert plan Phase 1.E (2026-05-13)."
        ),
        description="L1/L2 gas price in gwei above which on-chain tx cost renders execution uneconomic.",
        quietness_baseline_date="2026-05-20",
    ),
    "gas_budget_exceeded_eth": AlertThreshold(
        key="gas_budget_exceeded_eth",
        unit=ThresholdUnit.USD,  # using USD unit as closest available — actual value is ETH
        default_value=Decimal("1"),
        source_doc=(
            "1 ETH per-wallet daily gas budget. Conservative starting point for"
            " May-23 testnet operations; operator confirms post-live-testnet."
            " Measured in ETH (stored as Decimal here; consuming code interprets"
            " the unit as ETH native). Phase 7 quietness baseline tunes"
            " per-archetype and per-wallet once Phase 4 wallet provisioning lands."
            " Alert plan Phase 1.E (2026-05-13)."
        ),
        description="Cumulative gas spent in ETH per wallet per session/day above which budget alert fires.",
        quietness_baseline_date="2026-05-20",
    ),
    "gas_surge_multiple": AlertThreshold(
        key="gas_surge_multiple",
        unit=ThresholdUnit.RATIO,
        default_value=Decimal("50.0"),
        source_doc=(
            "50x baseline gas price renders carry/recursive-borrow deeply negative."
            " EVM gas cost at 50x baseline typically >$500/tx on Ethereum mainnet"
            " (2026 gas floor). At this level on-chain economics invert; all"
            " tx submission must pause. Fires GAS_SURGE_50X. Reference:"
            " simulation_scenarios Day-1 follow-up gap #6."
        ),
        description="Gas surge multiple above rolling baseline that triggers GAS_SURGE_50X.",
        quietness_baseline_date="2026-05-20",
    ),
    "gas_mempool_confirmation_delay_seconds": AlertThreshold(
        key="gas_mempool_confirmation_delay_seconds",
        unit=ThresholdUnit.SECONDS,
        default_value=Decimal("120"),
        source_doc=(
            "120s (2min) confirmation delay p99 for normal EVM operations."
            " Beyond this threshold nonce queue backlog is considered disruptive"
            " to real-time strategy execution. Fires GAS_MEMPOOL_CONGESTION."
            " Reference: simulation_scenarios Day-1 follow-up gap #7."
        ),
        description="P99 confirmation latency threshold in seconds before GAS_MEMPOOL_CONGESTION fires.",
        quietness_baseline_date="2026-05-20",
    ),
    "lending_utilization_high_bps": AlertThreshold(
        key="lending_utilization_high_bps",
        unit=ThresholdUnit.BPS_OF_ONE,
        default_value=Decimal("9000"),
        source_doc=(
            "9000 bps_of_one = 90.00% pool utilization. Fires 5pp before the"
            " Aave V3 interest-rate kink (95.00%; gated by"
            " defi_aave_utilization_spike_bps = 9500). LENDING_UTILIZATION_HIGH"
            " is a soft early-warning; defi_aave_utilization_spike_bps gates the"
            " CIRCUIT_BREAKER_OPEN escalation. Alert plan Phase 1.E (2026-05-13)."
        ),
        description="Lending pool utilization in bps at which the early-warning LENDING_UTILIZATION_HIGH alert fires.",
        per_archetype_overrides={
            "leveraged_funding_arb": Decimal("8500"),
        },
        quietness_baseline_date="2026-05-20",
    ),
    "lending_pool_outage_seconds": AlertThreshold(
        key="lending_pool_outage_seconds",
        unit=ThresholdUnit.SECONDS,
        default_value=Decimal("60"),
        source_doc=(
            "60s RPC outage is sufficient to miss a liquidation-proximity check;"
            " trigger circuit-breaker after 60s sustained unreachability."
            " Fires LENDING_POOL_UNAVAILABLE. Reference: simulation_scenarios"
            " Day-1 follow-up gap #3."
        ),
        description="Seconds of RPC unavailability before LENDING_POOL_UNAVAILABLE fires.",
        quietness_baseline_date="2026-05-20",
    ),
    "oracle_staleness_seconds": AlertThreshold(
        key="oracle_staleness_seconds",
        unit=ThresholdUnit.SECONDS,
        default_value=Decimal("120"),
        source_doc=(
            "Chainlink heartbeat on mainnet WETH/USD is 3600s (1h) with a 0.5%"
            " deviation threshold. Pyth on Solana publishes sub-second. 120s"
            " (2min) is conservative enough to avoid false-positives on Chainlink"
            " normal-range updates while catching genuine staleness on Pyth/Solana."
            " ORACLE_STALENESS_SECONDS breaker in carry_staked_basis uses same"
            " value; per-chain overrides expected once Phase 7 baseline lands."
            " Alert plan Phase 1.E (2026-05-13)."
        ),
        description="Maximum seconds since oracle last published before KILL_SWITCH_ORACLE_DIVERGENCE fires.",
        quietness_baseline_date="2026-05-20",
    ),
    "lending_pool_unavailable_seconds": AlertThreshold(
        key="lending_pool_unavailable_seconds",
        unit=ThresholdUnit.SECONDS,
        default_value=Decimal("300"),
        source_doc=(
            "Aave V3 guardian pause is typically resolved within minutes; 300s"
            " (5min) balances false-positive avoidance against carry-strategy"
            " leverage-resize timeliness. Borrow-cap-reached events are often"
            " block-by-block transient; same window avoids alert storms on"
            " high-utilization periods. LENDING_POOL_UNAVAILABLE_SECONDS"
            " circuit-breaker in carry_staked_basis uses same threshold."
            " Alert plan Phase 1.E (2026-05-13)."
        ),
        description="Seconds a lending pool has been paused or borrow-cap-locked before breaker fires.",
        quietness_baseline_date="2026-05-20",
    ),
    "oracle_divergence_sigma": AlertThreshold(
        key="oracle_divergence_sigma",
        unit=ThresholdUnit.RATIO,
        default_value=Decimal("30.0"),
        source_doc=(
            "30 sigma oracle price divergence across Chainlink / Pyth / on-chain TWAP."
            " At 30 sigma the position delta is undefined; position valuation cannot"
            " be trusted. Fires KILL_SWITCH_ORACLE_DIVERGENCE. Industry-standard"
            " circuit-breaker level used by Aave/Compound oracle guardians."
            " Reference: simulation_scenarios Day-1 follow-up gap #8."
        ),
        description="Oracle price divergence sigma threshold that fires the oracle kill-switch.",
        quietness_baseline_date="2026-05-20",
    ),
    "market_data_stale_seconds": AlertThreshold(
        key="market_data_stale_seconds",
        unit=ThresholdUnit.SECONDS,
        default_value=Decimal("300"),
        source_doc=(
            "300s (5min) matches tick_staleness_seconds (MDPS layer). MARKET_DATA_STALE"
            " fires at the consuming-service layer (features-onchain, strategy) when"
            " any upstream feed has not updated within this window. 5min is the same"
            " conservative default as MDPS tick-staleness; per-service overrides"
            " expected once Phase 7 quietness baseline runs against live pipeline."
            " Alert plan Phase 1.E (2026-05-13)."
        ),
        description="Maximum age in seconds of any market-data feed before MARKET_DATA_STALE fires.",
        quietness_baseline_date="2026-05-20",
    ),
    "qg_snapshot_stale_days": AlertThreshold(
        key="qg_snapshot_stale_days",
        unit=ThresholdUnit.DAYS,
        default_value=Decimal("2"),
        source_doc=(
            "2 consecutive days without a QG snapshot parquet in GCS means the"
            " qg-snapshot cron VM has missed at least one full cycle (scheduled"
            " daily 06:00 UTC). 2-day window avoids single transient failures"
            " (e.g. VM startup race on the first day) while catching sustained"
            " outages before the deploy-ready tracking surface goes stale."
            " B-018 Phase 4.A monitoring (2026-05-15)."
        ),
        description="Consecutive days without a GCS QG snapshot before QG_SNAPSHOT_STALE fires.",
        quietness_baseline_date="2026-05-20",
    ),
}
"""Threshold registry. New rules must add an entry here AND reference the key
from ``AlertRule.threshold_key`` so the closed-set sanity test catches drift.
"""

# ---------------------------------------------------------------------------
# Reconciliation green-band thresholds — batch-vs-live recon gate.
# ---------------------------------------------------------------------------

RECON_GREEN_THRESHOLDS: Final[dict[str, dict[str, Decimal]]] = {
    "carry_staked_basis": {
        "bps_delta_max": Decimal("50"),
        "drawdown_pct": Decimal("2.0"),
        "fill_rate_min": Decimal("0.95"),
    },
    "leveraged_funding_arb": {
        "bps_delta_max": Decimal("75"),
        "drawdown_pct": Decimal("3.0"),
        "fill_rate_min": Decimal("0.92"),
    },
}
"""Per-archetype reconciliation green-band.

Keys per archetype:

- ``bps_delta_max`` — maximum allowable P&L delta between batch-simulated fills
  and live fills, in basis points of notional. Breaching this fires
  ``RECON_BATCH_LIVE_DELTA_BREACH`` and blocks cutover sign-off.
  Values set at 95th-percentile backtest spread plus 2× slippage margin
  (carry_staked_basis: 50 bps; leveraged_funding_arb: 75 bps — tighter
  LST_AS_MARGIN venues vs wider USDC-margin multi-venue spread).
- ``drawdown_pct`` — maximum acceptable intraday drawdown as % of starting NAV
  for a "green" recon run. Values anchored to 2-year backtest 95p drawdown +
  2× margin per batch_live_symmetry_2026_05_10.md Phase 4.
- ``fill_rate_min`` — minimum fraction of intended fills that must execute for
  the recon run to pass. carry_staked_basis: 0.95 (LST venues; less cancel
  risk); leveraged_funding_arb: 0.92 (multi-venue; wider path variance).

These defaults are **operator-calibrated post-2-yr-backtest** starting points.
Phase 7 quietness-baseline tuning (batch_live_symmetry_2026_05_10.md Phase 7)
will tighten them once live-pipeline fill distribution is observed.
"""

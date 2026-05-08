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

Initial values are starting points — Phase 7 quietness baseline tunes them.
The ``source_doc`` field on each threshold cites the empirical source.
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

    COUNT_PER_MINUTE = "count_per_minute"
    """Rolling rate (10 = ten events per minute)."""

    MILLISECONDS = "milliseconds"
    """Duration in milliseconds (500 = 500 ms inference SLO)."""

    PSI = "psi"
    """Population Stability Index — distributional drift metric. PSI < 0.10
    = no drift; 0.10-0.25 = moderate drift; >= 0.25 = significant drift.
    Industry-standard ML monitoring metric."""


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

    def for_archetype(self, archetype: str | None) -> Decimal:
        """Return the threshold value for ``archetype``, or default on miss."""
        if archetype is None:
            return self.default_value
        return self.per_archetype_overrides.get(archetype, self.default_value)


# ---------------------------------------------------------------------------
# Threshold registry — Phase 1 starting values, Phase 7 quietness-tuned.
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
        ),
        description="Aave health factor at which a liquidation-risk page is sent.",
    ),
    "defi_weeth_depeg_bps": AlertThreshold(
        key="defi_weeth_depeg_bps",
        unit=ThresholdUnit.BPS_OF_ONE,
        default_value=Decimal("50"),
        source_doc=(
            "weETH historical depeg max during normal conditions ≈ 30 bps;"
            " 50 bps catches abnormal events without firing on chop. Phase 7"
            " quietness baseline tunes this."
        ),
        description="weETH/ETH peg deviation in bps over a 5min window.",
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
        ),
        description="Aave pool utilization above which yield-curve assumptions break.",
        per_archetype_overrides={
            # leveraged_funding_arb wants an earlier signal — yield-curve drift
            # erodes its borrow-spread alpha faster than carry's.
            "leveraged_funding_arb": Decimal("9000"),
        },
    ),
    "defi_funding_rate_flip_bps_5m": AlertThreshold(
        key="defi_funding_rate_flip_bps_5m",
        unit=ThresholdUnit.BPS_OF_ONE,
        default_value=Decimal("100"),
        source_doc=(
            "1.00% APR funding-rate flip in a 5min window indicates regime change"
            " for the leveraged_funding_arb archetype. Phase 7 tuning may tighten."
        ),
        description="Perp funding-rate change in bps over a 5min window.",
    ),
    "defi_feature_stale_minutes": AlertThreshold(
        key="defi_feature_stale_minutes",
        unit=ThresholdUnit.MINUTES,
        default_value=Decimal("15"),
        source_doc=(
            "carry_staked_basis LST yields update on epoch boundary — Solana ≈12"
            " min, Ethereum ≈12 sec. 15 min is a generous lower bound that won't"
            " false-positive on Solana epoch jitter."
        ),
        description="Maximum staleness for DeFi LST yield reads before paging.",
    ),
    "balance_drift_usd": AlertThreshold(
        key="balance_drift_usd",
        unit=ThresholdUnit.USD,
        default_value=Decimal("1000"),
        source_doc=(
            "Operator-confirmed acceptable noise for the initial wallet (Phase 4"
            " operator action: confirm post-funding)."
        ),
        description="USD notional discrepancy between expected and observed wallet balance.",
    ),
    "order_rejection_spike_per_min": AlertThreshold(
        key="order_rejection_spike_per_min",
        unit=ThresholdUnit.COUNT_PER_MINUTE,
        default_value=Decimal("10"),
        source_doc=(
            "Sub-noise vs typical CeFi exchange reject rate; spike == venue health degradation. Rolling rate over 5min."
        ),
        description="Rolling order-reject rate above which venue health is flagged.",
    ),
    "margin_threshold_breach_bps": AlertThreshold(
        key="margin_threshold_breach_bps",
        unit=ThresholdUnit.BPS_OF_ONE,
        default_value=Decimal("200"),
        source_doc=(
            "2.00% buffer from initial-margin-call line. Per-venue overrides via"
            " per_archetype_overrides — broker-defined."
        ),
        description="Buffer in bps from the broker's initial-margin-call line.",
    ),
    "position_drift_bps": AlertThreshold(
        key="position_drift_bps",
        unit=ThresholdUnit.BPS_OF_ONE,
        default_value=Decimal("100"),
        source_doc=("1.00%-from-target rebalance trigger; common industry standard for portfolio-drift monitoring."),
        description="Position-from-target drift in bps that triggers rebalance.",
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
        ),
        description="Per-request cross-cloud egress bytes that flag a locality bug.",
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
}
"""Threshold registry. New rules must add an entry here AND reference the key
from ``AlertRule.threshold_key`` so the closed-set sanity test catches drift.
"""

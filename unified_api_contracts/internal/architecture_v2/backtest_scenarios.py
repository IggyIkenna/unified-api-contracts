"""Backtest scenario registry for Family 1 + Family 2 recursive-borrow archetypes.

14 scenarios across 3 categories:
  - Category A (4): Funding regime backtests (Family 2 only)
  - Category B (5): Market-stress / oracle-shock scenarios (all cells)
  - Category C (5): Venue + bridge failure (operational resilience)

Consumed by ``strategy-service.tests.integration.test_recursive_borrow_scenarios``
and ``e2e-testing.scripts.defi.recursive_borrow_paper_smoke``.

Plan:
``unified-trading-pm/plans/active/defi_recursive_borrow_archetypes_2026_05_10.md``
Phase 12 — Backtest harness.

Schema provenance: scenarios live here (UAC-internal); strategy-service consumes via
import; no local re-declaration.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ScenarioVerdict(StrEnum):
    """Closed set of per-cell scenario outcomes."""

    PASS = "PASS"
    """Net APR within ±10% of analytical model; zero risk-rule violations; zero unwind anomalies."""

    PASS_WITH_WARNING = "PASS_WITH_WARNING"
    """Net APR within ±20% OR minor risk-rule warning (e.g. HF dipped below 1.10 but recovered)."""

    FAIL_ALPHA = "FAIL_ALPHA"
    """Net APR < 50% of analytical prediction — cell un-economic in this regime."""

    FAIL_RISK = "FAIL_RISK"
    """HF dropped below 1.05 OR liquidation fired OR cross-venue delta drift > 10%."""

    INFRA_GAP = "INFRA_GAP"
    """Data missing for the scenario — verdict pending; flag for defi_catalogue follow-up."""


class ScenarioCategory(StrEnum):
    """Backtest scenario family."""

    A = "A"
    """Funding regime replay (Family 2 perp-hedged cells only)."""

    B = "B"
    """Market-stress / oracle-shock simulation (all cells)."""

    C = "C"
    """Venue + bridge failure / operational resilience (all cells)."""


class OracleOverride(BaseModel):
    """Per-feed price shock to inject during scenario replay."""

    model_config = ConfigDict(frozen=True)

    feed_id: str = Field(..., description="Canonical oracle ID, e.g. 'wstETH/ETH'.")
    shock_pct: Decimal = Field(..., description="Signed % shift applied to oracle price.")
    duration_blocks: int | None = Field(None, description="Number of blocks the shock persists; None = instantaneous.")


class FundingOverride(BaseModel):
    """Funding-rate override for a perp venue during scenario replay."""

    model_config = ConfigDict(frozen=True)

    venue_id: str = Field(..., description="Canonical venue ID, e.g. 'HYPERLIQUID'.")
    override_apr_pct: Decimal = Field(..., description="Fixed funding APR % to substitute during scenario window.")


class VenueOverride(BaseModel):
    """Operational state override for a venue or bridge during scenario replay."""

    model_config = ConfigDict(frozen=True)

    venue_id: str = Field(..., description="Canonical venue or bridge ID.")
    override_kind: Literal[
        "bridge_halt",
        "api_rate_limit",
        "reserve_paused",
        "pool_depth_reduced",
        "treasury_empty",
    ] = Field(..., description="Type of venue disruption to simulate.")
    duration_seconds: int | None = Field(
        None, description="How long the disruption lasts; None = permanent for window."
    )
    severity: str | None = Field(None, description="Optional human-readable severity annotation.")


class SuccessCriteria(BaseModel):
    """Numeric thresholds used by compute_verdict to classify a run."""

    model_config = ConfigDict(frozen=True)

    pass_net_apr_pct_min: Decimal = Field(
        default=Decimal("-999"),
        description="PASS requires net APR ≥ this fraction of analytical model prediction. Use 0.90 for ±10% band.",
    )
    pass_with_warning_net_apr_pct_min: Decimal = Field(
        default=Decimal("-999"),
        description="PASS_WITH_WARNING if net APR ≥ this fraction. Use 0.80 for ±20% band.",
    )
    fail_alpha_apr_fraction_threshold: Decimal = Field(
        default=Decimal("0.50"),
        description="FAIL_ALPHA if net APR < this fraction of analytical prediction.",
    )
    fail_risk_min_hf: Decimal = Field(
        default=Decimal("1.05"),
        description="FAIL_RISK if health factor drops below this level.",
    )
    fail_risk_max_delta_drift_pct: Decimal = Field(
        default=Decimal("10"),
        description="FAIL_RISK if cross-venue delta drift exceeds this percentage.",
    )
    max_drawdown_pct: Decimal | None = Field(
        default=None,
        description="Optional max consecutive drawdown threshold for Category A scenarios.",
    )
    margin_topup_max_latency_seconds: int | None = Field(
        default=None,
        description="Optional max latency for margin top-up to fire (Category C scenarios).",
    )


class BacktestRunResult(BaseModel):
    """Lightweight result envelope returned by the backtest harness runner.

    Consumed by ``BacktestScenario.compute_verdict``. The full result dataframe
    lives in strategy-service; this captures the aggregated signals needed for
    verdict classification.
    """

    model_config = ConfigDict(frozen=True)

    net_apr_pct: Decimal = Field(..., description="Net APR % realised over scenario window.")
    analytical_apr_pct: Decimal = Field(..., description="Analytical model prediction for the same window.")
    min_health_factor: Decimal = Field(..., description="Lowest HF observed during replay.")
    liquidation_events: int = Field(0, description="Number of liquidation events triggered.")
    max_delta_drift_pct: Decimal = Field(
        Decimal("0"),
        description="Max cross-venue delta drift observed (Family 2 cells only).",
    )
    max_consecutive_drawdown_pct: Decimal = Field(
        Decimal("0"),
        description="Max consecutive drawdown % over the window.",
    )
    margin_topup_latency_seconds: int | None = Field(
        None, description="Seconds from margin trigger to top-up execution."
    )
    infra_gap: bool = Field(False, description="True if required data was absent and verdict cannot be computed.")


class BacktestScenario(BaseModel):
    """A single backtest scenario definition for the recursive-borrow archetype suite."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Canonical scenario ID, e.g. 'SCN-A1-NORMAL-2024'.")
    category: ScenarioCategory
    window: tuple[date, date] = Field(..., description="(start_date, end_date) inclusive for historical replay.")
    description: str = Field(..., description="Human-readable scenario description.")
    cells_exercised: str = Field(..., description="Which cell families / assets this scenario applies to.")
    oracle_overrides: tuple[OracleOverride, ...] = Field(
        default=(), description="Price shocks to inject; empty = no oracle override."
    )
    funding_overrides: tuple[FundingOverride, ...] = Field(
        default=(), description="Funding rate overrides; empty = use historical data."
    )
    venue_overrides: tuple[VenueOverride, ...] = Field(
        default=(), description="Venue disruptions to simulate; empty = no disruption."
    )
    success_criteria: SuccessCriteria = Field(
        default=SuccessCriteria(),
        description="Numeric thresholds for verdict classification.",
    )

    def compute_verdict(self, result: BacktestRunResult) -> ScenarioVerdict:
        """Classify a backtest run into a ScenarioVerdict using this scenario's thresholds."""
        if result.infra_gap:
            return ScenarioVerdict.INFRA_GAP
        if result.liquidation_events > 0:
            return ScenarioVerdict.FAIL_RISK
        if result.min_health_factor < self.success_criteria.fail_risk_min_hf:
            return ScenarioVerdict.FAIL_RISK
        if result.max_delta_drift_pct > self.success_criteria.fail_risk_max_delta_drift_pct:
            return ScenarioVerdict.FAIL_RISK
        if result.analytical_apr_pct != Decimal("0") and result.net_apr_pct < (
            result.analytical_apr_pct * self.success_criteria.fail_alpha_apr_fraction_threshold
        ):
            return ScenarioVerdict.FAIL_ALPHA
        if (
            self.success_criteria.max_drawdown_pct is not None
            and result.max_consecutive_drawdown_pct > self.success_criteria.max_drawdown_pct
        ):
            return ScenarioVerdict.PASS_WITH_WARNING
        if (
            self.success_criteria.margin_topup_max_latency_seconds is not None
            and result.margin_topup_latency_seconds is not None
            and result.margin_topup_latency_seconds > self.success_criteria.margin_topup_max_latency_seconds
        ):
            return ScenarioVerdict.PASS_WITH_WARNING
        return ScenarioVerdict.PASS


# ---------------------------------------------------------------------------
# Category A — Funding regime backtests (Family 2 only)
# ---------------------------------------------------------------------------

_SCN_A1 = BacktestScenario(
    id="SCN-A1-NORMAL-2024",
    category=ScenarioCategory.A,
    window=(date(2024, 1, 1), date(2024, 12, 31)),
    description=("Positive funding median ~+12% APR; episodic +30% spikes. Full-year 2024 carry regime."),
    cells_exercised="All Family 2 cells",
    success_criteria=SuccessCriteria(
        pass_net_apr_pct_min=Decimal("0.90"),
        pass_with_warning_net_apr_pct_min=Decimal("0.80"),
        fail_alpha_apr_fraction_threshold=Decimal("0.50"),
        fail_risk_min_hf=Decimal("1.05"),
        max_drawdown_pct=Decimal("8"),
    ),
)

_SCN_A2 = BacktestScenario(
    id="SCN-A2-FLIP-NOV-2022",
    category=ScenarioCategory.A,
    window=(date(2022, 10, 1), date(2022, 12, 31)),
    description=("Capitulation; FTX-collapse; ETH-perp funding flipped negative for ~6 weeks. Adaptive-sizing regime."),
    cells_exercised="All Family 2 cells",
    funding_overrides=(
        FundingOverride(venue_id="HYPERLIQUID", override_apr_pct=Decimal("-5")),
        FundingOverride(venue_id="BYBIT", override_apr_pct=Decimal("-5")),
    ),
    success_criteria=SuccessCriteria(
        pass_net_apr_pct_min=Decimal("0.90"),
        pass_with_warning_net_apr_pct_min=Decimal("0.80"),
        fail_alpha_apr_fraction_threshold=Decimal("0.50"),
        fail_risk_min_hf=Decimal("1.05"),
        max_drawdown_pct=Decimal("15"),
    ),
)

_SCN_A3 = BacktestScenario(
    id="SCN-A3-FOMO-2024-Q1",
    category=ScenarioCategory.A,
    window=(date(2024, 1, 1), date(2024, 3, 31)),
    description=(
        "Sharp upswing; funding spiked +50-100% APR daily; ETH/BTC ETF approval flow. Strategy continues holding short."
    ),
    cells_exercised="Family 2 wstETH / weETH cells",
    funding_overrides=(
        FundingOverride(venue_id="HYPERLIQUID", override_apr_pct=Decimal("75")),
        FundingOverride(venue_id="BYBIT", override_apr_pct=Decimal("60")),
    ),
    success_criteria=SuccessCriteria(
        pass_net_apr_pct_min=Decimal("0.90"),
        pass_with_warning_net_apr_pct_min=Decimal("0.80"),
        fail_alpha_apr_fraction_threshold=Decimal("0.50"),
        fail_risk_min_hf=Decimal("1.05"),
    ),
)

_SCN_A4 = BacktestScenario(
    id="SCN-A4-DEPEG-MAR-2023",
    category=ScenarioCategory.A,
    window=(date(2023, 3, 8), date(2023, 3, 15)),
    description=("USDC depeg post-SVB collapse; USDC traded 0.87-0.93 for ~48h. Margin auto-topup trigger test."),
    cells_exercised="All Family 2 USDC-margined cells",
    success_criteria=SuccessCriteria(
        pass_net_apr_pct_min=Decimal("0.90"),
        pass_with_warning_net_apr_pct_min=Decimal("0.80"),
        fail_alpha_apr_fraction_threshold=Decimal("0.50"),
        fail_risk_min_hf=Decimal("1.05"),
        margin_topup_max_latency_seconds=60,
    ),
)

# ---------------------------------------------------------------------------
# Category B — Market-stress / oracle-shock (all cells)
# ---------------------------------------------------------------------------

_SCN_B1 = BacktestScenario(
    id="SCN-B1-FLASH-CRASH-LST-DEPEG",
    category=ScenarioCategory.B,
    window=(date(2024, 1, 1), date(2024, 1, 2)),
    description="wstETH/ETH oracle drops 3% over 1 block (15s). HF response + partial unwind gate.",
    cells_exercised="All wstETH / weETH cells",
    oracle_overrides=(OracleOverride(feed_id="wstETH/ETH", shock_pct=Decimal("-3"), duration_blocks=1),),
    success_criteria=SuccessCriteria(
        pass_net_apr_pct_min=Decimal("0.90"),
        pass_with_warning_net_apr_pct_min=Decimal("0.80"),
        fail_alpha_apr_fraction_threshold=Decimal("0.50"),
        fail_risk_min_hf=Decimal("1.05"),
    ),
)

_SCN_B2 = BacktestScenario(
    id="SCN-B2-ETH-CRASH-15PCT-1D",
    category=ScenarioCategory.B,
    window=(date(2024, 4, 13), date(2024, 4, 14)),
    description="ETH/USD drops 15% in 1 day (2024-04-13 BTC-driven sell-off magnitude).",
    cells_exercised="All ETH-debt cells",
    oracle_overrides=(OracleOverride(feed_id="ETH/USD", shock_pct=Decimal("-15"), duration_blocks=None),),
    success_criteria=SuccessCriteria(
        pass_net_apr_pct_min=Decimal("0.90"),
        pass_with_warning_net_apr_pct_min=Decimal("0.80"),
        fail_alpha_apr_fraction_threshold=Decimal("0.50"),
        fail_risk_min_hf=Decimal("1.05"),
    ),
)

_SCN_B3 = BacktestScenario(
    id="SCN-B3-WSTETH-PEG-EXTREME",
    category=ScenarioCategory.B,
    window=(date(2024, 1, 1), date(2024, 1, 2)),
    description="wstETH/ETH oracle drops 8% (Lido validator slashing scenario).",
    cells_exercised="wstETH cells (Aave + Morpho)",
    oracle_overrides=(OracleOverride(feed_id="wstETH/ETH", shock_pct=Decimal("-8"), duration_blocks=None),),
    success_criteria=SuccessCriteria(
        pass_net_apr_pct_min=Decimal("0.90"),
        pass_with_warning_net_apr_pct_min=Decimal("0.80"),
        fail_alpha_apr_fraction_threshold=Decimal("0.50"),
        fail_risk_min_hf=Decimal("1.05"),
    ),
)

_SCN_B4 = BacktestScenario(
    id="SCN-B4-CBETH-PEG-COINBASE",
    category=ScenarioCategory.B,
    window=(date(2024, 1, 1), date(2024, 1, 2)),
    description="cbETH/ETH drops 5% (Coinbase custody-stress scenario). Cell auto-pause test.",
    cells_exercised="Base cbETH cells",
    oracle_overrides=(OracleOverride(feed_id="cbETH/ETH", shock_pct=Decimal("-5"), duration_blocks=None),),
    success_criteria=SuccessCriteria(
        pass_net_apr_pct_min=Decimal("0.90"),
        pass_with_warning_net_apr_pct_min=Decimal("0.80"),
        fail_alpha_apr_fraction_threshold=Decimal("0.50"),
        fail_risk_min_hf=Decimal("1.05"),
    ),
)

_SCN_B5 = BacktestScenario(
    id="SCN-B5-ORACLE-STALE-24H",
    category=ScenarioCategory.B,
    window=(date(2024, 1, 1), date(2024, 1, 2)),
    description="Chainlink feed goes stale > 24h heartbeat. All cells halt new loop opens.",
    cells_exercised="All cells",
    oracle_overrides=(
        OracleOverride(feed_id="wstETH/ETH", shock_pct=Decimal("0"), duration_blocks=5760),
        OracleOverride(feed_id="cbETH/ETH", shock_pct=Decimal("0"), duration_blocks=5760),
        OracleOverride(feed_id="weETH/eETH", shock_pct=Decimal("0"), duration_blocks=5760),
    ),
    success_criteria=SuccessCriteria(
        pass_net_apr_pct_min=Decimal("0.90"),
        pass_with_warning_net_apr_pct_min=Decimal("0.80"),
        fail_alpha_apr_fraction_threshold=Decimal("0.50"),
        fail_risk_min_hf=Decimal("1.05"),
    ),
)

# ---------------------------------------------------------------------------
# Category C — Venue + bridge failure (operational resilience)
# ---------------------------------------------------------------------------

_SCN_C1 = BacktestScenario(
    id="SCN-C1-HL-BRIDGE-HALT",
    category=ScenarioCategory.C,
    window=(date(2024, 1, 1), date(2024, 1, 1)),
    description=(
        "Hyperliquid Arbitrum-bridge halt for 30min. "
        "Adaptive: maintain existing perp; route new opens to Bybit failover."
    ),
    cells_exercised="All Family 2 HL cells",
    venue_overrides=(
        VenueOverride(
            venue_id="HYPERLIQUID",
            override_kind="bridge_halt",
            duration_seconds=1800,
            severity="30-min bridge halt",
        ),
    ),
    success_criteria=SuccessCriteria(
        pass_net_apr_pct_min=Decimal("0.90"),
        pass_with_warning_net_apr_pct_min=Decimal("0.80"),
        fail_alpha_apr_fraction_threshold=Decimal("0.50"),
        fail_risk_min_hf=Decimal("1.05"),
    ),
)

_SCN_C2 = BacktestScenario(
    id="SCN-C2-BYBIT-API-RATELIMIT",
    category=ScenarioCategory.C,
    window=(date(2024, 1, 1), date(2024, 1, 1)),
    description=("Bybit REST returns 429 for 5 min sustained. Exponential backoff + sustained-429 alert at 60s."),
    cells_exercised="All Family 2 Bybit cells",
    venue_overrides=(
        VenueOverride(
            venue_id="BYBIT",
            override_kind="api_rate_limit",
            duration_seconds=300,
            severity="5-min sustained 429",
        ),
    ),
    success_criteria=SuccessCriteria(
        pass_net_apr_pct_min=Decimal("0.90"),
        pass_with_warning_net_apr_pct_min=Decimal("0.80"),
        fail_alpha_apr_fraction_threshold=Decimal("0.50"),
        fail_risk_min_hf=Decimal("1.05"),
    ),
)

_SCN_C3 = BacktestScenario(
    id="SCN-C3-AAVE-PAUSE-RESERVE",
    category=ScenarioCategory.C,
    window=(date(2024, 1, 1), date(2024, 1, 1)),
    description=(
        "Aave V3 pauses one reserve (e.g. wstETH supply cap reached). "
        "Cell goes to PAUSED_NEW_OPENS; can still close/repay."
    ),
    cells_exercised="Cells supplying the paused reserve",
    venue_overrides=(
        VenueOverride(
            venue_id="AAVE_V3_ETHEREUM",
            override_kind="reserve_paused",
            duration_seconds=None,
            severity="wstETH supply cap reached",
        ),
    ),
    success_criteria=SuccessCriteria(
        pass_net_apr_pct_min=Decimal("0.90"),
        pass_with_warning_net_apr_pct_min=Decimal("0.80"),
        fail_alpha_apr_fraction_threshold=Decimal("0.50"),
        fail_risk_min_hf=Decimal("1.05"),
    ),
)

_SCN_C4 = BacktestScenario(
    id="SCN-C4-UNISWAP-V3-POOL-DRAIN",
    category=ScenarioCategory.C,
    window=(date(2024, 1, 1), date(2024, 1, 1)),
    description=(
        "Uniswap V3 wstETH/WETH pool drops to <$1M depth. Slippage gate triggers; fallback to Curve / Balancer."
    ),
    cells_exercised="All Family 1+2 wstETH cells using swap leg",
    venue_overrides=(
        VenueOverride(
            venue_id="UNISWAP_V3_WSTETH_WETH",
            override_kind="pool_depth_reduced",
            duration_seconds=None,
            severity="<$1M liquidity depth",
        ),
    ),
    success_criteria=SuccessCriteria(
        pass_net_apr_pct_min=Decimal("0.90"),
        pass_with_warning_net_apr_pct_min=Decimal("0.80"),
        fail_alpha_apr_fraction_threshold=Decimal("0.50"),
        fail_risk_min_hf=Decimal("1.05"),
    ),
)

_SCN_C5 = BacktestScenario(
    id="SCN-C5-USDC-TOPUP-TREASURY-EMPTY",
    category=ScenarioCategory.C,
    window=(date(2024, 1, 1), date(2024, 1, 1)),
    description=(
        "Treasury USDC balance reaches 0 just as margin top-up needed. "
        "Partial unwind fires to release margin; no liquidation events."
    ),
    cells_exercised="All Family 2 cells",
    venue_overrides=(
        VenueOverride(
            venue_id="TREASURY_USDC",
            override_kind="treasury_empty",
            duration_seconds=None,
            severity="zero USDC balance",
        ),
    ),
    success_criteria=SuccessCriteria(
        pass_net_apr_pct_min=Decimal("0.90"),
        pass_with_warning_net_apr_pct_min=Decimal("0.80"),
        fail_alpha_apr_fraction_threshold=Decimal("0.50"),
        fail_risk_min_hf=Decimal("1.05"),
    ),
)

# ---------------------------------------------------------------------------
# Exported registry
# ---------------------------------------------------------------------------

BACKTEST_SCENARIOS: tuple[BacktestScenario, ...] = (
    _SCN_A1,
    _SCN_A2,
    _SCN_A3,
    _SCN_A4,
    _SCN_B1,
    _SCN_B2,
    _SCN_B3,
    _SCN_B4,
    _SCN_B5,
    _SCN_C1,
    _SCN_C2,
    _SCN_C3,
    _SCN_C4,
    _SCN_C5,
)
"""14 canonical backtest scenarios (4 Category A + 5 Category B + 5 Category C)."""

BACKTEST_SCENARIOS_BY_ID: dict[str, BacktestScenario] = {s.id: s for s in BACKTEST_SCENARIOS}
"""Fast lookup by scenario ID."""

CATEGORY_A_SCENARIOS: tuple[BacktestScenario, ...] = tuple(
    s for s in BACKTEST_SCENARIOS if s.category == ScenarioCategory.A
)
CATEGORY_B_SCENARIOS: tuple[BacktestScenario, ...] = tuple(
    s for s in BACKTEST_SCENARIOS if s.category == ScenarioCategory.B
)
CATEGORY_C_SCENARIOS: tuple[BacktestScenario, ...] = tuple(
    s for s in BACKTEST_SCENARIOS if s.category == ScenarioCategory.C
)

__all__ = [
    "BACKTEST_SCENARIOS",
    "BACKTEST_SCENARIOS_BY_ID",
    "CATEGORY_A_SCENARIOS",
    "CATEGORY_B_SCENARIOS",
    "CATEGORY_C_SCENARIOS",
    "BacktestRunResult",
    "BacktestScenario",
    "FundingOverride",
    "OracleOverride",
    "ScenarioCategory",
    "ScenarioVerdict",
    "SuccessCriteria",
    "VenueOverride",
]

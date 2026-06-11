# Strategy Prospectus: Stat Arb Cross Sectional

> **Archetype ID**: `STAT_ARB_CROSS_SECTIONAL`  
> **Family**: `STAT_ARB_PAIRS`  
> **Status** (codex): design  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `STAT_ARB_PAIRS` | Primary venue categories: CEFI, DEFI, TRADFI

**[MACHINE-DERIVED]** Capability cells (from ARCHETYPE_CAPABILITY_REGISTRY):

| Venue Category | Instrument Type | Status  | Notes                                                                                 |
| -------------- | --------------- | ------- | ------------------------------------------------------------------------------------- |
| CEFI           | perp            | PARTIAL |                                                                                       |
| CEFI           | spot            | PARTIAL | Basket execution via sequential TRADE; batch-order path not tested.                   |
| DEFI           | perp            | PARTIAL |                                                                                       |
| DEFI           | spot            | BLOCKED | Multi-token atomic basket trade on DeFi is gas-prohibitive; needs specialised router. |
| TRADFI         | dated_future    | BLOCKED | Cross-sectional basket on CME requires multi-leg order capability not declared.       |
| TRADFI         | spot            | PARTIAL | Batch-order capability not declared for IBKR; basket of 50–500 legs.                  |

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Cross-sectional ranking across a universe of underlyings: score all N members on a signal (ML prediction, factor
exposure, or composite), long top-M / short bottom-M. Members rotate each rebalance period as rankings change. Joint
reasoning over the whole universe (this is what distinguishes it from running N independent ML directional strategies).

**[CODEX-DERIVED]** Execution semantics:

- Rebalance emits **multi-instrument TRADE set** — potentially dozens or hundreds of target-state changes per rebalance
- Execution-service sequences per its policy (e.g., TWAP over N minutes, balanced entry/exit pacing)
- Pre-flight check against venue-account health for the combined trade set
- ATOMIC not feasible for hundreds of names; sequential execution with pacing

**[CODEX-DERIVED]** Configurable parameters:

````yaml
universe_ref: RUSSELL_1000 # versioned universe artifact
ranking_model_ref: EQUITY_CS_CATBOOST_V3 # cross-sectional ML model
feature_group_refs:
  - equity-fundamentals@v4
  - equity-momentum@v3
  - equity-vol-adjusted@v2
basket_size_long_pct: 0.10 # long top 10% (100 names on R1000)
basket_size_short_pct: 0.10 # short bottom 10%
weighting_scheme: RANK_WEIGHTED # or EQUAL_WEIGHT or CONFIDENCE_WEIGHTED
rebalance_cadence: DAILY
rebalance_threshold_pct: 0.20 # only rebalance if ≥20% of basket changed
notional_per_side_pct_equity: 0.50 # 50% gross long + 50% gross short = 100% gross; net ~
_...truncated. See codex archetype doc._

## 2. Universe & Execution

**[CODEX-DERIVED]** Venue universe (from doc frontmatter): BINANCE, CME, IBKR, OKX

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

**[CODEX-DERIVED]** Risk profile:

- Drawdowns: factor reversals (value/momentum regime change) cause sharp reversals
- Typical Sharpe: 0.8-2.0 for well-run cross-sectional
- Kill switches: factor-exposure limit breach, single-name concentration breach, model calibration failure

**[CODEX-DERIVED]** P&L attribution:

- **Cross-sectional spread P&L**: (top-basket return) - (bottom-basket return) net of commission
- **Factor attribution**: decompose returns into factor exposures (value, momentum, size, quality, vol)
- **Turnover cost**: rebalance-driven commission and slippage
- **Execution alpha**: vs benchmark fills

> **[MACHINE-DERIVED — FINDING F-CLASS: GAP]** No declared exposure-normalization model found for this archetype. Staked-vs-spot equivalence (e.g. stETH/ETH delta-adjusted exposure), base-currency-neutral views, and intra-leg netting rules are `not_registered` in any UAC registry. Gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md` — `AGENT P1: Exposure normalization location: staked-ETH vs ETH equivalence`.

## 4. Fund Flow

**[MACHINE-DERIVED]** Wallets and venues keyed by venue categories + TREASURY_SPLIT_POLICIES (DeFi 20/80, CeFi 0/100, Sports no-split). Staked-basis leg structure derived from archetype family + capability cells.

```mermaid
flowchart TD
    CLIENT["Client Capital"]
    TREASURY["Treasury Wallet\n20% AUM"]
    HOT["Hot/Trading Wallet\n80% AUM"]
    CLIENT --> TREASURY
    CLIENT --> HOT
    CEFI["CeFi Exchange\n(BINANCE / BYBIT / OKX)"]
    POSITION["Trading Position"]
    HOT --> CEFI
    CEFI --> POSITION
    POSITION -. PnL .-> HOT
````

## 5. Risk & Circuit Breakers

**[MACHINE-DERIVED]** KillSwitchReason set (from UAC `enums.KillSwitchReason`):

- `COINTEGRATION_BREAKDOWN`
- `DAILY_LOSS_BREACH`
- `DATA_STALE`
- `DISABLED`
- `GREEK_LIMIT_BREACH`
- `KILL_SWITCH_TRIGGERED`
- `MAX_DRAWDOWN_BREACH`
- `VENUE_UNAVAILABLE`

**[MACHINE-DERIVED]** RiskGateLayer placement (from UAC `enums.RiskGateLayer`):

- `EXECUTION_PRETRADE`: Execution service pre-trade validation (order sizing, notional caps)
- `RISK_PREFLIGHT`: Risk service pre-flight validation (per-instruction, before execution queue)
- `STRATEGY_SELF_CHECK`: Strategy checks pre-instruction emit (position/PnL/delta guards)
- `VENUE_SIDE`: Venue-side limits (margin checks, open-order limits — external)

**[CODEX-DERIVED]** Archetype-specific risk notes:

- Drawdowns: factor reversals (value/momentum regime change) cause sharp reversals
- Typical Sharpe: 0.8-2.0 for well-run cross-sectional
- Kill switches: factor-exposure limit breach, single-name concentration breach, model calibration failure

**[CODEX-DERIVED]** Configurable risk parameters (from config schema):

- `max_single_name_pct: 0.02 # no more than 2% equity in one name`

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

Metric set: `unified_trading_library.performance_metrics` defines the canonical metric surface (expected: Sharpe ratio, max drawdown, CAGR, Sortino, Calmar, win rate, avg trade PnL). Import was unavailable on this host.

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `434e5beffedf400905475c64ca77535e474bd5fb`
- `archetype_id`: `STAT_ARB_CROSS_SECTIONAL`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

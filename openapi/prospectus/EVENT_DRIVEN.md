# Strategy Prospectus: Event Driven

> **Archetype ID**: `EVENT_DRIVEN`  
> **Family**: `EVENT_DRIVEN`  
> **Status** (codex): design  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `EVENT_DRIVEN` | Primary venue categories: CEFI, DEFI, PREDICTION, SPORTS, TRADFI

**[MACHINE-DERIVED]** Capability cells (from ARCHETYPE_CAPABILITY_REGISTRY):

| Venue Category | Instrument Type | Status  | Notes                                                             |
| -------------- | --------------- | ------- | ----------------------------------------------------------------- |
| CEFI           | option          | PARTIAL | Event-straddle expression policy not declared.                    |
| CEFI           | perp            | PARTIAL | Same calendar gap.                                                |
| CEFI           | spot            | PARTIAL | External event calendar not declared in UAC (gap #5).             |
| DEFI           | lending         | PARTIAL | Protocol-governance calendar gap.                                 |
| DEFI           | perp            | PARTIAL | Governance-vote reactive path; adapter ready.                     |
| DEFI           | spot            | PARTIAL | Token unlock calendar source gap.                                 |
| DEFI           | staking         | PARTIAL | Slashing feed integration incomplete.                             |
| PREDICTION     | event_settled   | PARTIAL | Same news-feed gap.                                               |
| SPORTS         | event_settled   | PARTIAL | News-feed + lineup timing model not declared.                     |
| TRADFI         | dated_future    | PARTIAL | Event-type → instrument mapping not declared in execution_policy. |
| TRADFI         | option          | PARTIAL | Same as CeFi option.                                              |
| TRADFI         | spot            | PARTIAL | Earnings calendar source gap.                                     |

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Schedules positioning around known external events (FOMC, CPI, NFP, OPEC, earnings, EIA). Consumes consensus forecast +
realized release data, computes surprise, emits directional trades in targeted instruments, then flattens at a
configured post-event window close.

**[CODEX-DERIVED]** Execution semantics:

- `TRADE` actions per instrument with target_position_units
- Urgency HIGH or EMERGENCY around event release (fast fills needed)
- MARKET or AGGRESSIVE_LIMIT algos typical
- Post-event flatten: urgency HIGH, market orders

**[CODEX-DERIVED]** Configurable parameters:

````yaml
event_calendar_ref: macro-events-q4-2026@v2
consensus_feed_refs:
  - bloomberg-econ-consensus@v1
  - tradingeconomics-consensus@v1
monitored_events:
  - FOMC_RATE_DECISION
  - US_CPI_YOY
  - US_NFP
direction_model_ref: TRADFI_MACRO_CRYPTO_direction_GBM_90d_V2
pre_event_minutes: 10
event_window_minutes: 30
exit_after_minutes: 45
min_surprise_sigma: 1.5
max_notional_per_event_usd: 500_000
event_size_multiplier_fomc: 2.0 # FOMC 2x standard size
volatility_exit_multiplier: 3.0 # exit if post-event vol > 3x pre-event
share_class: USDT
venues:
  - BINANCE
  - HYPERLIQUID
instruments_eligible
_...truncated. See codex archetype doc._

## 2. Universe & Execution

**[CODEX-DERIVED]** Venue universe (from doc frontmatter): BINANCE, CME, HYPERLIQUID, IBKR, OKX

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

**[CODEX-DERIVED]** Risk profile:

- Drawdowns: sharp on wrong-direction surprises (hedge with stop or exit-only-at-window)
- Typical Sharpe: event-specific; cumulative annualized depends on event frequency
- Kill switches: event release delayed > N min, realized vol post-event > pre × 5, simultaneous unexpected event

**[CODEX-DERIVED]** P&L attribution:

- **Event-window P&L**: entry → exit within window
- **Pre-event positioning P&L**: separate accounting for early-entry positions
- **Execution alpha**: vs benchmark (fill at release_ts price)
- **Attribution by event type**: rollup per (event_type, surprise_bucket) to understand which events are most profitable

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

- Drawdowns: sharp on wrong-direction surprises (hedge with stop or exit-only-at-window)
- Typical Sharpe: event-specific; cumulative annualized depends on event frequency
- Kill switches: event release delayed > N min, realized vol post-event > pre × 5, simultaneous unexpected event

**[CODEX-DERIVED]** Configurable risk parameters (from config schema):

- `max_notional_per_event_usd: 500_000`
- `min_surprise_sigma: 1.5`

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

Metric set: `unified_trading_library.performance_metrics` defines the canonical metric surface (expected: Sharpe ratio, max drawdown, CAGR, Sortino, Calmar, win rate, avg trade PnL). Import was unavailable on this host.

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `434e5beffedf400905475c64ca77535e474bd5fb`
- `archetype_id`: `EVENT_DRIVEN`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

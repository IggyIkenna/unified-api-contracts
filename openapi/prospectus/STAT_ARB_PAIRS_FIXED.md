# Strategy Prospectus: Stat Arb Pairs Fixed

> **Archetype ID**: `STAT_ARB_PAIRS_FIXED`  
> **Family**: `STAT_ARB_PAIRS`  
> **Status** (codex): design  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `STAT_ARB_PAIRS` | Primary venue categories: CEFI, DEFI, TRADFI

**[MACHINE-DERIVED]** Capability cells (from ARCHETYPE_CAPABILITY_REGISTRY):

| Venue Category | Instrument Type | Status    | Notes                                                                                                                   |
| -------------- | --------------- | --------- | ----------------------------------------------------------------------------------------------------------------------- |
| CEFI           | perp            | SUPPORTED |                                                                                                                         |
| CEFI           | spot            | SUPPORTED |                                                                                                                         |
| DEFI           | perp            | PARTIAL   |                                                                                                                         |
| DEFI           | spot            | PARTIAL   | Price-feed liquidity concerns on thinner pairs.                                                                         |
| TRADFI         | dated_future    | PARTIAL   | Calendar / cross-product pairs; roll service required (BL-10).                                                          |
| TRADFI         | spot            | PARTIAL   | Pair pre-declaration config path fine; no batch-tested instances. Treasury ETFs (TLT/IEF/SHY) are spot equities on IBKR |

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Trades a pre-determined, cointegration-tested (or historical-beta-stable) pair of underlyings. When the spread deviates
from its historical mean by a z-score threshold, enter long underperformer + short outperformer. Close when spread
reverts.

**[CODEX-DERIVED]** Execution semantics:

- Both legs entered/exited as ATOMIC (same venue) or LEADER_HEDGE (different venues)
- Hedge ratio updates periodically; re-emit reconciliation if ratio drift > threshold

**[CODEX-DERIVED]** Configurable parameters:

````yaml
pair_instruments:
  long_candidate: "IBKR:EQUITY:GOOG"
  short_candidate: "IBKR:EQUITY:META"
hedge_ratio_model: KALMAN # or OLS_ROLLING, COINTEGRATION_VECTOR
hedge_ratio_window_days: 90
z_score_window_days: 60
entry_z_score: 2.0
exit_z_score: 0.3
stop_loss_z_score: 3.5
cointegration_pvalue_max: 0.10
max_hold_days: 30
half_life_max_days: 15 # skip if OU half-life too slow
notional_allocation_usd: 500_000 # per pair
share_class: USD
venues: [IBKR]
execution_policy_ref: tradfi-paired-execution-v2 # leader-hedge or atomic

## 2. Universe & Execution

**[CODEX-DERIVED]** Venue universe (from doc frontmatter): BINANCE, CME, DERIBIT, IBKR, OKX

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

**[CODEX-DERIVED]** Risk profile:

- Drawdowns: spread-risk (relationship breaks) — can be severe if cointegration breaks (M&A, index rebalance, regime
  shift)
- Typical Sharpe: 1.0-2.5 for well-run stat arb
- Kill switches: cointegration pvalue breach, one-leg liquidity collapse, extreme z-score without reversion

**[CODEX-DERIVED]** P&L attribution:

- **Spread P&L**: (entry_z × σ_spread) × notional captured on reversion
- **Leg-by-leg P&L**: attribution to long leg and short leg separately for interpretation
- **Hedge ratio drift cost**: when Kalman updates, small rebalance trades incur cost
- **Execution alpha**: per fill

> **[MACHINE-DERIVED — FINDING F-CLASS: GAP]** No declared exposure-normalization model found for this archetype. Staked-vs-spot equivalence (e.g. stETH/ETH delta-adjusted exposure), base-currency-neutral views, and intra-leg netting rules are `not_registered` in any UAC registry. Gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md` — `AGENT P1: Exposure normalization location: staked-ETH vs ETH equivalence`.

## Leg Structure

**[GAP — no leg structure]** This archetype has no entry in `ARCHETYPE_LEG_STRUCTURES` yet, so its structural per-leg restrictions (roles, per-leg instrument types, per-leg venue eligibility, conditional constraints) are not modelled — only the flat `(asset_group, instrument_type)` capability cells above apply. Tracked as a leg-truth gap (F22).

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

- Drawdowns: spread-risk (relationship breaks) — can be severe if cointegration breaks (M&A, index rebalance, regime
  shift)
- Typical Sharpe: 1.0-2.5 for well-run stat arb
- Kill switches: cointegration pvalue breach, one-leg liquidity collapse, extreme z-score without reversion

**[CODEX-DERIVED]** Configurable risk parameters (from config schema):

- `max_hold_days: 30`
- `stop_loss_z_score: 3.5`

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

When backtest results are available, the following metric set will be reported (from `unified_trading_library.performance_metrics`):

- `DAYS_PER_YEAR`

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `c17a6be5b2bbbd7bb306468fcf10c90e6ed4007d`
- `archetype_id`: `STAT_ARB_PAIRS_FIXED`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

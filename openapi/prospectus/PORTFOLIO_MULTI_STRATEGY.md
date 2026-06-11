# Strategy Prospectus: Portfolio Multi Strategy

> **Archetype ID**: `PORTFOLIO_MULTI_STRATEGY`  
> **Family**: `PORTFOLIO`  
> **Status** (codex): design  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `PORTFOLIO` | Primary venue categories: not registered

**[MACHINE-DERIVED]** Capability cells: `not_registered` — archetype not in ARCHETYPE_CAPABILITY_REGISTRY

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Equal-weighted (or operator-fixed-weight) multi-strategy sleeve. Allocates equity across N child strategy instances
spanning multiple families (e.g. ML Directional + Carry + Vol Trading) with operator-mandated weights. Rebalances on a
fixed cadence; within a rebalance window the weights are held constant.

This is the simplest Portfolio archetype — the allocation rule is static: weights are set in config and only change when
the operator updates the config. The value-add versus the Portfolio Allocator service's FIXED allocator is that this
archetype is itself a strategy instance (receives equity, is risk-gated, can be itself allocated-to by a higher
allocator) enabling **nested portfolio construction**.

**[CODEX-DERIVED]** Execution semantics:

- Emits `AllocationDirective` events only (no `TRADE` instructions).
- No kill-switch at the sleeve level triggers child CLOSE_ALL — each child has its own kill-switch.
- Sleeve-level kill-switch suspends re-emission of new directives; existing child allocations wind down naturally.
- `MANUAL` cadence requires an explicit operator `RebalanceTrigger` event.

**[CODEX-DERIVED]** Configurable parameters:

````yaml
archetype: PORTFOLIO_MULTI_STRATEGY
child_strategy_ids:
  - "ML_DIRECTIONAL_CONTINUOUS@hyperliquid-btc-5m-usdt-prod"
  - "CARRY_BASIS_PERP@uniswap-hyperliquid-eth-usdt-prod"
  - "STAT_ARB_PAIRS_FIXED@ibkr-goog-meta-daily-usd-prod"

child_weights: # must sum to 1.0; indexed same order as child_strategy_ids
  - 0.40
  - 0.35
  - 0.25

rebalance_cadence: DAILY # or WEEKLY | MONTHLY | MANUAL
rebalance_threshold: 0.05 # drift fraction before intra-cadence rebalance fires (0.05 = 5%)
min_active_fraction: 0.5 # if fewer than 50% of children active, suspend allocation + alert
cash_buffer_pct:
_...truncated. See codex archetype doc._

## 2. Universe & Execution

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

> **[MACHINE-DERIVED — FINDING F-CLASS: GAP]** No declared exposure-normalization model found for this archetype. Staked-vs-spot equivalence (e.g. stETH/ETH delta-adjusted exposure), base-currency-neutral views, and intra-leg netting rules are `not_registered` in any UAC registry. Gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md` — `AGENT P1: Exposure normalization location: staked-ETH vs ETH equivalence`.

## 4. Fund Flow

**[MACHINE-DERIVED]** Wallets and venues keyed by venue categories + TREASURY_SPLIT_POLICIES (DeFi 20/80, CeFi 0/100, Sports no-split). Staked-basis leg structure derived from archetype family + capability cells.

```mermaid
flowchart TD
    CLIENT["Client Capital"]
    TREASURY["Treasury Wallet\n0% AUM"]
    HOT["Hot/Trading Wallet\n100% AUM"]
    CLIENT --> TREASURY
    CLIENT --> HOT
    VENUE["Trading Venue"]
    HOT --> VENUE
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

**[CODEX-DERIVED]** Configurable risk parameters (from config schema):

- `min_active_fraction: 0.5 # if fewer than 50% of children active, suspend allocation + alert`

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

Metric set: `unified_trading_library.performance_metrics` defines the canonical metric surface (expected: Sharpe ratio, max drawdown, CAGR, Sortino, Calmar, win rate, avg trade PnL). Import was unavailable on this host.

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `434e5beffedf400905475c64ca77535e474bd5fb`
- `archetype_id`: `PORTFOLIO_MULTI_STRATEGY`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

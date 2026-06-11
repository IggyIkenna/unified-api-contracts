# Strategy Prospectus: Vol Carry

> **Archetype ID**: `VOL_CARRY`  
> **Family**: `VOL_TRADING`  
> **Status** (codex): design  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `VOL_TRADING` | Primary venue categories: not registered

**[MACHINE-DERIVED]** Capability cells: `not_registered` — archetype not in ARCHETYPE_CAPABILITY_REGISTRY

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Harvests the persistent IV-over-RV premium at short tenors by selling options and collecting theta decay. The structural
alpha is that implied vol at 1-4 week tenors consistently prices in more realised-vol premium than materialises on
average. Delta-hedge the short-options book via the underlying perp/future to isolate the vega/theta P&L from
directional exposure.

**Core P&L equation (annualised, USDT):**

```
carry_pnl = (IV² − RV²) × vega_notional / 2   (variance-based vol carry)
theta_pnl = theta_daily × hold_days
delta_hedge_cost ≈ gamma × sigma² × dt / 2     (cost to hedge realised moves)
net ≈ carry_pnl + theta_pnl − delta_hedge_cost − fees
```

**[CODEX-DERIVED]** Execution semantics:

- `ATOMIC` multi-leg TRADE for option entry (straddle / strangle / iron condor)
- `TRADE` for delta hedge on underlying (perp or future)
- `ATOMIC` roll at expiry: close expiring legs + open next-expiry legs in one instruction
- Never enter with only one leg open when the other fill fails — abort ATOMIC on partial fill

**[CODEX-DERIVED]** Configurable parameters:

````yaml
underlying: BTC
venue: DERIBIT
surface_model_ref: svi-btc-v3
target_dte_entry: 14 # target DTE at entry (7-21 range)
roll_before_expiry_dte: 3 # roll to next expiry at ≤3 DTE
min_carry_threshold_vp: 3.0 # minimum (IV − RV_14d) in vol points to enter
expression: straddle # straddle | strangle | iron_condor | short_put_spread
strangle_delta_target: 0.20 # for strangle: target option delta per wing (20d)
max_vega_notional_usd: 50_000
delta_hedge_band_pct: 0.05 # rehedge when |portfolio_delta| > 5% of vega_notional
hedge_venue: DERIBIT
hedge_instrument: "DERIBIT:PERPETUAL:BTC-PERPETUAL"
ta
_...truncated. See codex archetype doc._

## 2. Universe & Execution

**[CODEX-DERIVED]** Venue universe (from doc frontmatter): CBOE, DERIBIT, OKX_OPTIONS

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

**[CODEX-DERIVED]** Risk profile:

- Primary risk: short-gamma blowout on vol spike (BTC ±20%+ in hours can exceed stop)
- Typical Sharpe: 1.5-2.5 in low-IV regimes; negative tail on sudden vol events
- Kill switches: RV > iv_stop_rv_multiple × IV; vega loss > stop_loss_vega_pct; venue outage
- Regime sensitivity: do NOT run during known high-vol events (FOMC, major protocol hacks, ETF approvals)

**[CODEX-DERIVED]** P&L attribution:

- **Theta P&L**: time decay collected per day (positive for short-vol); largest component in stable regimes
- **Vega P&L**: loss when vol rises post-entry, gain when vol falls (short-vol is short-vega)
- **Gamma P&L**: cost of delta-hedging realised moves (negative for short-gamma)
- **Delta-hedge slippage**: taker spread on hedge TRADE
- **Execution alpha**: vs mid on option fills

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

**[CODEX-DERIVED]** Archetype-specific risk notes:

- Primary risk: short-gamma blowout on vol spike (BTC ±20%+ in hours can exceed stop)
- Typical Sharpe: 1.5-2.5 in low-IV regimes; negative tail on sudden vol events
- Kill switches: RV > iv_stop_rv_multiple × IV; vega loss > stop_loss_vega_pct; venue outage
- Regime sensitivity: do NOT run during known high-vol events (FOMC, major protocol hacks, ETF approvals)

**[CODEX-DERIVED]** Configurable risk parameters (from config schema):

- `max_vega_notional_usd: 50_000`
- `min_carry_threshold_vp: 3.0 # minimum (IV − RV_14d) in vol points to enter`
- `stop_loss_vega_pct: 0.75 # exit if vega loss > 75% of premium collected`

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

Metric set: `unified_trading_library.performance_metrics` defines the canonical metric surface (expected: Sharpe ratio, max drawdown, CAGR, Sortino, Calmar, win rate, avg trade PnL). Import was unavailable on this host.

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `434e5beffedf400905475c64ca77535e474bd5fb`
- `archetype_id`: `VOL_CARRY`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

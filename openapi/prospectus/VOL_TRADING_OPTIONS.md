# Strategy Prospectus: Vol Trading Options

> **Archetype ID**: `VOL_TRADING_OPTIONS`  
> **Family**: `VOL_TRADING`  
> **Status** (codex): design  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `VOL_TRADING` | Primary venue categories: CEFI, DEFI, TRADFI

**[MACHINE-DERIVED]** Capability cells (from ARCHETYPE_CAPABILITY_REGISTRY):

| Venue Category | Instrument Type | Status    | Notes                                                     |
| -------------- | --------------- | --------- | --------------------------------------------------------- |
| CEFI           | option          | SUPPORTED | Full Deribit surface support; multi-leg ATOMIC supported. |
| DEFI           | option          | BLOCKED   | No supported DeFi options venue (Lyra / Dopex archived).  |
| TRADFI         | option          | PARTIAL   | CME options-on-futures not declared.                      |

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Expresses a directional view on a vol metric (IV/RV divergence, skew, term structure, soft surface residuals) through a
delta-hedged options position. P&L comes from vega, gamma, and theta — not delta. Statistical, not risk-free.

**[CODEX-DERIVED]** Execution semantics:

- `ATOMIC` multi-leg orders on options venue (Deribit supports multi-leg structures)
- `TRADE` for delta hedge on underlying
- Roll at expiry: ATOMIC (close expiring + open next-expiry)

**[CODEX-DERIVED]** Configurable parameters:

````yaml
underlying: BTC
venue: DERIBIT
surface_model_ref: svi-btc-v3 # versioned surface model
vol_edge_method: IV_RV_DIVERGENCE # or SKEW, TERM, SOFT_RESIDUAL
iv_rv_divergence_threshold: 0.10 # 10% (IV 50%, RV 40% → trade)
min_days_to_expiry: 7
max_days_to_expiry: 45
max_vega_notional_usd: 75_000
max_gamma_notional_usd: 15_000
delta_hedge_band_pct: 0.05 # rehedge when |delta| > 5% of vega
hedge_venue: DERIBIT # hedge on same venue usually
hedge_instrument: "DERIBIT:PERPETUAL:BTC-PERPETUAL"
time_decay_exit_dte: 3
take_profit_vega_pct: 0.25 # realize at 25% vega-P&L gain
stop_loss_vega_pct: 0.4
_...truncated. See codex archetype doc._

## 2. Universe & Execution

**[CODEX-DERIVED]** Venue universe (from doc frontmatter): CBOE, DERIBIT, OKX_OPTIONS

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

**[CODEX-DERIVED]** Risk profile:

- Drawdowns: can be sharp on vol regime change (short-vol blown up on VIX spike)
- Typical Sharpe: 1.0-2.5; short-vol regimes 2+ but tail-risky
- Kill switches: vol spike > N × regime, greeks breach, IV > configured ceiling (regime disruption)

**[CODEX-DERIVED]** P&L attribution:

- **Vega P&L**: vol movement × vega × days held
- **Gamma P&L**: realized vol captured via delta rehedges (gamma scalping positive for long-vol)
- **Theta P&L**: time decay (negative for long-vol, positive for short-vol)
- **Delta-hedge slippage**: cost of rehedging (ideally zero at true vol; >0 in practice)
- **Execution alpha**: per leg

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

- Drawdowns: can be sharp on vol regime change (short-vol blown up on VIX spike)
- Typical Sharpe: 1.0-2.5; short-vol regimes 2+ but tail-risky
- Kill switches: vol spike > N × regime, greeks breach, IV > configured ceiling (regime disruption)

**[CODEX-DERIVED]** Configurable risk parameters (from config schema):

- `max_days_to_expiry: 45`
- `max_gamma_notional_usd: 15_000`
- `max_vega_notional_usd: 75_000`
- `min_days_to_expiry: 7`
- `stop_loss_vega_pct: 0.40 # stop at 40% vega-P&L loss`

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

Metric set: `unified_trading_library.performance_metrics` defines the canonical metric surface (expected: Sharpe ratio, max drawdown, CAGR, Sortino, Calmar, win rate, avg trade PnL). Import was unavailable on this host.

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `434e5beffedf400905475c64ca77535e474bd5fb`
- `archetype_id`: `VOL_TRADING_OPTIONS`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

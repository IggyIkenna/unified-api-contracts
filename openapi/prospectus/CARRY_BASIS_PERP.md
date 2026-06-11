# Strategy Prospectus: Carry Basis Perp

> **Archetype ID**: `CARRY_BASIS_PERP`  
> **Family**: `CARRY_AND_YIELD`  
> **Status** (codex): design  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `CARRY_AND_YIELD` | Primary venue categories: CEFI, DEFI

**[MACHINE-DERIVED]** Capability cells (from ARCHETYPE_CAPABILITY_REGISTRY):

| Venue Category | Instrument Type | Status    | Notes                                                                     |
| -------------- | --------------- | --------- | ------------------------------------------------------------------------- |
| CEFI           | perp            | SUPPORTED | Single-venue netted (most capital-efficient) or cross-venue LEADER_HEDGE. |
| DEFI           | perp            | SUPPORTED | Same-chain SUPPORTED; cross-chain PARTIAL (bridge latency).               |

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Long spot + short perpetual future. Captures funding rate (paid by perp longs to perp shorts when perp > spot) while
staying delta-neutral. Position rebalanced when funding rate drops below threshold or moves to another venue.

**[CODEX-DERIVED]** Execution semantics:

- Entry: ATOMIC if spot+perp on same venue (Binance batch API); LEADER_HEDGE otherwise
- Exit: same
- Funding collection: passive; PBMS tracks funding accrual per position

### LegController integration

The 2-leg paired entry/exit is the **logical** flow. Mechanically, `LegController.update(slot, tick)` resolves the spot
(leader) and perp (hedge) legs from the `ExecutionPlanner`'s `PairedLegPlan`. Mode selection (ATOMIC vs LEADER_HEDGE) is
derived at preflight from `venue_accepts_batch_orders(venue)`.

**Code-backport status:** DEFERRED — `carry_and_yield/carry_basis_perp.py` still wires legs hand-built. Backport tracked
in `defi_recursive_borrow_archetypes_2026_05_10.md` factory-wiring phase. Docs ship now per operator decision
2026-05-07.

**[CODEX-DERIVED]** Configurable parameters:

````yaml
spot_venue: UNISWAP_V3_ETHEREUM # or BINANCE for netted
spot_instrument: "UNISWAP_V3:ETH-USDC"
perp_venue: HYPERLIQUID
perp_instrument: "HYPERLIQUID:PERPETUAL:ETH-USD"
target_funding_rate_bps: 80 # 80 bps (8%) annualized minimum
exit_funding_rate_bps: 20 # exit when funding drops below 20 bps
delta_hedge_rebalance_pct: 2 # rebalance if delta > 2%
staking_method: fractional_kelly
max_allocated_equity_pct: 0.30
share_class: USDT
execution_policy_ref: cefi-defi-combined-v7
exploit_venue_netting: true # when spot + perp on same venue

## 2. Universe & Execution

**[CODEX-DERIVED]** Venue universe (from doc frontmatter): BINANCE, BYBIT, DERIBIT, DRIFT, HYPERLIQUID, JUPITER, KRAKEN, OKX, ORCA, RAYDIUM, UNISWAP_V3

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

**[CODEX-DERIVED]** Risk profile:

- Drawdowns: very low (delta-neutral); tail risks are funding reversal, spot/perp spread widening during stress
- Typical Sharpe: 1.5-3.5 for well-run basis (high thanks to low vol + consistent funding)
- Kill switches: funding flips negative beyond hold threshold, LST/spot depeg (if variant with LST), venue outage

**[CODEX-DERIVED]** P&L attribution:

- **Funding P&L**: funding_rate × notional × holding_period (earned)
- **Basis change P&L**: entry_basis - exit_basis (minor, tends to zero for perps)
- **Fees / slippage**: per-fill
- **Execution alpha**: vs benchmark

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

- Drawdowns: very low (delta-neutral); tail risks are funding reversal, spot/perp spread widening during stress
- Typical Sharpe: 1.5-3.5 for well-run basis (high thanks to low vol + consistent funding)
- Kill switches: funding flips negative beyond hold threshold, LST/spot depeg (if variant with LST), venue outage

**[CODEX-DERIVED]** Configurable risk parameters (from config schema):

- `max_allocated_equity_pct: 0.30`

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

Metric set: `unified_trading_library.performance_metrics` defines the canonical metric surface (expected: Sharpe ratio, max drawdown, CAGR, Sortino, Calmar, win rate, avg trade PnL). Import was unavailable on this host.

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `434e5beffedf400905475c64ca77535e474bd5fb`
- `archetype_id`: `CARRY_BASIS_PERP`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

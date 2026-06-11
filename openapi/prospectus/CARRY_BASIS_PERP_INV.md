# Strategy Prospectus: Carry Basis Perp Inv

> **Archetype ID**: `CARRY_BASIS_PERP_INV`  
> **Family**: `CARRY_AND_YIELD`  
> **Status** (codex): design  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `CARRY_AND_YIELD` | Primary venue categories: DEFI

**[MACHINE-DERIVED]** Capability cells (from ARCHETYPE_CAPABILITY_REGISTRY):

| Venue Category | Instrument Type | Status    | Notes                                                                                                                    |
| -------------- | --------------- | --------- | ------------------------------------------------------------------------------------------------------------------------ |
| DEFI           | staking         | SUPPORTED | Family 2 recursive borrow: lend ETH/stETH on Aave (USDC margin), short USDC-margined perp on Hyperliquid/Bybit to neutra |

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Family 2 recursive supply-borrow loop: supply ETH LST as collateral on a lending protocol (Aave V3 / Morpho), borrow
ETH, swap to LST, re-supply — amplifying the staking spread (`R_lend`). A USDC-margined ETH perp short is placed on a
CeFi venue sized to neutralise the residual spot-ETH delta the recursion carries.

**Yield = `R_lend + R_fund + R_usdc − gas − slippage`** where:

- `R_lend` = amplified staking spread (supply LST yield minus borrow ETH rate), levered by recursion depth
- `R_fund` = perp funding capture (positive when longs pay shorts)
- `R_usdc` = USDC margin yield at perp venue (near-zero for Hyperliquid May-23 baseline)

The "INV" suffix denotes that the on-chain long-equivalent is realised via recursive borrow leverage — the inverse of
`CARRY_BASIS_PERP`'s direct spot purchase. Both achieve a delta-neutral long-spot + short-perp structure; this archetype
amplifies `R_lend` via recursion while `CARRY_BASIS_PERP` leaves the spot unlevered.

**[CODEX-DERIVED]** Execution semantics:

Two-phase opening per `LegController.update(slot, tick, execution_mode=LEADER_HEDGE)`:

1. Recursive on-chain bundle (leader): STAKE → TRANSFER → LEND → BORROW × N (flash mode or sequential multicall)
2. CeFi perp short (hedge): fires after on-chain finalization within `hedge_deadline_ms`

`CLOSE_LEADER_IF_HEDGE_FAILS` triggers flash-unwind of the on-chain loop if the perp fails.

**[CODEX-DERIVED]** Configurable parameters:

````yaml

## 2. Universe & Execution

**[CODEX-DERIVED]** Venue universe (from doc frontmatter): AAVE, BYBIT, HYPERLIQUID, MORPHO

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

**[CODEX-DERIVED]** Risk profile:

- **Delta**: 0 by construction (`E_actual` always hedged by perp short via PerpHedgeSizer)
- **Liquidation**: on-chain loop faces health-factor risk; kill-switch at `min_health_factor`
- **Funding flip**: perp funding going negative erodes net APR; degradation policy manages this
- **Bridge risk**: Hyperliquid 5-min withdrawal dispute window encoded in unwind timing budget
- **Smart contract**: Aave / Morpho exploit risk; mitigated by per-protocol position caps
- **Typical Sharpe**: 1.5–3.5 in +funding regime; degrades to 0.8–1.2 in neutral-funding regime

**[CODEX-DERIVED]** P&L attribution:

| Layer        | Income source            | Cost                     |
| ------------ | ------------------------ | ------------------------ |
| Lending loop | Amplified staking spread | Gas (4–12 rebalances/yr) |
| Perp short   | Funding APR (when +)     | Commission               |
| USDC margin  | Venue margin yield       | Near-zero May-23         |

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

- **Delta**: 0 by construction (`E_actual` always hedged by perp short via PerpHedgeSizer)
- **Liquidation**: on-chain loop faces health-factor risk; kill-switch at `min_health_factor`
- **Funding flip**: perp funding going negative erodes net APR; degradation policy manages this
- **Bridge risk**: Hyperliquid 5-min withdrawal dispute window encoded in unwind timing budget
- **Smart contract**: Aave / Morpho exploit risk; mitigated by per-protocol position caps
- **Typical Sharpe**: 1.5–3.5 in +
  _...truncated. See codex archetype doc._

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

Metric set: `unified_trading_library.performance_metrics` defines the canonical metric surface (expected: Sharpe ratio, max drawdown, CAGR, Sortino, Calmar, win rate, avg trade PnL). Import was unavailable on this host.

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `434e5beffedf400905475c64ca77535e474bd5fb`
- `archetype_id`: `CARRY_BASIS_PERP_INV`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

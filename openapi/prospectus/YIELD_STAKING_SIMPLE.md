# Strategy Prospectus: Yield Staking Simple

> **Archetype ID**: `YIELD_STAKING_SIMPLE`  
> **Family**: `CARRY_AND_YIELD`  
> **Status** (codex): design  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `CARRY_AND_YIELD` | Primary venue categories: DEFI

**[MACHINE-DERIVED]** Capability cells (from ARCHETYPE_CAPABILITY_REGISTRY):

| Venue Category | Instrument Type | Status    | Notes                                                                               |
| -------------- | --------------- | --------- | ----------------------------------------------------------------------------------- |
| DEFI           | staking         | SUPPORTED | Pure staking, no hedge. Ethereum (stETH / rETH / eETH) and Solana (JitoSOL / mSOL). |

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Pure staking: deposit native PoS asset (ETH, SOL, etc.) into liquid staking protocol to earn validator rewards. No basis
leg, no leverage, no directional view. Just held-to-earn-yield.

**[CODEX-DERIVED]** Execution semantics:

- `STAKE` action type for deposits
- `UNSTAKE` action type for withdrawals (or SWAP via DEX if exit_preference = DEX_SWAP)
- Passive between events

### LegController integration

`LegController.update(slot, tick, execution_mode=ATOMIC)` resolves a 1-leg STAKE or UNSTAKE action per equity-change
event. Exit via DEX_SWAP becomes a 2-leg SWAP→TRANSFER bundle (ATOMIC if same-DEX, LEADER_HEDGE otherwise).

**Code-backport status:** DEFERRED — `carry_and_yield/yield_staking_simple.py` still wires legs hand-built. Backport
tracked in `defi_recursive_borrow_archetypes_2026_05_10.md` factory-wiring phase. Docs ship now per operator decision
2026-05-07.

**[CODEX-DERIVED]** Configurable parameters:

````yaml
staking_protocol: LIDO # or ROCKET_POOL, JITO, MARINADE
asset: ETH # or SOL
share_class: ETH # typically same as underlying
exit_preference: DEX_SWAP # or PROTOCOL_WITHDRAWAL
max_allocated_pct: 1.0 # can hold 100% staked for pure yield strategies
execution_policy_ref: defi-direct-v2
rebalance_cadence_days: 30 # e.g., claim rewards + restake monthly

## 2. Universe & Execution

**[CODEX-DERIVED]** Venue universe (from doc frontmatter): ETHERFI, JITO, LIDO, MARINADE, ROCKET_POOL

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

**[CODEX-DERIVED]** Risk profile:

- Drawdowns: LST depeg (stETH depegged to ~0.94 in 2022; rare but real)
- Typical Sharpe: very high in nominal terms (low vol); tail risk is depeg
- Kill switches: depeg > threshold (e.g., 1%), slashing events on validators, protocol incident
- Depeg kill-switch default: **100 bps (1%)** absolute deviation between LST oracle price and redemption NAV;
  auto-unwind on breach. Tightened per-LST when volatility warrants (e.g. 50 bps on stETH post-2022).

**[CODEX-DERIVED]** P&L attribution:

- **Staking yield**: LST_balance_change × ETH_price (rebase model) OR LST_price × ETH_price (exchange rate model)
- **No execution alpha** (mostly passive deposit/withdrawal)

> **[MACHINE-DERIVED — FINDING F-CLASS: GAP]** No declared exposure-normalization model found for this archetype. Staked-vs-spot equivalence (e.g. stETH/ETH delta-adjusted exposure), base-currency-neutral views, and intra-leg netting rules are `not_registered` in any UAC registry. Gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md` — `AGENT P1: Exposure normalization location: staked-ETH vs ETH equivalence`.

## Leg Structure

**[MACHINE-DERIVED]** Structural legs from `ARCHETYPE_LEG_STRUCTURES` (F22 leg-truth SSOT) — the exhaustive per-leg restriction surface the flat capability cells cannot express. Execution coupling: `ATOMIC_ON_CHAIN`.

| Leg | Role | Required | Instrument types | Eligible venues |
|---|---|---|---|---|
| `stake` | `stake` | true | `staking` | `etherfi`, `jito`, `lido`, `marinade`, `rocketpool` |

## 4. Fund Flow

**[MACHINE-DERIVED]** Wallets and venues keyed by venue categories + TREASURY_SPLIT_POLICIES (DeFi 20/80, CeFi 0/100, Sports no-split). Staked-basis leg structure derived from archetype family + capability cells.

```mermaid
flowchart TD
    CLIENT["Client Capital"]
    TREASURY["Treasury Wallet\n20% AUM"]
    HOT["Hot/Trading Wallet\n80% AUM"]
    CLIENT --> TREASURY
    CLIENT --> HOT
    SPOT_DEX["Spot DEX\n(UNISWAP_V3 / JUPITER)"]
    STAKING["Staking Protocol\n(LIDO / JITO / MARINADE)"]
    LST["LST Asset\n(stETH / JitoSOL / mSOL)"]
    CEFI_VENUE["CeFi Perp Venue\n(DERIBIT / DRIFT / BYBIT)"]
    PERP_SHORT["Short Perp Position"]
    HOT --> SPOT_DEX
    SPOT_DEX --> STAKING
    STAKING --> LST
    LST --> CEFI_VENUE
    CEFI_VENUE --> PERP_SHORT
    PERP_SHORT -. funding yield .-> HOT
    LST -. staking yield .-> HOT
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

- Drawdowns: LST depeg (stETH depegged to ~0.94 in 2022; rare but real)
- Typical Sharpe: very high in nominal terms (low vol); tail risk is depeg
- Kill switches: depeg > threshold (e.g., 1%), slashing events on validators, protocol incident
- Depeg kill-switch default: **100 bps (1%)** absolute deviation between LST oracle price and redemption NAV;
  auto-unwind on breach. Tightened per-LST when volatility warrants (e.g. 50 bps on stETH post-2022).

**[CODEX-DERIVED]** Configurable risk parameters (from config schema):

- `max_allocated_pct: 1.0 # can hold 100% staked for pure yield strategies`

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

When backtest results are available, the following metric set will be reported (from `unified_trading_library.performance_metrics`):

- `DAYS_PER_YEAR`

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `c17a6be5b2bbbd7bb306468fcf10c90e6ed4007d`
- `archetype_id`: `YIELD_STAKING_SIMPLE`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

# Strategy Prospectus: Carry Staked Basis Dated

> **Archetype ID**: `CARRY_STAKED_BASIS_DATED`  
> **Family**: `CARRY_AND_YIELD`  
> **Status** (codex): design  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `CARRY_AND_YIELD` | Primary venue categories: CEFI, DEFI

**[MACHINE-DERIVED]** Capability cells (from ARCHETYPE_CAPABILITY_REGISTRY):

| Venue Category | Instrument Type | Status  | Notes                                                                                                                    |
| -------------- | --------------- | ------- | ------------------------------------------------------------------------------------------------------------------------ |
| CEFI           | dated_future    | PARTIAL | CeFi dated-future leg for staked-basis carry. Requires stETH as collateral at CeFi venue — only Deribit / Binance accept |
| DEFI           | staking         | PARTIAL | Dated-contract variant of CARRY_STAKED_BASIS. stETH margin (ETH-collateral); hedge leg is Deribit dated ETH future. Roll |

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Dated-contract variant of `CARRY_STAKED_BASIS`: stake ETH into an LST, transfer to the perp venue as cross-margin, SHORT
a **dated futures contract** (quarterly/monthly expiry) instead of a perpetual. Earns staking yield on the staked
principal during the hold period, PLUS the dated futures basis premium locked in at entry — which converts to P&L as the
contract converges to spot at expiry.

**vs `CARRY_STAKED_BASIS`**: replaces the perpetual hedge with a dated-expiry contract. The dated variant locks in the
basis premium at entry (guaranteed to zero out at expiry if held); the perp variant earns ongoing funding rate
(variable, can flip). Use `CARRY_STAKED_BASIS_DATED` when the dated basis premium exceeds expected perp funding over the
contract period and you prefer certainty of the basis over variability of funding.

**Combined yield** (USDC, annualised):

```
net_apy_bps = staking_apy_total_bps + (basis_at_entry_bps × 365 / days_to_expiry) − fees
```

**[CODEX-DERIVED]** Execution semantics:

`AtomicInstruction` with `execution_mode = LEADER_HEDGE` (same 4-leg flow as `CARRY_STAKED_BASIS`):

- **4-leg entry**: SWAP (leader) + STAKE + TRANSFER + TRADE (dated short)
- **Compensation policy**: `CLOSE_LEADER_IF_HEDGE_FAILS` — unwind SWAP + STAKE + TRANSFER if dated short fails

On expiry: execute exit automatically or roll to next quarter per `auto_roll_enabled`.

**Code-backport status:** DEFERRED — shares `staked_basis.py` engine via `ALLOWED_ARCHETYPES`; engine branches on
`archetype_id == CARRY_STAKED_BASIS_DATED` to read `dated_basis_bps` instead of `funding_rate_apy_bps` and set
`rollover_days_before_expiry` for expiry logic. Backport tracked in `defi_recursive_borrow_archetypes_2026_05_10.md`
factory-wiring phase.

**[CODEX-DERIVED]** Configurable parameters:

````yaml

## 2. Universe & Execution

**[CODEX-DERIVED]** Venue universe (from doc frontmatter): BYBIT, DERIBIT, DRIFT, ETHERFI, JITO, JUPITER, LIDO, UNISWAP_V3

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

**[CODEX-DERIVED]** Risk profile:

- **Delta**: 0 by construction (LST long ≡ dated short on the underlying)
- **Basis convergence risk**: dated basis can widen before converging — mark-to-market drawdown
- **Liquidation**: LST haircut breach at perp venue; same health-factor kill-switch as `CARRY_STAKED_BASIS`
- **Depeg risk**: stETH/JitoSOL discount-to-fair on secondary; same kill-switch as `CARRY_STAKED_BASIS`
- **Roll risk**: dated contracts expire; must roll or close 5 days before expiry to avoid delivery
- **No funding flip risk**: unlike perp variant, there is no funding rate component — basis is locked at entry
- Typica
_...truncated. See codex archetype doc._

**[CODEX-DERIVED]** P&L attribution:

| Leg                 | Income                           | Cost                | Source                         |
| ------------------- | -------------------------------- | ------------------- | ------------------------------ |
| Staked principal    | staking_apy_total_bps × notional | mint/burn fees      | `lst_rates` on-chain rate-diff |
| Dated short         | basis_at_entry_bps × days/365    | commission          | Deribit/Drift dated ticker     |
| LST → perp transfer | n/a
_...truncated. See codex archetype doc._

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

- **Delta**: 0 by construction (LST long ≡ dated short on the underlying)
- **Basis convergence risk**: dated basis can widen before converging — mark-to-market drawdown
- **Liquidation**: LST haircut breach at perp venue; same health-factor kill-switch as `CARRY_STAKED_BASIS`
- **Depeg risk**: stETH/JitoSOL discount-to-fair on secondary; same kill-switch as `CARRY_STAKED_BASIS`
- **Roll risk**: dated contracts expire; must roll or close 5 days before expiry to avoid delivery
- \*\*No funding flip
  _...truncated. See codex archetype doc._

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

Metric set: `unified_trading_library.performance_metrics` defines the canonical metric surface (expected: Sharpe ratio, max drawdown, CAGR, Sortino, Calmar, win rate, avg trade PnL). Import was unavailable on this host.

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `434e5beffedf400905475c64ca77535e474bd5fb`
- `archetype_id`: `CARRY_STAKED_BASIS_DATED`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

# Strategy Prospectus: Carry Basis Dated Inv

> **Archetype ID**: `CARRY_BASIS_DATED_INV`  
> **Family**: `CARRY_AND_YIELD`  
> **Status** (codex): design  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `CARRY_AND_YIELD` | Primary venue categories: CEFI, DEFI

**[MACHINE-DERIVED]** Capability cells (from ARCHETYPE_CAPABILITY_REGISTRY):

| Venue Category | Instrument Type | Status    | Notes                                                                                                                    |
| -------------- | --------------- | --------- | ------------------------------------------------------------------------------------------------------------------------ |
| CEFI           | dated_future    | SUPPORTED | Inverse of CARRY_BASIS_DATED: short the basis (lend USDC-margined perp, hold spot). Same cap/gates as CARRY_BASIS_DATED; |
| DEFI           | dated_future    | BLOCKED   | No DeFi dated-future venue available — mirrors CARRY_BASIS_DATED DeFi BLOCKED cell.                                      |

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Inverse of `CARRY_BASIS_DATED`: short dated future + long cash (or equivalent). Captures the futures-spot discount
(backwardation) as the spread converges to zero at expiry. The position profits when futures trade below spot — typical
in commodity supply-crunch regimes (oil/gas front-month premium) and crypto bear markets.

**Backwardation**: spot > future. Entry when
`basis_spread = (spot_price − future_price) / spot_price > min_entry_threshold`. P&L locked at entry; realised at
convergence (expiry or early exit).

**[CODEX-DERIVED]** Execution semantics:

- Both legs entered via ATOMIC (same venue) or LEADER_HEDGE (cross-venue)
- Exit symmetrically — buy back short future + release cash
- No roll needed if held to expiry (futures settle; cash released)
- If closed early: both legs closed simultaneously

### LegController integration

Same as `CARRY_BASIS_DATED` with direction inverted. `LegController.update(slot, tick)` reads `archetype_id` and sets
short leg = future, long leg = cash. ATOMIC on single-venue instruments; LEADER_HEDGE otherwise.

**Code-backport status:** DEFERRED — `carry_and_yield/basis_dated.py` still wires legs hand-built. Backport tracked in
`defi_recursive_borrow_archetypes_2026_05_10.md` factory-wiring phase.

**[CODEX-DERIVED]** Configurable parameters:

````yaml
spot_venue: CME # cash/spot leg venue
spot_instrument: "CME:SPOT:CL"
future_venue: CME
future_instrument: "CME:FUTURE:CL:20260920"
share_class: USD
min_entry_basis_bps: 50 # minimum spot premium (backwardation) after costs
exit_basis_bps: 10 # close when spread < 10 bps (near convergence)
max_allocated_equity_pct: 0.20 # 20% of equity per opportunity
rollover_days_before_expiry: 5
execution_policy_ref: tradfi-paired-basis-v2

## 2. Universe & Execution

**[CODEX-DERIVED]** Venue universe (from doc frontmatter): BYBIT, CME, DERIBIT, OKX

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

**[CODEX-DERIVED]** Risk profile:

- Drawdowns: low (delta-neutral); main risk is backwardation widening further before convergence
- Basis widening risk is asymmetric — commodity supply crunches can persist weeks before front-month premium collapses
- Typical Sharpe: 1.2–2.5 for well-run commodity backwardation basis (lower than contango due to spike risk)
- Kill switches: basis widens beyond `max_basis_bps`, venue outage, one-leg liquidity collapse

**[CODEX-DERIVED]** P&L attribution:

- **Basis convergence P&L**: locked-in spread × notional (captured at exit/expiry)
- **Carry cost of short future**: daily settlement P&L on the short position (mark-to-market roll)
- **Cash yield**: interest on the long cash leg (T-bill / money-market yield on un-deployed capital)
- **Commissions + execution alpha**: per-fill

> **[MACHINE-DERIVED — FINDING F-CLASS: GAP]** No declared exposure-normalization model found for this archetype. Staked-vs-spot equivalence (e.g. stETH/ETH delta-adjusted exposure), base-currency-neutral views, and intra-leg netting rules are `not_registered` in any UAC registry. Gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md` — `AGENT P1: Exposure normalization location: staked-ETH vs ETH equivalence`.

## Leg Structure

**[MACHINE-DERIVED]** Structural legs from `ARCHETYPE_LEG_STRUCTURES` (F22 leg-truth SSOT) — the exhaustive per-leg restriction surface the flat capability cells cannot express. Execution coupling: `LEADER_HEDGE`.

| Leg | Role | Required | Instrument types | Eligible venues |
|---|---|---|---|---|
| `future` | `future_long` | true | `dated_future` | `binance`, `cme`, `deribit`, `ice` |
| `spot` | `spot_short` | true | `spot` | `binance`, `coinbase`, `deribit`, `ibkr` |

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

- Drawdowns: low (delta-neutral); main risk is backwardation widening further before convergence
- Basis widening risk is asymmetric — commodity supply crunches can persist weeks before front-month premium collapses
- Typical Sharpe: 1.2–2.5 for well-run commodity backwardation basis (lower than contango due to spike risk)
- Kill switches: basis widens beyond `max_basis_bps`, venue outage, one-leg liquidity collapse

**[CODEX-DERIVED]** Configurable risk parameters (from config schema):

- `max_allocated_equity_pct: 0.20 # 20% of equity per opportunity`
- `min_entry_basis_bps: 50 # minimum spot premium (backwardation) after costs`

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

When backtest results are available, the following metric set will be reported (from `unified_trading_library.performance_metrics`):

- `DAYS_PER_YEAR`

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `c17a6be5b2bbbd7bb306468fcf10c90e6ed4007d`
- `archetype_id`: `CARRY_BASIS_DATED_INV`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

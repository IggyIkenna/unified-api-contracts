# Strategy Prospectus: Liquidation Capture

> **Archetype ID**: `LIQUIDATION_CAPTURE`  
> **Family**: `ARBITRAGE_STRUCTURAL`  
> **Status** (codex): design  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `ARBITRAGE_STRUCTURAL` | Primary venue categories: CEFI, DEFI

**[MACHINE-DERIVED]** Capability cells (from ARCHETYPE_CAPABILITY_REGISTRY):

| Venue Category | Instrument Type | Status    | Notes                                                                              |
| -------------- | --------------- | --------- | ---------------------------------------------------------------------------------- |
| CEFI           | perp            | PARTIAL   | Hyperliquid liquidation feed; edge limited to bid-ladder placement near liq price. |
| DEFI           | lending         | SUPPORTED | Flash-loan receiver contract required per-chain. Aave V3 + Kamino primary.         |
| DEFI           | perp            | PARTIAL   | GMX perp liquidations have different economics than lending liquidations.          |

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Monitors under-collateralized lending positions on DeFi protocols and executes liquidation calls to capture the
protocol's paid bonus (typically 5-10% of seized collateral). Zero directional risk; alpha is the structural bonus paid
by the lending protocol for cleaning up unhealthy positions.

**[CODEX-DERIVED]** Execution semantics:

- Single `ATOMIC` instruction per opportunity
- Flash-loan embedded within the bundle
- Submission via Flashbots (Ethereum + Base) / equivalent bundlers (other chains)
- Reverts atomically if profit falls short mid-bundle

### LegController integration

`LegController.update(slot, tick, execution_mode=ATOMIC)` resolves a single bundled flash-loan→liquidate→swap-to-debt
sequence per opportunity. Uses `FlashLoanReceiver.sol` (passthrough — not `RecursiveLeverageReceiver.sol`); see
[`../../04-architecture/flash-loan-receiver.md`](../../../04-architecture/flash-loan-receiver.md) for receiver details.

**Code-backport status:** DEFERRED — `arbitrage/liquidation_capture.py` still builds bundles inline. Backport tracked in
`defi_recursive_borrow_archetypes_2026_05_10.md` factory-wiring phase. Doc
_...truncated (844 chars total). See codex archetype doc for full detail._

**[CODEX-DERIVED]** Configurable parameters:

````yaml
protocols_eligible:
  - AAVE_V3_ETHEREUM
  - AAVE_V3_ARBITRUM
  - AAVE_V3_OPTIMISM
  - AAVE_V3_POLYGON
  - AAVE_V3_AVALANCHE
  - AAVE_V3_BASE
min_profit_usd: 50 # skip opps < $50 profit
max_debt_repay_usd: 1_000_000 # flash-loan cap per opp
priority_fee_strategy: AGGRESSIVE # win the gas auction
submission_mode: FLASHBOTS_BUNDLE # prevent front-run
dex_slippage_tolerance: 0.005 # 0.5%
execution_policy_ref: defi-liquidation-v3
share_class: USD

## 2. Universe & Execution

**[CODEX-DERIVED]** Venue universe (from doc frontmatter): AAVE_V3, COMPOUND_V3, EULER, KAMINO, MORPHO

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

**[CODEX-DERIVED]** Risk profile:

- Drawdowns: none from successful opps; only cost from failed attempts (wasted gas, failed bundle inclusion)
- Typical Sharpe: high on a per-opp basis; opp frequency is the constraint on annualized returns
- Kill switches: protocol incident (oracle failure, governance pause), abnormal bundle failure rate, gas price spike
  making opps unprofitable

**[CODEX-DERIVED]** P&L attribution:

- **Gross liquidation profit**: seized_collateral_value − debt_repaid
- **Flash-loan fee**: minor (e.g., Aave 0.05%)
- **Gas**: deducted
- **DEX slippage on collateral sale**: deducted
- **Net P&L**: what's left after all above

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

- Drawdowns: none from successful opps; only cost from failed attempts (wasted gas, failed bundle inclusion)
- Typical Sharpe: high on a per-opp basis; opp frequency is the constraint on annualized returns
- Kill switches: protocol incident (oracle failure, governance pause), abnormal bundle failure rate, gas price spike
  making opps unprofitable

**[CODEX-DERIVED]** Configurable risk parameters (from config schema):

- `max_debt_repay_usd: 1_000_000 # flash-loan cap per opp`
- `min_profit_usd: 50 # skip opps < $50 profit`

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

When backtest results are available, the following metric set will be reported (from `unified_trading_library.performance_metrics`):

- `DAYS_PER_YEAR`

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `c17a6be5b2bbbd7bb306468fcf10c90e6ed4007d`
- `archetype_id`: `LIQUIDATION_CAPTURE`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

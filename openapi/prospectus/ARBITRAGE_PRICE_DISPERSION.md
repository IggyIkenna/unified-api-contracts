# Strategy Prospectus: Arbitrage Price Dispersion

> **Archetype ID**: `ARBITRAGE_PRICE_DISPERSION`  
> **Family**: `ARBITRAGE_STRUCTURAL`  
> **Status** (codex): code-shipped  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `ARBITRAGE_STRUCTURAL` | Primary venue categories: CEFI, DEFI, PREDICTION, SPORTS, TRADFI

**[MACHINE-DERIVED]** Capability cells (from ARCHETYPE_CAPABILITY_REGISTRY):

| Venue Category | Instrument Type | Status    | Notes                                                                      |
| -------------- | --------------- | --------- | -------------------------------------------------------------------------- |
| CEFI           | option          | PARTIAL   | vol_arb not a separate capability; multi-leg vol-arb algo pending.         |
| CEFI           | perp            | PARTIAL   | UAC lacks funding_arb flag distinct from price-arb (gap #2).               |
| CEFI           | spot            | SUPPORTED |                                                                            |
| DEFI           | lp              | PARTIAL   | Flash-loan receiver per-chain registry missing from UAC (gap #3).          |
| DEFI           | option          | BLOCKED   | No supported DeFi options venue.                                           |
| DEFI           | perp            | SUPPORTED |                                                                            |
| DEFI           | spot            | SUPPORTED |                                                                            |
| PREDICTION     | event_settled   | SUPPORTED | Cross-category arb (Polymarket ↔ Unity / Betfair for correlated markets). |
| SPORTS         | event_settled   | SUPPORTED | Unity single-wallet makes cross-book arb near-atomic.                      |
| TRADFI         | dated_future    | PARTIAL   | Cross-product routing policy not declared in UAC (gap #10).                |
| TRADFI         | option          | PARTIAL   | Same-surface no-arb (butterfly / calendar / parity) on CBOE via IBKR.      |
| TRADFI         | spot            | PARTIAL   | IBKR smart-router absorbs most intra-TradFi spot arb.                      |

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Detects price dispersion between venues on the same (or equivalent) instrument and executes a paired position that locks
in the spread net of costs. Covers:

- Cross-CEX spot / perp arb
- Cross-DEX arb (same chain, flash-loan optionally)
- Sports cross-book arb (via Unity prime broker — single wallet)
- Cross-category arb (Polymarket ↔ Betfair/Unity for correlated markets)
- Cross-venue vol arb (same option quoted at different IVs on Deribit vs OKX options)
- Within-venue no-arb violations (butterfly / calendar / put-call parity)
- Funding-rate dispersion arb (net position sized to capture funding differential)

**[CODEX-DERIVED]** Execution semantics:

- `ATOMIC` instruction type for bundled legs
- `TRADE` instructions sequenced for LEADER_HEDGE
- Execution-service enforces leader-hedge timing via execution_policy_ref
- Mid-execution abort if conditions breach (unwind whichever leg filled)

### LegController integration

Both ATOMIC and LEADER_HEDGE modes flow through `LegController.update(slot, tick)`. The controller reads the
`DispersionOpportunity` from `features-onchain` and maps it to the leg sequence:

- **ATOMIC mode**: buy leg + sell leg emitted as a single bundled `AtomicInstruction` with `execution_mode=ATOMIC`.
- **LEADER_HEDGE mode**: leader (larger/safer venue) fires first; `LegController.on_leader_fill()` triggers the hedge
  leg within `hedge_deadline_ms`; `CLOSE_LEADER_IF_HEDGE_FAILS` compensation on deadline breach.

\*\*C
_...truncated (1030 chars total). See codex archetype doc for full detail._

**[CODEX-DERIVED]** Configurable parameters:

> **⚠️ SUPERSEDED (generic schema below)** — the generic `opportunity_type`/`eligible_venues`/`eligible_markets` schema
> below was the original design. The two deployed variants are documented in the concrete sections that follow. Use
> those for new strategy-instance configs.

````yaml

## 2. Universe & Execution

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

**[CODEX-DERIVED]** Risk profile:

- Drawdowns: rare but sharp when execution fails mid-sequence (partial fill, adverse move, gas auction loss)
- Typical Sharpe: 3+ when opportunities are found; limited by opportunity frequency
- Kill switches: abnormal dispersion (likely broken feed), consecutive execution failures, venue outage

**[CODEX-DERIVED]** P&L attribution:

- **Arb edge captured**: (total_received - total_paid) on successful opp
- **Execution slippage**: difference between detected spread and realized spread
- **Gas / fees / commission**: per opp
- **Adverse-move losses** (leader-hedge aborts): unwind cost when hedge failed to fill in time

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

- Drawdowns: rare but sharp when execution fails mid-sequence (partial fill, adverse move, gas auction loss)
- Typical Sharpe: 3+ when opportunities are found; limited by opportunity frequency
- Kill switches: abnormal dispersion (likely broken feed), consecutive execution failures, venue outage

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

Metric set: `unified_trading_library.performance_metrics` defines the canonical metric surface (expected: Sharpe ratio, max drawdown, CAGR, Sortino, Calmar, win rate, avg trade PnL). Import was unavailable on this host.

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `434e5beffedf400905475c64ca77535e474bd5fb`
- `archetype_id`: `ARBITRAGE_PRICE_DISPERSION`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

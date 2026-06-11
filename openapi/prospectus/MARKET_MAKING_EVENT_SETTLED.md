# Strategy Prospectus: Market Making Event Settled

> **Archetype ID**: `MARKET_MAKING_EVENT_SETTLED`  
> **Family**: `MARKET_MAKING`  
> **Status** (codex): design  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `MARKET_MAKING` | Primary venue categories: PREDICTION, SPORTS

**[MACHINE-DERIVED]** Capability cells (from ARCHETYPE_CAPABILITY_REGISTRY):

| Venue Category | Instrument Type | Status    | Notes                                                                     |
| -------------- | --------------- | --------- | ------------------------------------------------------------------------- |
| PREDICTION     | event_settled   | PARTIAL   | Polymarket CLOB MM supported in theory but quoting UX differs (no 'lay'). |
| PREDICTION     | event_settled   | BLOCKED   | Kalshi execution adapter pending.                                         |
| SPORTS         | event_settled   | SUPPORTED | Primary — lay-native.                                                     |
| SPORTS         | event_settled   | PARTIAL   | Lay semantics differ per venue; capability flag gap per-venue.            |
| SPORTS         | event_settled   | BLOCKED   | Unity Feed Connector is place-only, not quoting.                          |

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Posts back + lay quotes on sports exchanges (Betfair, Smarkets, Matchbook, Betdaq) OR prediction-market exchanges
(Polymarket). Earns the bid-ask spread on matched bets while managing inventory exposure. Unlike CLOB MM (continuous),
each market settles discretely on event resolution.

**[CODEX-DERIVED]** Execution semantics:

- `QUOTE` action type — continuous quote lifecycle
- Delta-proxy repricer handles reference moves
- Fill stream → inventory update → skew recompute → quote cancel/replace
- `CANCEL` on event start

**[CODEX-DERIVED]** Configurable parameters:

````yaml
venue: BETFAIR_DIRECT # or UNITY (routes to Betfair-via-Unity)
league: EPL
markets_eligible: ["1X2", "OVER_UNDER_2_5", "BTTS"]
theo_source: sharp_book # or consensus / model / hybrid
sharp_reference_venue: PINNACLE # used if theo_source = sharp_book
half_spread_ticks: 1
max_inventory_per_selection: 500 # in bankroll units
max_inventory_imbalance: 250
skew_factor: 0.5
commission_rate: 0.028 # Betfair via Unity 2.8%
min_spread_edge_pct: 0.5 # min net edge after commission
cancel_on_event_start: true
pre_event_cancel_minutes: 2
kill_switch_movement_pct: 10.0
refresh_interval_seconds: 5
sh
_...truncated. See codex archetype doc._

## 2. Universe & Execution

**[CODEX-DERIVED]** Venue universe (from doc frontmatter): BETDAQ, BETFAIR, MATCHBOOK, POLYMARKET, SMARKETS

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

**[CODEX-DERIVED]** Risk profile:

- Drawdowns: moderate; inventory carried into match resolution can go wrong
- Typical Sharpe: 1.5-3.0 for well-run sports MM
- Kill switches: rapid odds move (injury, red card, goal), venue outage, inventory breach

**[CODEX-DERIVED]** P&L attribution:

- **Spread captured**: (lay_price - back_price) × matched_size − commission
- **Inventory P&L on settlement**: realized when match resolves
- **Commission drag**: per filled bet
- **Execution alpha**: vs benchmark fills

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
    EXCHANGE["Betting Exchange\n(BETFAIR / SPORTRADAR)"]
    BET["Back/Lay Position"]
    HOT --> EXCHANGE
    EXCHANGE --> BET
    BET -. settlement .-> HOT
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

- Drawdowns: moderate; inventory carried into match resolution can go wrong
- Typical Sharpe: 1.5-3.0 for well-run sports MM
- Kill switches: rapid odds move (injury, red card, goal), venue outage, inventory breach

**[CODEX-DERIVED]** Configurable risk parameters (from config schema):

- `max_inventory_imbalance: 250`
- `max_inventory_per_selection: 500 # in bankroll units`
- `min_spread_edge_pct: 0.5 # min net edge after commission`

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

Metric set: `unified_trading_library.performance_metrics` defines the canonical metric surface (expected: Sharpe ratio, max drawdown, CAGR, Sortino, Calmar, win rate, avg trade PnL). Import was unavailable on this host.

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `434e5beffedf400905475c64ca77535e474bd5fb`
- `archetype_id`: `MARKET_MAKING_EVENT_SETTLED`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

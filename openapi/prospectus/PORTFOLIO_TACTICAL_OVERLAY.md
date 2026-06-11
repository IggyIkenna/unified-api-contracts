# Strategy Prospectus: Portfolio Tactical Overlay

> **Archetype ID**: `PORTFOLIO_TACTICAL_OVERLAY`  
> **Family**: `PORTFOLIO`  
> **Status** (codex): design  
> **Alpha disclosure**: full (debugging mode) — no client-facing curtailment applied.

## 1. What It Does + How It Makes Decisions

**[MACHINE-DERIVED]** Family: `PORTFOLIO` | Primary venue categories: not registered

**[MACHINE-DERIVED]** Capability cells: `not_registered` — archetype not in ARCHETYPE_CAPABILITY_REGISTRY

**[CODEX-DERIVED]** From `codex/09-strategy/architecture-v2/archetypes/`:

Operator/regime-driven tactical re-weighting on top of a base allocation. A regime classifier or explicit operator
command produces per-strategy multipliers that adjust the base weight vector. Higher-frequency rebalancing than the
other 3 portfolio archetypes — intraday firing is supported when regime transitions are detected.

The key distinction from the other Portfolio archetypes:

| Archetype                        | Weight driver                                      |
| -------------------------------- | -------------------------------------------------- |
| `PORTFOLIO_MULTI_STRATEGY`       | Static config — no change until operator edits     |
| `PORTFOLIO_RISK_PARITY`          | Realised volatility per child                      |
| `PORTFOLIO_FACTOR_ALLOCATION`    | Factor exposure vs mandate                         |
| **`PORTFOLIO_TACTICAL_OVERLAY`** | **Regime classifier OR explicit operator command** |

Tactical overlay is used for mandates that require **situational response**: reduce risk-on strategies during vol-spike
regimes; increase carry exposure in low-vol/high-rate environments; rotate toward defensive strategies on operator
risk-off command.

**[CODEX-DERIVED]** Execution semantics:

Identical to `PORTFOLIO_MULTI_STRATEGY` — emits `AllocationDirective` only. On regime change:

1. Recompute effective weights using new regime label.
2. Emit revised directives to children immediately (within `latency_budget_ms` = 10 000 ms for intraday response).
3. Emit `REGIME_TRANSITION` event to audit log with old/new regime + old/new weights.

Operator command path:

- `POST /api/strategies/{id}/tactical-override` in strategy-service API.
- Body: `{ "regime_label": "HIGH_VOL_RISK_OFF", "duration_minutes": 240, "operator_id": "..." }`.
- Overlay reverts to classifier-driven regime after `duration_minutes` expires.

**[CODEX-DERIVED]** Configurable parameters:

````yaml
archetype: PORTFOLIO_TACTICAL_OVERLAY
child_strategy_ids:
  - "ML_DIRECTIONAL_CONTINUOUS@hyperliquid-btc-5m-usdt-prod"
  - "CARRY_BASIS_PERP@uniswap-hyperliquid-eth-usdt-prod"
  - "VOL_TRADING_OPTIONS@deribit-eth-usdt-prod"

base_weights: # base allocation; regime multipliers scale from here
  - 0.40 # ML_DIRECTIONAL_CONTINUOUS
  - 0.35 # CARRY_BASIS_PERP
  - 0.25 # VOL_TRADING_OPTIONS

regime_source: cross_instrument/regime_classifier_signal # features-service data_type
regime_lookback_bars: 12 # regime averaging window (12 × 4h bars = 2-day average)

regime_multiplier_tables: # see i
_...truncated. See codex archetype doc._

## 2. Universe & Execution

**[MACHINE-DERIVED]** Available execution algorithms: Adaptive Twap, Almgren Chriss, Hybrid Optimal, Passive Aggressive Hybrid, Pov Dynamic, Twap, Vwap

> **[MACHINE-DERIVED — GAP]** Order semantics (TIF/FOK/IOC/post-only, ref-pricing modes, multi-leg delta ownership): `not_registered` — VENUE_ORDER_SEMANTICS registry is honest-empty (Phase 2 backfill pending). See gap tracker: `plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md`.

## 3. Exposures & Normalization

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

**[CODEX-DERIVED]** Configurable risk parameters (from config schema):

- `max_child_weight: 0.70`
- `min_active_fraction: 0.5`
- `min_child_weight: 0.05`
- `min_regime_confidence: 0.70 # classifier confidence threshold; below → NEUTRAL regime`

## 6. Performance

> **No backtest metrics recorded for this archetype configuration.** Run Phase 5 backtest-on-demand (`strategy_service/engine/backtest/runner.py` over historical data) to generate metrics.

**NEVER invented numbers are shown here** — this section is honest about the absence.

Metric set: `unified_trading_library.performance_metrics` defines the canonical metric surface (expected: Sharpe ratio, max drawdown, CAGR, Sortino, Calmar, win rate, avg trade PnL). Import was unavailable on this host.

## 7. Provenance

- `manifest_version`: 1.0.0
- `generated_from_commit`: `434e5beffedf400905475c64ca77535e474bd5fb`
- `archetype_id`: `PORTFOLIO_TACTICAL_OVERLAY`
- `generated_by`: `scripts/openapi/generate_strategy_prospectus.py` (unified-trading-pm generator family)

_This prospectus is machine-generated. Sections marked [CODEX-DERIVED] are sourced from hand-authored engineering docs in `codex/09-strategy/architecture-v2/archetypes/`. Sections marked [MACHINE-DERIVED] are sourced from the capability manifest (UAC registry data, 409 nodes / 663 edges). Full alpha disclosure — debugging mode. Curtailment is a later config flag._

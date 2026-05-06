<!-- POST_PLAN_BANNER_2026_05_06_FINAL -->

> **Post-2026-05-06** — read [`../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md`](../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md) before code/doc changes informed by this doc. The post-plan-reality doc summarizes the 10 cross-cutting principles codified in workspace `CLAUDE.md` (live=batch, no double SSOT, three-category empty-output decision A/B/C, cluster validation MANDATORY at `record_captured`, `available_at` per-row write-time, prediction lifecycle, temporary state must have named successor, per-VM shard isolation, multi-axis shard-vs-display distinction) plus the active plans (`writegate_honest_coverage_endtoend_2026_05_06.plan.md`, `predictions_canonical_question_group_polymarket_migration_2026_05_06.plan.md`, `data_status_multi_axis_shard_propagation_2026_05_06.plan.md`). If this doc disagrees with the active plans, the plans win. Flag conflicts to user — don't decide unilaterally.

# VIX Live Streaming Research

**Current state (batch):** Barchart manual CSV dumps → `BarchartOhlcv15m` schema → market-tick-data-service → GCS. Instrument: `CBOE:INDEX:VIX-USD`.

**Gap:** We need live VIX streaming (index or futures) for real-time strategies.

## Research Targets

| Provider      | Status               | Notes                                                                   |
| ------------- | -------------------- | ----------------------------------------------------------------------- |
| **Databento** | Index in development | VIX options (OPRA) available; VIX index real-time/historical on roadmap |
| **IBKR**      | Available            | TWS API streams VIX index/futures; requires market data subscription    |
| **CBOE**      | Direct               | CBOE direct feed; evaluate cost/coverage                                |
| **Others**    | TBD                  | Document as we find them                                                |

## Barchart Batch (Current)

- **Schema**: `BarchartOhlcv15m` (Time, Open, High, Low, Last, Volume)
- **Source**: Manual CSV from Barchart subscription
- **Path**: `market-tick-data-service/data/vix/vix_intraday-15min_historical-data-*.csv`
- **No API, no live** — migrate when Databento index or IBKR VIX streaming is chosen

## Migration Path

1. **Short term**: Keep Barchart batch; document schema in unified-api-contracts (done)
2. **When Databento index ships**: Add Databento VIX schemas; migrate market-tick-data-service
3. **When IBKR VIX chosen**: Add IBKR VIX streaming schemas; integrate TWS

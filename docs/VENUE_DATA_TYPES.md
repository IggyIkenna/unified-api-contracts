<!-- POST_PLAN_BANNER_2026_05_06 -->

> **POST-PLAN REALITY (2026-05-06)** — read [`../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md`](../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md) BEFORE making code or doc changes informed by this doc. This doc is partially stale: may not reflect new UAC SSOTs being added in writegate Phase 1B + predictions Phase 1A: BUNDLED_DATA_TYPES, DATA_TYPE_TO_CLUSTER_REGISTRY, SOURCE_PRIORITY, AVAILABILITY_AT_SEMANTICS, CanonicalQuestionGroup enum + classifier, MarketLifecycle, MATCH_END_TIME_DETECTORS, OPTIONS_CLUSTERS (lifted from instruments-service), FUTURES_CLUSTERS, SPORTS_FIXTURE_CLUSTERS, PREDICTION_GROUPS. The post-plan-reality doc lists the 10 cross-cutting principles codified in workspace `CLAUDE.md` (live=batch, no double SSOT, three-category empty-output decision A/B/C, cluster validation mandatory at record_captured, per-row write-time `available_at`, prediction lifecycle timing, temporary state must have named successor, per-VM shard isolation, etc.) plus the active plans where the canonical post-plan reality is being implemented. If this doc and the active plans disagree, the plans win. If you find a contradiction the plans don't address, flag to user — don't decide unilaterally.

# Per-venue data types: trades, OHLCV, orderbook, ticker, funding, liquidations

Single source of truth for which data types each venue/data vendor provides. Align with `venue_manifest.py` and `INDEX.md`.

| Venue             | trades | OHLCV      | orderbook | ticker  | funding      | liquidations | Notes                                          |
| ----------------- | ------ | ---------- | --------- | ------- | ------------ | ------------ | ---------------------------------------------- |
| **databento**     | ✓      | ✓ (1m, 1s) | ✓ MBP-1   | —       | —            | —            | Historical; symbology, definition              |
| **tardis**        | ✓      | —          | ✓         | —       | —            | —            | Exchanges, instruments, trades, book           |
| **ccxt**          | ✓      | —          | ✓         | ✓       | per exchange | —            | Unified; Binance, OKX, Bybit, Upbit, etc.      |
| **binance**       | ✓      | ✓ klines   | ✓         | ✓       | ✓ (futures)  | ✓ (futures)  | REST + WebSocket                               |
| **okx**           | ✓      | ✓          | ✓         | ✓       | ✓            | ✓            | UMI adapter                                    |
| **bybit**         | ✓      | ✓          | ✓         | ✓       | ✓            | ✓            | UMI adapter                                    |
| **deribit**       | ✓      | —          | ✓         | ✓       | ✓            | —            | Options chain                                  |
| **hyperliquid**   | ✓      | —          | ✓         | ✓       | ✓            | ✓            | On-chain perps                                 |
| **aster**         | ✓      | —          | ✓         | ✓       | ✓            | ✓            | On-chain perps                                 |
| **upbit**         | ✓      | —          | ✓         | ✓       | —            | —            | CeFi full surface                              |
| **coinbase**      | ✓      | ✓ candles  | ✓         | ✓       | —            | —            | Spot only                                      |
| **ibkr**          | ✓      | ✓ bars     | —         | ✓       | —            | —            | TWS/ib_insync                                  |
| **yahoo_finance** | —      | ✓ 24h      | —         | ✓ quote | —            | —            | OHLCV daily, splits, dividends; TradFi adapter |
| **barchart**      | —      | ✓ 15m      | —         | —       | —            | —            | VIX index (CBOE); manual CSV dumps             |
| **thegraph**      | —      | —          | —         | —       | —            | —            | Subgraph-specific (swaps, pools, reserves)     |
| **alchemy**       | —      | —          | —         | —       | —            | —            | RPC/API; DeFi fallback                         |

## Schema mapping

| Venue         | OHLCV schema      | Ticker schema | Trades schema  | Orderbook schema |
| ------------- | ----------------- | ------------- | -------------- | ---------------- |
| databento     | DatabentoOhlcvBar | —             | DatabentoTrade | DatabentoMbp1    |
| tardis        | —                 | —             | TardisTrade    | TardisOrderBook  |
| binance       | BinanceKline      | BinanceTicker | BinanceTrade   | BinanceOrderBook |
| yahoo_finance | YahooOhlcv24h     | YahooQuote    | —              | —                |
| barchart      | BarchartOhlcv15m  | —             | —              | —                |

## Yahoo Finance and Barchart (TradFi external providers)

- **yahoo_finance**: Daily OHLCV (YahooOhlcv24h), quote (YahooQuote), splits (YahooSplits), dividends (YahooDividends). Used for FX (KRW/USD), equities, ETFs. No trades, orderbook, funding, liquidations.
- **barchart**: 15-minute OHLCV (BarchartOhlcv15m). Used for VIX index (CBOE). Manual CSV dumps; no API, no live. No trades, orderbook, ticker, funding, liquidations.

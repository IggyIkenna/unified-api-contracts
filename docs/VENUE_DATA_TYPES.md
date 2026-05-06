# Per-venue data types: trades, OHLCV, orderbook, ticker, funding, liquidations

<!-- POST_PLAN_SECTION_2026_05_06 -->

## Post-2026-05-06 additions

**Post-2026-05-06 additions** — bundled data_types (cluster validation mandatory): `options_chain`, `futures_chain`, `prediction_canonical_question_group`, sports per-fixture-bundle data_types (`ODDS_SNAPSHOT`/`ODDS_MOVEMENT`/`ARBITRAGE`). New prediction data_type `prediction_canonical_question_group` replaces legacy per-base_asset Polymarket sharding (`BTC`/`ETH`/`SPX`/`FOOTBALL`/`OTHER`).

**Workspace SSOTs**: [POST_PLAN_REALITY](../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md) (10 cross-cutting principles + active plans), [availability-manifest-and-data-status](../../unified-trading-pm/codex/02-data/availability-manifest-and-data-status.md), [deployment-clusters-live-vs-batch](../../unified-trading-pm/codex/05-infrastructure/deployment-clusters-live-vs-batch.md), [shard-level-failure-isolation](../../unified-trading-pm/codex/04-architecture/shard-level-failure-isolation.md), [error-handling](../../unified-trading-pm/codex/06-coding-standards/error-handling.md), [validation-patterns](../../unified-trading-pm/codex/06-coding-standards/validation-patterns.md).

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

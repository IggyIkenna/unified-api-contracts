# Batch-Live Symmetry Contract — unified-api-contracts

> **Canonical SSOT:** [batch-live-architecture.md](../../unified-trading-pm/codex/04-architecture/batch-live-architecture.md).
> This file carries only the **unified-api-contracts**-specific normalizer/venue mapping. The cross-cutting invariant —
> live and batch are operational modes of the SAME pipeline (identical schemas, identical `data_types`, identical fields;
> only the SOURCE per `(asset_group, data_type)` may differ), normalizers are pure functions with no `mode`/`source`
> branching, and `available_at` is stamped from the `SOURCE_PRIORITY` top entry's live emission time — lives in the codex
> SSOT above. **Do not duplicate those rules here; if this file disagrees with codex, codex wins.**

## UAC-specific normalizer + symmetry surface

### Symmetry helpers (all `symbol`/`side`-setting normalizers MUST use these)

| Helper                         | Module                       | Purpose                                                      |
| ------------------------------ | ---------------------------- | ------------------------------------------------------------ |
| `normalize_symbol(venue, raw)` | `normalize_utils/symbols.py` | Venue-native symbol → `BASE-QUOTE[-PERP\|-EXPIRY]` canonical |
| `normalize_side(raw)`          | `normalize_utils/sides.py`   | Any side string/int → `"buy"` or `"sell"`                    |

### Per-venue source mapping (live source ↔ batch source ↔ UAC normalizer)

| Venue           | Live source                            | Batch source                   | Normalizers                                                                                                           |
| --------------- | -------------------------------------- | ------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| **Binance**     | WebSocket (`@trade`/`@depth`/`@kline`) | Tardis GCS / Databento (OHLCV) | `normalize_binance_{trade,orderbook,ticker,kline}`                                                                    |
| **Bybit**       | WebSocket (`v5/public`)                | Tardis GCS                     | `normalize_bybit_{trade,orderbook,ticker,kline}`                                                                      |
| **OKX**         | WebSocket (`ws/v5/public`)             | Tardis GCS                     | `normalize_okx_{trade,orderbook,ticker,kline}`                                                                        |
| **Deribit**     | WebSocket (`ws/api/v2`)                | Tardis GCS + option quotes     | `normalize_deribit_{trade,orderbook,option_ticker}`, `normalize_tardis_option_quote`                                  |
| **Coinbase**    | WebSocket (`advanced-trade-ws`)        | — (live-only)                  | `normalize_coinbase_{trade,orderbook,ticker}`                                                                         |
| **Hyperliquid** | WebSocket (`api.hyperliquid.xyz/ws`)   | — (live-only)                  | `normalize_hyperliquid_{order,fill,ticker,derivative_ticker,orderbook}`                                               |
| **Tardis**      | — (batch aggregator)                   | replays venue-native format    | `normalize_tardis_{trade,orderbook,option_quote,ws_subscription}` (symbols pass through uppercase, unchanged)         |
| **Databento**   | — (batch aggregator)                   | CME/CBOT/NYMEX, prices ÷ 1e9   | `normalize_databento_{trade,mbp1_orderbook,mbp10_orderbook,bbo1s_orderbook,ohlcv_bar,option_quote,definition,symbol}` |

Live-only venues (Coinbase, Hyperliquid) have no batch source — parity tests skip them.

### Fields allowed to differ live↔batch for the same logical event

`received_at` (ingestion wall-clock — never assert equal), `sequence` (WS-only; batch may be 0/None — skip if None),
`raw` (not in canonical output), `venue` (case may differ, e.g. live `"binance"` vs Tardis `"BINANCE"` — compare
lowercase). All other canonical fields (`trade_id`, `price`, `quantity`, `side`, `symbol`, `timestamp`) MUST be equal.

### Timestamp handling (UAC normalizers)

Nanosecond ts (Databento) ÷ `1_000_000_000`; millisecond ts (Binance/Bybit/OKX) ÷ `1_000`; ISO-8601 via
`datetime.fromisoformat()`. Always construct with `tzinfo=timezone.utc`; use `datetime.now(timezone.utc)` **only** when
the raw record carries no timestamp.

### Parity test contract

`tests/test_batch_live_parity.py` — per venue pair with overlapping data: construct equivalent raw records for the same
logical event, normalize both independently, assert equality on `trade_id`/`price`/`quantity`/`side`/`symbol` (after
symbol normalization), skip `received_at`/`sequence`/`venue`.

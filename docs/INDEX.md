# Per-venue contract index

<!-- POST_PLAN_SECTION_2026_05_06 -->

## Post-2026-05-06 additions

**Post-2026-05-06 additions** — UAC owns new canonical-crosscutting registries: `BUNDLED_DATA_TYPES` + cluster registries (writegate Phase 1B), `SOURCE_PRIORITY` (Phase 1B), `AVAILABILITY_AT_SEMANTICS` (Phase 1B), `CanonicalQuestionGroup` enum + classifier + `MarketLifecycle` (predictions Plan A Phase 1A), `MATCH_END_TIME_DETECTORS` (sports). New facade `predictions.py`. New module `canonical/crosscutting/{honest_coverage, source_priority, availability_semantics}.py`. See [ARCHITECTURE.md](ARCHITECTURE.md) for full table.

**Workspace SSOTs**: [POST_PLAN_REALITY](../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md) (10 cross-cutting principles + active plans), [availability-manifest-and-data-status](../../unified-trading-pm/codex/02-data/availability-manifest-and-data-status.md), [deployment-clusters-live-vs-batch](../../unified-trading-pm/codex/05-infrastructure/deployment-clusters-live-vs-batch.md), [shard-level-failure-isolation](../../unified-trading-pm/codex/04-architecture/shard-level-failure-isolation.md), [error-handling](../../unified-trading-pm/codex/06-coding-standards/error-handling.md), [validation-patterns](../../unified-trading-pm/codex/06-coding-standards/validation-patterns.md).

| Venue         | Market data     | Order feed | Position feed | Errors | WebSocket     | FIX          | Notes                                       |
| ------------- | --------------- | ---------- | ------------- | ------ | ------------- | ------------ | ------------------------------------------- |
| databento     | Yes             | N/A        | N/A           | Yes    | N/A           | N/A          | Historical, symbology                       |
| tardis        | Yes             | N/A        | N/A           | Yes    | If documented | N/A          | Exchanges, instruments, trades, book        |
| ccxt          | Yes             | Yes        | Yes           | Yes    | Per exchange  | Per exchange | Shared for Binance, OKX, Bybit, Upbit, etc. |
| binance       | Yes             | Yes        | Yes           | Yes    | Yes           | N/A          | REST + WebSocket                            |
| thegraph      | Yes (subgraph)  | N/A        | N/A           | Yes    | N/A           | N/A          | GraphQL; Uniswap, Aave                      |
| okx           | Yes             | Yes        | Yes           | Yes    | Yes           | If offered   | UMI adapter                                 |
| bybit         | Yes             | Yes        | Yes           | Yes    | Yes           | If offered   | UMI adapter                                 |
| yahoo_finance | Yes             | N/A        | N/A           | Yes    | N/A           | N/A          | TradFi adapter                              |
| alchemy       | RPC/API         | N/A        | N/A           | Yes    | N/A           | N/A          | DeFi fallback                               |
| hyperliquid   | Yes             | Yes        | Yes           | Yes    | Yes           | N/A          | HTTP + S3 bucket                            |
| aster         | Yes             | Yes        | Yes           | Yes    | Yes           | N/A          | On-chain perps                              |
| upbit         | Yes             | Yes        | Yes           | Yes    | Yes           | If offered   | CeFi full surface                           |
| ibkr          | Yes             | Yes        | Yes           | Yes    | Callbacks     | N/A          | TWS/ib_insync, UMI+UOI+position monitor     |
| barchart      | Yes (OHLCV 15m) | N/A        | N/A           | N/A    | N/A           | N/A          | VIX index; manual CSV dumps                 |

Schema files: `unified_api_contracts/<venue>/schemas.py`. Examples: `unified_api_contracts/<venue>/examples/`. VCR mocks: `unified_api_contracts/<venue>/mocks/`.

- **Available inventory**: [API_CONTRACTS_AVAILABLE_INVENTORY.md](API_CONTRACTS_AVAILABLE_INVENTORY.md) — Full inventory of external APIs (CeFi, TradFi, DeFi, Sports, Cloud); schema coverage; gaps.
- **Cross-venue matrix**: [CROSS_VENUE_MATRIX.md](CROSS_VENUE_MATRIX.md) — CCXT vs direct access; normalization flow; venue-unique exposure.
- **Chain of events**: [API_CONTRACTS_CHAIN_OF_EVENTS.md](API_CONTRACTS_CHAIN_OF_EVENTS.md) — Config → SDK/API call → schema validation → adapter output; VCR recording and live verification done in the six interfaces (unified-trade-execution-interface, unified-sports-execution-interface, unified-reference-data-interface, unified-position-interface, unified-market-interface, unified-cloud-interface); AC does replay only; version alignment.
- **Cross-venue matrix**: [CROSS_VENUE_MATRIX.md](CROSS_VENUE_MATRIX.md) — CCXT vs direct, normalization flow, venue-unique exposure, data source mapping, schema coverage.
- **Per-venue data types**: [VENUE_DATA_TYPES.md](VENUE_DATA_TYPES.md) — trades, OHLCV, orderbook, ticker, funding, liquidations per venue.
- **Transport and constraints**: [TRANSPORT_AND_ENDPOINTS.md](TRANSPORT_AND_ENDPOINTS.md) — REST vs WebSocket vs FIX per venue, rate limits, auth, how to handle each.
- **Mocks and VCR**: [MOCKS_AND_VCR.md](MOCKS_AND_VCR.md) — recording cassettes, filtering secrets, per-venue cassette naming.
- **VCR ↔ schema alignment**: [VCR_SCHEMA_ALIGNMENT.md](VCR_SCHEMA_ALIGNMENT.md) — every schema vs VCR/example coverage; checklist to fully align mocks to schemas.

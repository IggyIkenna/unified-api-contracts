# Per-venue contract index

| Venue | Market data | Order feed | Position feed | Errors | WebSocket | FIX | Notes |
|-------|-------------|------------|---------------|--------|-----------|-----|-------|
| databento | Yes | N/A | N/A | Yes | N/A | N/A | Historical, symbology |
| tardis | Yes | N/A | N/A | Yes | If documented | N/A | Exchanges, instruments, trades, book |
| ccxt | Yes | Yes | Yes | Yes | Per exchange | Per exchange | Shared for Binance, OKX, Bybit, Upbit, etc. |
| binance | Yes | Yes | Yes | Yes | Yes | N/A | REST + WebSocket |
| thegraph | Yes (subgraph) | N/A | N/A | Yes | N/A | N/A | GraphQL; Uniswap, Aave |
| okx | Yes | Yes | Yes | Yes | Yes | If offered | UMI adapter |
| bybit | Yes | Yes | Yes | Yes | Yes | If offered | UMI adapter |
| yahoo_finance | Yes | N/A | N/A | Yes | N/A | N/A | TradFi adapter |
| alchemy | RPC/API | N/A | N/A | Yes | N/A | N/A | DeFi fallback |
| hyperliquid | Yes | Yes | Yes | Yes | Yes | N/A | HTTP + S3 bucket |
| aster | Yes | Yes | Yes | Yes | Yes | N/A | On-chain perps |
| upbit | Yes | Yes | Yes | Yes | Yes | If offered | CeFi full surface |
| ibkr | Yes | Yes | Yes | Yes | Callbacks | N/A | TWS/ib_insync, UMI+UOI+position monitor |

Schema files: `api_contracts/<venue>/schemas.py`. Examples: `api_contracts/<venue>/examples/`. VCR mocks: `api_contracts/<venue>/mocks/`.

- **Transport and constraints**: [TRANSPORT_AND_ENDPOINTS.md](TRANSPORT_AND_ENDPOINTS.md) — REST vs WebSocket vs FIX per venue, rate limits, auth, how to handle each.
- **Mocks and VCR**: [MOCKS_AND_VCR.md](MOCKS_AND_VCR.md) — recording cassettes, filtering secrets, per-venue cassette naming.
- **VCR ↔ schema alignment**: [VCR_SCHEMA_ALIGNMENT.md](VCR_SCHEMA_ALIGNMENT.md) — every schema vs VCR/example coverage; checklist to fully align mocks to schemas.

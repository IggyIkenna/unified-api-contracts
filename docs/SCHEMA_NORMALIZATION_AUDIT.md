<!-- POST_PLAN_BANNER_2026_05_06 -->

> **POST-PLAN REALITY (2026-05-06)** — read [`../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md`](../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md) BEFORE making code or doc changes informed by this doc. This doc is partially stale: may not reflect new UAC SSOTs being added in writegate Phase 1B + predictions Phase 1A: BUNDLED_DATA_TYPES, DATA_TYPE_TO_CLUSTER_REGISTRY, SOURCE_PRIORITY, AVAILABILITY_AT_SEMANTICS, CanonicalQuestionGroup enum + classifier, MarketLifecycle, MATCH_END_TIME_DETECTORS, OPTIONS_CLUSTERS (lifted from instruments-service), FUTURES_CLUSTERS, SPORTS_FIXTURE_CLUSTERS, PREDICTION_GROUPS. The post-plan-reality doc lists the 10 cross-cutting principles codified in workspace `CLAUDE.md` (live=batch, no double SSOT, three-category empty-output decision A/B/C, cluster validation mandatory at record_captured, per-row write-time `available_at`, prediction lifecycle timing, temporary state must have named successor, per-VM shard isolation, etc.) plus the active plans where the canonical post-plan reality is being implemented. If this doc and the active plans disagree, the plans win. If you find a contradiction the plans don't address, flag to user — don't decide unilaterally.

# Unified API Contracts — Schema Normalization Audit

**Date:** 2026-03-05
**Scope:** External vs normalised schemas, orphan detection, mapping coverage

---

## Ideology

- **UAC = normalization layer** — like an internal CCXT/TARDIS. unified-api-contracts maps raw venue responses to canonical types.
- **Interfaces = venue routers** — raw never flows to services; interfaces return normalized data only.
- **All response types** must have a normalization path.
- **Full plan:**
- **Codex:** 02-data/contracts-scope-and-layout.md, 05-infrastructure/contracts-integration.md

---

## 1. Terminology Clarification

| Term                               | Meaning                                                                                                                                            |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **unified_api_contracts.egg-info** | Build artifact from `pip install -e .` / `uv pip install -e .`. Contains package metadata. **Not** a schema package. Should be in `.gitignore`.    |
| **external**                       | Raw external schemas — per-venue Pydantic models for API request/response shapes (BinanceTrade, OkxOrder, etc.).                                   |
| **canonical**                      | Canonical schemas — CanonicalTrade, CanonicalOrder, CanonicalOrderBook, CanonicalFill, etc. One-hop normalisation target.                          |
| **"Extended"**                     | Not a package. In sports schemas, "Extended" is a field-naming convention (e.g. "Extended HT features", "Team Extended") for extra/derived fields. |
| **sports/canonical**               | Cross-source normalised sports types (CanonicalFixture, CanonicalOdds, CanonicalBookmakerMarket) — separate domain from trading canonical.         |

---

## 2. Package Structure

unified_api_contracts/
external/ # Raw external schemas (60+ providers)
canonical/ # Trading canonical schemas
schemas/ # Shared cross-venue
canonical_mappings.py # DataSourceMapping, VENUE_TO_DATA_SOURCE

---

## 3. Normalization Coverage

### 3.1 Trading Domain — normalize.py

| External Schema                  | Normalised To  | Status   |
| -------------------------------- | -------------- | -------- |
| BinanceTrade                     | CanonicalTrade | MAPPED   |
| DatabentoTrade                   | CanonicalTrade | MAPPED   |
| TardisTrade                      | CanonicalTrade | MAPPED   |
| All other external trade schemas | —              | ORPHANED |

Missing normalizers: No normalize_order, normalize_orderbook, normalize_fill for any provider.

### 3.2 Orphaned External Providers (~57)

CeFi: okx, bybit, coinbase, upbit, ccxt, deribit, nautilus
DeFi: thegraph, aster, hyperliquid, alchemy
TradFi: ibkr
Sports/Betting: matchbook, betfair, betdaq, smarkets, kalshi, polymarket, predictit, pinnacle
Data/Alt: api_football, footystats, understat, barchart, fred, glassnode, open_meteo, coingecko

### 3.3 Sports Domain

sports/canonical/ — Cross-source normalised (CanonicalFixture, CanonicalOdds). Used by features-sports-service.
sports/sources/ — Raw per source. Normalisation in adapters.

---

## 4. Summary

| Metric                       | Count                          |
| ---------------------------- | ------------------------------ |
| External providers           | 60                             |
| With trade normalization     | 3 (binance, databento, tardis) |
| Orphaned (no normalize path) | ~57                            |

Conclusion: Most external schemas are raw-only. Normalization exists only for trades from 3 providers. Order/orderbook/fill normalization absent.

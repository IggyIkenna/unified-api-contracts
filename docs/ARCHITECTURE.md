<!-- POST_PLAN_BANNER_2026_05_06 -->

> **POST-PLAN REALITY (2026-05-06)** — read [`../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md`](../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md) BEFORE making code or doc changes informed by this doc. This doc is partially stale: may not reflect new UAC SSOTs being added in writegate Phase 1B + predictions Phase 1A: BUNDLED_DATA_TYPES, DATA_TYPE_TO_CLUSTER_REGISTRY, SOURCE_PRIORITY, AVAILABILITY_AT_SEMANTICS, CanonicalQuestionGroup enum + classifier, MarketLifecycle, MATCH_END_TIME_DETECTORS, OPTIONS_CLUSTERS (lifted from instruments-service), FUTURES_CLUSTERS, SPORTS_FIXTURE_CLUSTERS, PREDICTION_GROUPS. The post-plan-reality doc lists the 10 cross-cutting principles codified in workspace `CLAUDE.md` (live=batch, no double SSOT, three-category empty-output decision A/B/C, cluster validation mandatory at record_captured, per-row write-time `available_at`, prediction lifecycle timing, temporary state must have named successor, per-VM shard isolation, etc.) plus the active plans where the canonical post-plan reality is being implemented. If this doc and the active plans disagree, the plans win. If you find a contradiction the plans don't address, flag to user — don't decide unilaterally.

# Architecture

**SSOT for constraints and layout:** unified-trading-codex/02-data/contracts-scope-and-layout.md. **Full layout:** [PACKAGE_LAYOUT_AND_SCOPE.md](PACKAGE_LAYOUT_AND_SCOPE.md).

## Package structure

The package is organized into six top-level directories plus root facade files:

| Directory              | Purpose                                                                 | Contents                                                                                                                                                                                                                                      |
| ---------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Root facade files**  | Domain-level re-exports for consumer convenience                        | `market.py`, `execution.py`, `reference.py`, `sports.py`, `position.py`, `features.py`, `derivatives.py`, `infrastructure.py`, `connectivity.py`, `latency.py`, `options.py`, `odds.py`, `errors.py`, `rate_limits.py`, `sports_reference.py` |
| **`canonical/`**       | Canonical domain types, crosscutting types, errors                      | `domain/{market,execution,reference,sports,position,features,derivatives,infrastructure,onchain}/`, `crosscutting/{analytics,connectivity,latency,rate_limits,risk}`, `errors/{cefi,defi,altdata,sports}`, `canonical_mappings.py`            |
| **`external/`**        | Raw per-source request/response/error schemas + per-source normalize.py | 79 source directories (binance, databento, hyperliquid, betfair, fix, gcp, etc.)                                                                                                                                                              |
| **`normalize_utils/`** | Shared normalization helpers used by per-source normalize.py files      | 25 modules (ohlcv, tickers, orderbooks, trades, symbols, instruments, options, sports, onchain, etc.)                                                                                                                                         |
| **`registry/`**        | Venue/capability/endpoint registry and manifest                         | `capability.py`, `capability_data.py`, `endpoint_registry.py`, `venue_constants.py`, `venue_rate_limits.py`, `venue_manifest/{cefi,defi,tradfi,betting_sports,data_providers,internal_services}.py`                                           |
| **`config/`**          | Validation configuration                                                | `trading_validation.py`                                                                                                                                                                                                                       |
| **`testing/`**         | Test infrastructure exported for consumers                              | `conftest_helper.py`, `fault_injection.py`, `detect_cassette_drift.py`, `network_block_plugin.py`, `vcr_endpoints.py`                                                                                                                         |

## Placement rule (where new modules go)

| Content type                                            | Location                           | Examples                                                                                       |
| ------------------------------------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Raw schemas for an external API, protocol, or venue** | **`external/<name>/`**             | binance, databento, ccxt, fix, nautilus, prime_broker, regulatory                              |
| **Normalization for a specific source**                 | **`external/<name>/normalize.py`** | Each source's normalize.py maps raw schemas to canonical types                                 |
| **Shared normalization helpers**                        | **`normalize_utils/`**             | ohlcv.py, tickers.py, orderbooks.py, symbols.py                                                |
| **Canonical domain types**                              | **`canonical/domain/<domain>/`**   | market, execution, sports, position, features, derivatives, reference, infrastructure, onchain |
| **Canonical crosscutting types**                        | **`canonical/crosscutting/`**      | analytics, connectivity, latency, rate_limits, risk                                            |
| **Canonical error types**                               | **`canonical/errors/`**            | cefi.py, defi.py, altdata.py, sports.py                                                        |
| **Root facade re-exports**                              | **Root `.py` files**               | `market.py`, `execution.py` -- re-export from canonical for convenience                        |
| **Venue/capability/endpoint metadata**                  | **`registry/`**                    | capability.py, venue_constants.py, endpoint_registry.py                                        |
| **Venue manifest data**                                 | **`registry/venue_manifest/`**     | cefi.py, defi.py, tradfi.py, betting_sports.py                                                 |

**Internal** (service-to-service) schemas live in **unified-internal-contracts**; AC is external + normalised only.

## External vs normalised

- **External**: Venue- or protocol-specific Pydantic models matching provider APIs. Use for parsing and validating raw API responses before mapping to canonical types. Each `external/{source}/` directory contains `schemas.py` and `normalize.py`.
- **Normalised**: Canonical types used by UMI/UOI and services. Organized under `canonical/domain/` by domain (market, execution, sports, etc.) and `canonical/crosscutting/` for cross-domain concerns. Root facade files (`market.py`, `execution.py`, etc.) re-export these for convenience.

See [README Structure](../README.md#structure), [docs/INDEX.md](INDEX.md), [docs/CROSS_VENUE_MATRIX.md](CROSS_VENUE_MATRIX.md).

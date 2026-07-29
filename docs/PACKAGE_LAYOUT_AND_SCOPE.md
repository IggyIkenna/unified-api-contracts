# Package Layout and Scope — unified-api-contracts

> **Canonical SSOT for the scope/dependency rule:**
> [separation-of-concerns.md](../../unified-trading-pm/codex/04-architecture/separation-of-concerns.md) (the T0 contracts
> layer: UAC canonical/external = external API schemas + canonical normalization with no deps except pydantic; UAC
> `internal` subpackage = internal service-to-service schemas depending on UAC canonical only). Schema-ownership
> placement lives in [schema-governance.md](../../unified-trading-pm/codex/02-data/schema-governance.md). This file
> carries only this repo's **physical package layout**. **Do not duplicate the cross-cutting scope/import rules here; if
> this file disagrees with codex, codex wins.**

## Dependency + scope rule (repo-local restatement)

- **unified-api-contracts must not import from unified-internal-contracts.** AC is a Tier 0 leaf — no `unified-*` deps;
  UIC can depend on AC, never the reverse. Therefore all schemas needed for mapping stay in AC (canonical instrument IDs,
  venue enums/manifest used by normalizers, any type venue adapters need to produce canonical output).
- **AC = external API contracts + mapping surface** (interfaces own connectivity; AC owns `normalize` + external
  contract availability/typing). **A schema not used for any external contract and not needed for mapping belongs in
  unified-internal-contracts.**

## Current package layout

```
unified_api_contracts/
├── __init__.py
├── # ── Root facade files (domain re-exports) ──
├── market.py / execution.py / reference.py / sports.py / sports_reference.py
├── position.py / features.py / derivatives.py / infrastructure.py / connectivity.py
├── latency.py / options.py / odds.py / errors.py / rate_limits.py
│
├── canonical/                 # Canonical types (domain + crosscutting + errors)
│   ├── canonical_mappings.py  # Cross-venue canonical mapping tables
│   ├── crosscutting/          # analytics, connectivity, latency, rate_limits, risk,
│   │                          #   + honest_coverage, source_priority, availability_semantics
│   ├── domain/                # market, execution, reference, sports, position, features,
│   │                          #   derivatives, infrastructure, onchain, predictions
│   └── errors/                # cefi, defi, altdata, sports canonical errors
│
├── external/                  # Raw per-source request/response/error schemas (79 sources)
│   │                          #   cefi (binance/coinbase/okx/bybit/…), tradfi (databento/tardis/ibkr/yahoo/…),
│   │                          #   defi (hyperliquid/alchemy/thegraph/dydx/…), sports (betfair/pinnacle/polymarket/…),
│   │                          #   protocols (fix/nautilus/prime_broker/regulatory/protocol_sdks), cloud (gcp/aws/github)
│   │                          # Each source dir: schemas.py, normalize.py, examples/, mocks/
│
├── normalize_utils/           # Shared normalization helpers (ohlcv, tickers, orderbooks, trades,
│                              #   symbols, instruments, options, sports, onchain, tradfi, sides, … — 25 modules)
├── registry/                  # capability, endpoint_registry, endpoints, venue_constants,
│                              #   venue_rate_limits, provider_modes, quota_broker, venue_manifest/
├── config/                    # trading_validation.py
├── shared/                    # Reserved (currently empty)
└── testing/                   # conftest_helper, detect_cassette_drift, fault_injection,
                               #   network_block_plugin, vcr_endpoints (exported for consumers)
```

## Key design points

- **Root facade files.** Each domain has a root `.py` re-exporting its canonical types — consumers import
  `from unified_api_contracts.market import ...` for convenience.
- **Per-source `normalize.py`.** Each `external/{source}/` maps raw venue schemas to canonical types (74 `normalize.py`
  across the 79 source dirs); shared helpers live in `normalize_utils/`.
- **Registry** replaced the old top-level `venue_manifest/` (capability defs, endpoint registry, venue constants, rate
  limits, per-category manifest data).
- **Canonical domain split.** The old flat `canonical/{domain,execution,errors,normalize}.py` is now
  `canonical/domain/{...}/`, `canonical/crosscutting/`, and `canonical/errors/`.

## Deleted directories (no longer exist)

`canonical/normalize/` (→ per-source `external/{source}/normalize.py` + `normalize_utils/`), top-level `schemas/`
(→ `canonical/crosscutting/` or `external/`), `sports/` (→ `canonical/domain/sports/` + per-source dirs), `internal/`
(→ unified-internal-contracts), `external/{sports,venue_manifest,cloud_sdks,onchain,macro}/` (folded into individual
`external/{source}/` dirs or `registry/venue_manifest/`).

## Who tests what

- **Interfaces** (UMI, UOI, …): connectivity + validity of raw external schemas against live/VCR responses.
- **unified-api-contracts (this repo):** mapping (`normalize`), external contract availability, and typing; VCR replay is
  invoked by interfaces, not run in AC CI.

# Contributing to unified-api-contracts

## Package layout

- **external/** — Raw venue schemas (binance, databento, tardis, etc.). Add new venues here.
- **canonical/** — Canonical schemas and `normalize.py` for raw→canonical conversion.
- Service-to-service (internal) schemas live in **unified-internal-contracts**; AC is external + normalised only.

## Adding a new venue or API

1. **Create directory**  
   Add `unified_api_contracts/external/<venue>/` with:
   - `schemas.py` — Pydantic models for request/response (and errors, WebSocket payloads if applicable).
   - `examples/` — JSON (or CSV) examples; add manually or capture from the interface that uses the venue (interfaces hold API keys).
   - `mocks/` — VCR cassettes for tests (filter `authorization`, `x-api-key`, etc.).
   - Add a `normalize_*` function in `canonical/normalize.py` if the venue has trade/order types.
   - **VCR cassettes** under `mocks/` are recorded from the **six interfaces** (they hold API keys), not from AC scripts.

2. **Use Context7**  
   Before defining schemas, look up the provider’s official API/SDK docs (Context7 or web). If docs are insufficient, run minimal real API calls and capture responses to infer/refine schemas.

3. **Full surface**  
   Cover everything the exchange offers: market data, order feed, position feed, error/status types, WebSocket message schemas, FIX if supported, and corner cases (rate limits, pagination, symbol formats). Prefer more endpoints/schemas than we use today.

4. **Contract-vs-reality**  
   Add or extend `tests/test_contracts_vs_reality.py` so that example JSON validates against the Pydantic models. Live verification and VCR recording are done in the six interfaces (unified-trade-execution-interface, unified-sports-execution-interface, unified-reference-data-interface, unified-position-interface, unified-market-interface, unified-cloud-interface).

## Capturing examples and recording VCR

- **Validation against external APIs** and **VCR recording** are done in the **six interfaces** (unified-market-interface, unified-trade-execution-interface, unified-sports-execution-interface, unified-reference-data-interface, unified-position-interface, unified-cloud-interface); they hold API keys. Do not add or run live capture/record scripts in unified-api-contracts.
- For new venues: add schemas and `examples/*.json` in AC; the interface that integrates that venue runs live capture and VCR recording. **Interfaces contribute cassettes to AC’s `mocks/` via PR** (recommended) so one canonical location is used for replay and by all consumers. Filter headers (`authorization`, `x-api-key`) before committing. **SSOT:** `unified-trading-codex/02-data/vcr-cassette-ownership.md` (see “Contributing cassettes to AC mocks/ via PR”).

## Code and schema standards

- Pydantic v2 for all schemas; no `Any` for response shapes (use specific types or TypedDict).
- Follow workspace rules: UV for installs, ruff 0.15.0, quality gates. See unified-trading-codex and .cursor/rules.

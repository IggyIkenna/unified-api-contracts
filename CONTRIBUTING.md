# Contributing to api-contracts

## Package layout

- **api_contracts_external/** — Raw venue schemas (binance, databento, tardis, etc.). Add new venues here.
- **unified_normalised_contracts/** — Canonical schemas and `normalize.py` for raw→canonical conversion.
- **internal/** — Service-to-service schemas (will move to unified-internal-contracts in Phase 2).

## Adding a new venue or API

1. **Create directory**  
   Add `api_contracts/api_contracts_external/<venue>/` with:
   - `schemas.py` — Pydantic models for request/response (and errors, WebSocket payloads if applicable).
   - `examples/` — JSON (or CSV) examples; use `scripts/capture_api_responses.py` or per-API capture.
   - `mocks/` — VCR cassettes for tests (filter `authorization`, `x-api-key`, etc.).
   - Add a `normalize_*` function in `unified_normalised_contracts/normalize.py` if the venue has trade/order types.

2. **Use Context7**  
   Before defining schemas, look up the provider’s official API/SDK docs (Context7 or web). If docs are insufficient, run minimal real API calls and capture responses to infer/refine schemas.

3. **Full surface**  
   Cover everything the exchange offers: market data, order feed, position feed, error/status types, WebSocket message schemas, FIX if supported, and corner cases (rate limits, pagination, symbol formats). Prefer more endpoints/schemas than we use today.

4. **Contract-vs-reality**  
   Add or extend `tests/test_contracts_vs_reality.py` and `scripts/verify_contracts_vs_reality.py` so that example JSON (and optionally live requests) validate against the Pydantic models.

## Capturing examples

- Run `scripts/capture_api_responses.py` (or a per-API script) with small queries; write output to `api_contracts/api_contracts_external/<venue>/examples/`.
- Use env or Secret Manager for API keys; never commit secrets. Scripts should filter sensitive headers before writing anything to disk if recording for VCR.

## Recording VCR cassettes

- In repos that use cassettes (UMI, UOI, market-tick-data-handler), set `cassette_library_dir` to the shared api-contracts mocks path (e.g. `api-contracts/<api>/mocks/`).
- Use `record_mode='once'`, filter headers (`authorization`, `x-api-key`), and commit cassettes so tests do not call live APIs.

## Code and schema standards

- Pydantic v2 for all schemas; no `Any` for response shapes (use specific types or TypedDict).
- Follow workspace rules: UV for installs, ruff 0.15.0, quality gates. See unified-trading-codex and .cursor/rules.

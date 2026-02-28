# API Contracts Chain of Events

Single reference for the end-to-end flow from configuration through schema validation to adapter output. Interfaces (UMI, UOI) and services consume unified-api-contracts for type safety and validation.

## 1. Chain Overview

```
Config (UnifiedCloudConfig) → SDK/API call → unified-api-contracts schema validation → adapter output
```

1. **Config**: `UnifiedCloudConfig` (unified-config-interface) provides project ID, secret names, and environment. API keys resolved via `get_secret_client` (unified-trading-services).
2. **SDK/API call**: Adapters (UMI, UOI, market-tick-data-service) or scripts use SDKs (CCXT, databento, tardis-client, ib_insync) or direct HTTP to fetch data.
3. **Schema validation**: Raw responses are validated against Pydantic schemas in `unified_api_contracts/{venue}/schemas.py`.
4. **Adapter output**: Validated data is mapped to canonical types (UMI/UOI) or consumed directly by services.

## 2. Schema Validation Pipeline

### Flow: collect_responses → validate_schemas → unified_api_contracts canonical schemas

| Step | Script | Input | Output |
|------|--------|-------|--------|
| 1 | `scripts/collect_responses.py` | Live API (requires `LIVE_API_VERIFICATION=1`, API keys) | `collected_responses/{venue}/*.json` |
| 2 | `scripts/validate_schemas.py` | `collected_responses/` | Validation report; optionally `--generate-schemas` → `generated_schemas/` |
| 3 | Manual review | `generated_schemas/` | Promote to `unified_api_contracts/{venue}/schemas.py` |

**Commands:**

```bash
# Collect real API responses (requires LIVE_API_VERIFICATION=1 and API keys)
LIVE_API_VERIFICATION=1 uv run python scripts/collect_responses.py
LIVE_API_VERIFICATION=1 uv run python scripts/collect_responses.py --venue binance

# Validate schemas against collected responses
uv run python scripts/validate_schemas.py
uv run python scripts/validate_schemas.py --venue coinbase

# Generate draft schemas from responses
uv run python scripts/validate_schemas.py --generate-schemas --venue coinbase
```

**Data flow:**

- `collected_responses/` — Raw JSON from live APIs (gitignored or committed as samples).
- `generated_schemas/` — Auto-generated Pydantic drafts; review and promote to `unified_api_contracts/`.
- `unified_api_contracts/` — Canonical schemas; single source of truth for UMI, UOI, and services.

## 3. VCR Flow

### record_vcr_cassettes → test_vcr_replay

| Step | Script/Test | Purpose |
|------|-------------|---------|
| 1 | `scripts/record_vcr_cassettes.py` | Record live HTTP requests to `unified_api_contracts/<venue>/mocks/*.yaml` |
| 2 | `tests/test_vcr_replay.py` | Replay cassettes and validate responses against venue schemas |

**Commands:**

```bash
# Record cassettes (requires network; secrets filtered in output)
uv run python scripts/record_vcr_cassettes.py
uv run python scripts/record_vcr_cassettes.py --venue binance

# Replay (CI; no live calls)
uv run pytest tests/test_vcr_replay.py -v
```

**Config:** `unified_api_contracts/vcr_endpoints.py` defines `VCR_ENDPOINTS` (url, method, cassette_name, response_path, schema_class, key_env). See [MOCKS_AND_VCR.md](MOCKS_AND_VCR.md) and [VCR_SCHEMA_ALIGNMENT.md](VCR_SCHEMA_ALIGNMENT.md).

## 4. Live Verification

When `LIVE_API_VERIFICATION=1`:

- `scripts/collect_responses.py` — Fetches real API responses for schema validation.
- `scripts/verify_contracts_vs_reality_live.py` — Validates contracts against live APIs using same config and Secret Manager as UMI/UOI.
- `tests/test_contracts_vs_reality.py` — Runs live checks when env is set.

**Setup:**

```bash
uv pip install -e ../unified-trading-services -e ../unified-config-interface
LIVE_API_VERIFICATION=1 uv run python scripts/verify_contracts_vs_reality_live.py
```

## 5. Version Alignment

### SCHEMA_VERSIONS.md

Tracks per-venue API/SDK versions, endpoint→schema mappings, and recommended pins. See [SCHEMA_VERSIONS.md](../SCHEMA_VERSIONS.md).

### [schema-validation] Dependencies

Install: `uv pip install -e ".[schema-validation]"`

| Package | Version | Purpose |
|---------|---------|---------|
| pydantic | >=2.0,<3.0 | Schema validation |
| requests | >=2.31.0 | collect_responses HTTP |
| databento | >=0.32.0 | Databento API validation |
| tardis-client | >=1.3.7 | Tardis HTTP API validation |
| ccxt | >=4.5.24,<5.0.0 | CCXT unified response validation |
| ib_insync | >=0.9.86 | IBKR TWS schema validation |

### check_sdk_version_alignment.py

Verifies interface repos (UMI, UTEI, URDI) use SDK versions that overlap with unified-api-contracts `[schema-validation]` pins.

```bash
uv run python scripts/check_sdk_version_alignment.py
```

## 6. Key Data Structures

### ENDPOINT_SCHEMA_MAP

`unified_api_contracts/endpoints.py` — `(venue, endpoint) → schema_class_name`. Used by collect_responses, validate_schemas, VCR recording, and schema validation.

Example: `("binance", "ticker")` → `"BinanceTicker"`.

### BASE_URLS

`unified_api_contracts/endpoints.py` — Per-venue REST base URLs (e.g. `binance` → `https://api.binance.com/api/v3`).

### venue_manifest

`unified_api_contracts/venue_manifest.py` — `VENUE_MANIFEST`: per-venue `has_rest`, `has_websocket`, `has_fix`, `config_secret_field`, `response_schema_classes`, `error_schema_classes`, `example_schema_map`. Align with [INDEX.md](INDEX.md).

## 7. Consumer Model

| Consumer | Uses |
|----------|------|
| **Interfaces** (UMI, UOI) | unified-api-contracts schemas for validation; map to canonical types |
| **Services** | unified-api-contracts directly or via interfaces |
| **market-tick-data-service** | unified-api-contracts (Tardis, Databento schemas) |
| **instruments-service** | unified-api-contracts (Databento, Tardis) |

Path dependency: `../unified-api-contracts` in pyproject.toml. See [README](../README.md) and [CONTRIBUTING](../CONTRIBUTING.md).

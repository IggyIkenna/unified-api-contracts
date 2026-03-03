# Configuration

Environment and config for consumers of unified-api-contracts.

## Consumers (UMI / UOI / services)

- Use **path dependency** `../unified-api-contracts` (see workspace path-dependency-ci and [README — Consuming from UMI / UOI](../README.md#consuming-from-umi--uoi)).
- No package-specific env vars required for import; config is in the consuming service (e.g. `UnifiedCloudConfig`, API keys via Secret Manager).

## This repo (AC only)

- **No API keys or live verification in AC.** Quality gates run schema and example validation only; no collection or VCR recording. **Live validation and VCR recording** are done in the six interfaces (they hold API keys).
- **`GCP_PROJECT_ID`** — Not required for AC quality gates (replay-only tests).

See [CONTRIBUTING.md](../CONTRIBUTING.md) and [docs/API_CONTRACTS_CHAIN_OF_EVENTS.md](API_CONTRACTS_CHAIN_OF_EVENTS.md) for the full chain (config → SDK → schema validation → adapter output).

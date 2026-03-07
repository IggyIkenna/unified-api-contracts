# Package Layout and Scope: API vs Internal Contracts

**SSOT:** This doc defines the target layout for `unified-api-contracts` and the rule for what belongs here vs `unified-internal-contracts`. See also `unified-trading-pm/workspace-manifest.json` (arch_tier, L6 and below) and codex `02-data/vcr-cassette-ownership.md` (circular dependency rules).

## Dependency rule (blocking)

**unified-api-contracts must not import from unified-internal-contracts.** AC is a Tier 0 leaf; it has no `unified-*` dependencies. Internal contracts can depend on AC; AC cannot depend on UIC.

Therefore **all schemas needed for mapping must remain in unified-api-contracts**, including:

- Canonical instrument IDs and venue identifiers used in normalization
- Venue enums / manifest used by `normalize.py` and external→canonical mapping
- Any type that `unified_normalised_contracts` or venue adapters need to produce canonical output

If a schema is only used for internal service-to-service contracts and is not needed for external API mapping, it belongs in unified-internal-contracts. If it is needed for mapping (or for external API request/response typing), it stays in AC.

## Scope rule

- **unified-api-contracts** = **external API contracts** + **mapping surface**. Schemas for third-party APIs (exchanges, data providers, cloud SDKs) and anything required to map them to canonical types (venues, canonical IDs, normalised types). Interfaces own connectivity; this repo owns **mapping** (normalize) and **external contract availability and typing**.
- **unified-internal-contracts** = **internal contracts only**. Schemas used to contract our codebase to our codebase (no external API surface). If a schema is **not** used for any external API contract and **not** needed for mapping, it does **not** belong in api-contracts — move or keep it in internal-contracts.

**Check order:** (1) Is it needed for mapping or external contract? If yes → AC. (2) Is it used for external contract? If no and not needed for mapping → internal-contracts. (3) Is it imported by repos at/below L6 only for internal use? If yes and not external → internal-contracts.

## Target package layout

Top-level packages under `unified_api_contracts/` should be grouped into three buckets:

| Bucket                             | Purpose                                       | Current / target contents                                                                                                                                                                            |
| ---------------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **shared**                         | Cross-venue shared types, errors, quotas      | `shared/` (error_action, quota_types, etc.). Move generic bits from `schemas/`, `fix/`, `regulatory/` here where they are cross-venue and external.                                                  |
| **unified_api_contracts_external** | Raw per-venue request/response/errors         | All venue-specific schemas (binance, databento, ccxt, sports sources, etc.). `unified_normalised_contracts` lives alongside because this package **owns the schema mapping** (external → canonical). |
| **unified_normalised_contracts**   | Canonical domain/execution/errors + normalize | Already under `unified_api_contracts_external` conceptually; owns `normalize.py` and canonical types.                                                                                                |

**Current top-level packages to rationalize:** `nautilus`, `prime_broker`, `fix`, `regulatory`, `schemas`, `sports`, `venue_manifest`. Each should either:

- Live under **shared** (if cross-venue and external),
- Live under **unified_api_contracts_external** (if venue-specific or mapping-related), or
- Move to **unified-internal-contracts** (if internal-only per the scope rule above).

The **schemas/** directory should be split: external-facing parts → shared or unified_api_contracts_external; internal-only → unified-internal-contracts.

## Who tests what

- **Interfaces** (UMI, UOI, etc.): Connectivity and **validity of raw external schemas** against live or VCR-recorded responses.
- **unified-api-contracts (this repo):** **Mapping** (normalize), **external contract availability**, and **typing**; VCR replay is invoked by interfaces, not run in AC CI.

---

## Refactor status

**Not yet done.** This doc describes the _intended_ layout and rules. The physical refactor (moving top-level packages into shared / unified_api_contracts_external / unified_normalised_contracts, and moving internal-only schemas to unified-internal-contracts) is pending. When doing it: (1) ensure nothing that mapping depends on (canonical ids, venues, normalised types) is moved to UIC, and (2) keep AC free of any `unified_internal_contracts` import.

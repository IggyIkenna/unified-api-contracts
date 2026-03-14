# Architecture

**SSOT for constraints and layout:** unified-trading-codex/02-data/contracts-scope-and-layout.md. **Full layout and refactor plan:** [PACKAGE_LAYOUT_AND_SCOPE.md](PACKAGE_LAYOUT_AND_SCOPE.md).

Package layout and the split between external (venue-specific), normalised (canonical), and shared contracts.

## Placement rule (where new modules go)

| Content type                                                          | Location                      | Examples                                                                                                                                                 |
| --------------------------------------------------------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Raw schemas for an external API, protocol, or venue**               | **`external/<name>/`**        | binance, databento, ccxt, yahoo_finance, **prime_broker**, **fix**, **nautilus** (one dir per external surface).                                         |
| **Canonical domain/execution/error types**                            | **`canonical/`**              | domain.py, execution.py, errors.py, normalize.py.                                                                                                        |
| **Shared cross-venue schemas** (not mirroring a single external API)  | **`schemas/`**                | risk, latency, analytics, protocol_sdks, **regulatory**.                                                                                                 |
| **Small shared types** (enums, actions) used across the package       | **`shared/`**                 | quota_types, error_action.                                                                                                                               |
| **Venue/contract manifest** (which venues, endpoints, schema classes) | **`venue_manifest/`** at root | Package infrastructure; not external API or shared schema.                                                                                               |
| **Sports domain** (canonical + per-source)                            | **`sports/`** at root         | Exception: combines canonical types (`sports/canonical`) and source-specific schemas (`sports/sources`); long-term could align to external + normalised. |

**Internal** (service-to-service) schemas live in **unified-internal-contracts**; AC is external + normalised only.

## Current top-level folders vs rule

| Folder at root     | Should live under        | Notes                                                         |
| ------------------ | ------------------------ | ------------------------------------------------------------- |
| **prime_broker**   | `external/prime_broker`  | External API (HiddenRoad, Talos, etc.).                       |
| **fix**            | `external/fix`           | FIX protocol (external).                                      |
| **nautilus**       | `external/nautilus`      | NautilusTrader engine (external).                             |
| **regulatory**     | `schemas/regulatory`     | Shared report formats (MiFID II, EMIR).                       |
| **schemas**        | (already correct)        | Shared cross-venue.                                           |
| **shared**         | (already correct)        | Small shared types.                                           |
| **sports**         | (exception at root)      | Domain namespace: canonical + sources; optional future split. |
| **venue_manifest** | (infrastructure at root) | Manifest/metadata; not a schema category.                     |

Migration of **prime_broker**, **fix**, **nautilus** into `external/` and **regulatory** into `schemas/regulatory` would align the tree with the rule; all imports and `venue_manifest/internal_services.py` module paths would need updating. Until then, the rule above applies to **new** modules.

## Package layout

- **`unified_api_contracts/`** — Root package.
  - **`external/`** — Raw request/response/error schemas per venue or external system (Binance, Databento, Tardis, CCXT, etc.). Per-venue dirs contain `schemas.py`, `examples/`, `mocks/` (VCR cassettes; recording done in interfaces). **prime_broker**, **fix**, **nautilus** belong here per rule (currently at root).
  - **`canonical/`** — Canonical domain, execution, and error types (self-contained; no internal imports).
  - **`schemas/`** — Shared cross-venue schemas (risk, latency, analytics, regulatory, etc.). **regulatory** belongs here per rule (currently at root).
  - **`shared/`** — Small shared types (enums, actions).
  - **`venue_manifest/`** — Manifest of venues and contract coverage (infrastructure).
  - **`sports/`** — Sports domain (canonical + sources); exception at root.
  - Internal service-to-service schemas live in **unified-internal-contracts**; AC is external + normalised only.

## External vs normalised

- **External**: Venue- or protocol-specific Pydantic models matching provider APIs. Use for parsing and validating raw API responses before mapping to canonical types.
- **Normalised**: Canonical types used by UMI/UOI and services. See `unified_api_contracts.canonical` and [README Structure](../README.md#structure), [docs/INDEX.md](INDEX.md), [docs/CROSS_VENUE_MATRIX.md](CROSS_VENUE_MATRIX.md).

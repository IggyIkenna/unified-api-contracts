# Quality Gate Bypass Audit

This document records all intentional bypasses of quality gate rules in `unified-api-contracts`.
Every bypass must be justified and tracked here per workspace rules.

---

## 2.1 Ruff Config Bypasses

### N815 — camelCase field names in schemas.py files

**Scope:** `unified_api_contracts/**/schemas.py`
**Rule:** `N815` (mixed-case variable name in class scope)
**Reason:** External API field names are camelCase (Binance: `orderId`, OKX: `instId`, etc.).
Renaming would break deserialization when using `model_validate(raw_api_response)`.
**Config:** `[tool.ruff.lint.per-file-ignores] "unified_api_contracts/**/schemas.py" = ["N815"]`

### N803 — camelCase parameter names in cloud_sdks

**Scope:** `unified_api_contracts/cloud_sdks/*.py`
**Rule:** `N803` (argument name should be lowercase)
**Reason:** Protocol stubs mirror GCP/AWS SDK interfaces which use camelCase.
**Config:** `[tool.ruff.lint.per-file-ignores] "unified_api_contracts/cloud_sdks/*.py" = ["N803", "N815"]`

### External API Field Name Preservation

**Scope:** `unified_api_contracts/unified_api_contracts_external/ibkr/schemas.py`
**Rule:** Field naming comments
**Reason:** IBKR TWS API exposes both `bid`/`ask` and `bid_price`/`ask_price` field names for bond market data. Both fields are preserved in the schema to match the raw API surface exactly. Comments document the API field mapping for maintainability — these are not backward-compatibility shims but external API shape mirrors.

### E741 — ambiguous variable name `l` in API schemas

**Scope:** `unified_api_contracts/binance/schemas.py`, `unified_api_contracts/okx/schemas.py`
**Rule:** `E741` (ambiguous variable name)
**Reason:** Field name `l` (lowercase L) is mandated by Binance EAPI options stream
(`BinanceOptionTicker.l`) and OKX candle stream (`OKXCandleWS.l`). Cannot rename.
**Suppression:** `# noqa: E741` inline on affected fields.

---

## 2.2 basedpyright Relaxations

`[tool.basedpyright]` uses `typeCheckingMode = "strict"` because this is a schema
contract library that benefits from strict type checking.

The following `reportUnknown*` rules are set to `"error"`:

- `reportUnknownVariableType`

The following `reportUnknown*` rules are set to `"warning"` rather than `"error"` (relaxed for external API schema definitions that mirror third-party SDK types):

- `reportUnknownParameterType`
- `reportUnknownMemberType`

---

## 2.2b Any-type Decisions (resolved)

| File                                                                   | Fields                                           | Resolution                                                                                                                                             |
| ---------------------------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `unified_api_contracts/domain_config.py`                               | `config: dict[str, Any]` in all Protocol classes | Changed to `dict[str, object]` — avoids `Any`, preserves extensibility; Protocol implementors can still satisfy with `dict[str, object]` or narrower   |
| `unified_api_contracts/unified_api_contracts_external/ibkr/schemas.py` | `contract`, `info` fields                        | Changed to `dict[str, str \| int \| float \| bool \| None]` — covers all TWS API primitive types                                                       |
| `unified_api_contracts/venue_manifest/internal_services.py`            | `INTERNAL_CONTRACTS: dict[str, Any]`             | Changed to `dict[str, ContractEntry]` using a `TypedDict` with `total=False` for optional fields — all known entry shapes captured; no `Any` remaining |

---

## 2.3 Known Pre-existing Type Violations (basedpyright warnings)

These violations existed before the Phase 1a–1e schema additions and are tracked here
pending a future refactor pass.

| File                                                                              | Lines | Rule                                                       | Description                                                                                                                                                                                                                                                                                                                           | Action                                                                          |
| --------------------------------------------------------------------------------- | ----- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `unified_api_contracts/coinbase/schemas.py`                                       | 53–61 | `reportUnknownParameterType` / `reportUnknownArgumentType` | `CoinbaseCandle.from_list(cls, candle_data: list)` uses untyped `list` parameter. Subscript indexing on untyped list produces unknown-type arguments.                                                                                                                                                                                 | Phase 1b: type as `list[int \| str]` and use explicit `Decimal(str(...))` casts |
| `unified_api_contracts/vcr_endpoints.py`                                          | 50    | `reportUnknownParameterType`                               | `json_body: dict[Unknown, Unknown] \| None` — VCR infrastructure uses untyped JSON dicts for mock bodies.                                                                                                                                                                                                                             | Acceptable for test infrastructure; document as permanent exception             |
| `unified_api_contracts/unified_api_contracts_external/venue_manifest/__init__.py` | 35    | `reportAssignmentType`                                     | VENUE_MANIFEST dict merges submodule dicts whose `VenueContract` TypedDicts are locally defined (cefi.VenueContract, data_providers.VenueContract, etc.) — basedpyright cannot unify them with the top-level VenueContract. Fixed with `cast()` at merge site; root fix requires moving VenueContract to shared \_types.py (Phase 2). |
| `unified_api_contracts/unified_api_contracts_external/cloud_sdks/schemas/iam.py`  | 191   | `reportUnknownParameterType`                               | OAuth2Error(code, http_status) — code/http_status from untyped exception handler.                                                                                                                                                                                                                                                     | Mirror GCP IAM SDK; add explicit types in future cloud_sdks hardening           |

---

## 2.4 Test Skips

None currently.

---

## 2.5 File Size Exceptions (MAX_FILE_LINES=900)

| File                           | Lines | Reason                                                                                                                                                                     |
| ------------------------------ | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sports/canonical/features.py` | ~1196 | Pure Pydantic schema (`SportsFeatureVector`) with ~998 sport feature fields; splitting a single dataclass across files would reduce readability with no structural benefit |

**Config:** `scripts/quality-gates.sh` — `continue` for these paths when under threshold.

---

## 2.6 Hardening Decisions

- `unified-api-contracts` has zero production service code — no retry logic, no GCS writes,
  no pubsub. Error handling rules (no bare `except:`, `@handle_api_errors`) do not
  apply here. The library is pure schema definitions and VCR mocks.
- `os.getenv()` is used only in `scripts/` (not in `unified_api_contracts/` source code).
  This is acceptable for CLI scripts that run outside the service config system.

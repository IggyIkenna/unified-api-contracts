# Quality Gate Bypass Audit

This document records all intentional bypasses of quality gate rules in `api-contracts`.
Every bypass must be justified and tracked here per workspace rules.

---

## 2.1 Ruff Config Bypasses

### N815 — camelCase field names in schemas.py files
**Scope:** `api_contracts/**/schemas.py`
**Rule:** `N815` (mixed-case variable name in class scope)
**Reason:** External API field names are camelCase (Binance: `orderId`, OKX: `instId`, etc.).
Renaming would break deserialization when using `model_validate(raw_api_response)`.
**Config:** `[tool.ruff.lint.per-file-ignores] "api_contracts/**/schemas.py" = ["N815"]`

### N803 — camelCase parameter names in cloud_sdks
**Scope:** `api_contracts/cloud_sdks/*.py`
**Rule:** `N803` (argument name should be lowercase)
**Reason:** Protocol stubs mirror GCP/AWS SDK interfaces which use camelCase.
**Config:** `[tool.ruff.lint.per-file-ignores] "api_contracts/cloud_sdks/*.py" = ["N803", "N815"]`

### E741 — ambiguous variable name `l` in API schemas
**Scope:** `api_contracts/binance/schemas.py`, `api_contracts/okx/schemas.py`
**Rule:** `E741` (ambiguous variable name)
**Reason:** Field name `l` (lowercase L) is mandated by Binance EAPI options stream
(`BinanceOptionTicker.l`) and OKX candle stream (`OKXCandleWS.l`). Cannot rename.
**Suppression:** `# noqa: E741` inline on affected fields.

---

## 2.2 basedpyright Relaxations

`[tool.basedpyright]` uses `typeCheckingMode = "standard"` (not "strict") because this
is a schema contract library — strict mode would require TypedDict for every `dict` field
in api responses that we cannot fully type without VCR-verified field enumerations.

The following `reportUnknown*` rules are set to `"warning"` rather than `"error"`:
- `reportUnknownVariableType`
- `reportUnknownParameterType`
- `reportUnknownMemberType`

---

## 2.3 Known Pre-existing Type Violations (basedpyright warnings)

These violations existed before the Phase 1a–1e schema additions and are tracked here
pending a future refactor pass.

| File | Lines | Rule | Description | Action |
|------|-------|------|-------------|--------|
| `api_contracts/coinbase/schemas.py` | 53–61 | `reportUnknownParameterType` / `reportUnknownArgumentType` | `CoinbaseCandle.from_list(cls, candle_data: list)` uses untyped `list` parameter. Subscript indexing on untyped list produces unknown-type arguments. | Phase 1b: type as `list[int \| str]` and use explicit `Decimal(str(...))` casts |
| `api_contracts/kraken/schemas.py` | 96–103 | `reportUnknownArgumentType` | `KrakenOHLCV.from_list()` indexing untyped list produces 8 unknown-type arguments. | Phase 1b: same fix pattern as Coinbase |
| `api_contracts/vcr_endpoints.py` | 50 | `reportUnknownParameterType` | `json_body: dict[Unknown, Unknown] \| None` — VCR infrastructure uses untyped JSON dicts for mock bodies. | Acceptable for test infrastructure; document as permanent exception |

---

## 2.4 Test Skips

None currently.

---

## 2.5 Hardening Decisions

- `api-contracts` has zero production service code — no retry logic, no GCS writes,
  no pubsub. Error handling rules (no bare `except:`, `@handle_api_errors`) do not
  apply here. The library is pure schema definitions and VCR mocks.
- `os.getenv()` is used only in `scripts/` (not in `api_contracts/` source code).
  This is acceptable for CLI scripts that run outside the service config system.

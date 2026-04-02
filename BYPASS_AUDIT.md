# BYPASS_AUDIT.md — unified-api-contracts

This file documents intentional ruff rule suppressions in this repo. All suppressions are
reviewed and approved. Custom `# noqa: qg-*` codes are self-documenting inline.

## F401 — Unused imports (19 instances)

**Rule**: `F401` — module imported but unused
**Suppressed in**: facade modules (`__init__.py`, root facades `market.py`, `execution.py`, etc.)
**Reason**: UAC uses a facade pattern where root modules re-export symbols from sub-packages for
consumer convenience. Ruff sees these as "unused" because they are only used as re-exports.
The alternative is `__all__` on every facade, but the existing `# noqa: F401` pattern is
consistent across all facade layers.
**Approved**: Yes — inherent to UAC's citadel facade architecture.

## E402 — Module level import not at top (15 instances)

**Rule**: `E402` — module level import not at top of file
**Suppressed in**: domain facade modules and registry loaders
**Reason**: UAC's domain facades perform conditional registration of normalizers and schema
validators at import time. Some imports must happen after the registry is initialized, which
requires a specific import order that violates E402. Restructuring would require splitting the
registry initialization into a separate bootstrap phase.
**Approved**: Yes — required by UAC's lazy normalization registry pattern.

## F403 — Star import (2 instances)

**Rule**: `F403` — `from module import *` used
**Suppressed in**: facade re-export modules
**Reason**: UAC's top-level facades use `import *` from sub-packages to flatten the namespace
for consumers. This is intentional — consumers use `from unified_api_contracts import X`
without knowing the sub-package layout.
**Approved**: Yes — explicit in UAC architecture docs. Mitigated by `__all__` in sub-packages.

## E741 — Ambiguous variable name (1 instance)

**Rule**: `E741` — ambiguous variable name (`l`, `O`, `I`)
**Suppressed in**: financial math utilities
**Reason**: Financial domain uses `l` as standard notation for certain parameters following
industry-standard mathematical conventions (e.g., log-return `l`).
**Approved**: Case-by-case. Annotate with inline comment explaining the variable meaning.

## E731 — Lambda assignment (1 instance)

**Rule**: `E731` — do not assign a lambda expression
**Suppressed in**: functional transform utilities
**Reason**: Lambda is used as a mapping value in a dict of transformers where a full `def`
would be unnecessarily verbose. The lambda is not exported.
**Approved**: Yes — one-off, not a pattern.

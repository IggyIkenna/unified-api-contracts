# AGENTS.md

## Cursor Cloud specific instructions

This is a **pure Python schema library** (no running services, no databases, no Docker). It provides Pydantic v2 schemas for external trading APIs.

### Requirements

- **Python 3.13** (strictly `>=3.13,<3.14` — enforced by quality gates)
- **uv** package manager (lockfile: `uv.lock`)
- **ripgrep** (`rg`) — required by `scripts/quality-gates.sh`

### Key commands

Commands are documented in the `Makefile` and `README.md`. Quick reference:

| Task               | Command                                          |
| ------------------ | ------------------------------------------------ |
| **Full setup**     | `bash scripts/setup.sh` or `make setup`          |
| Verify env         | `bash scripts/setup.sh --check`                  |
| Install deps       | `uv pip install -e ".[dev]"`                     |
| Lint (source)      | `ruff check unified_api_contracts/`              |
| Lint + fix         | `ruff check --fix unified_api_contracts/ tests/` |
| Unit tests         | `pytest tests/unit/ -v -n 2 --timeout=60`        |
| All tests          | `pytest tests/ -v`                               |
| Type check         | `basedpyright unified_api_contracts/`            |
| Full quality gates | `bash scripts/quality-gates.sh`                  |

### Non-obvious caveats

- **Use `uv sync`, not `uv pip install`** — `uv sync --extra dev` reads `uv.lock` and is a 16ms no-op when nothing changed. `uv pip install` ignores the lockfile and resolves from scratch. The setup script uses `uv sync`.
- **Quality gates run `tests/unit/` only** — the full `tests/` directory includes alignment tests (`test_ac_uic_alignment.py`) that require the sibling `unified_internal_contracts` repo, which is unavailable in isolation. Expect ~79 failures from that file when running `pytest tests/`.
- **Pre-existing lint errors in tests** — `tests/test_ac_uic_alignment.py` has ~42 `N814` naming convention violations. These are pre-existing and will cause `ruff check` on tests to fail; the source directory (`unified_api_contracts/`) lints cleanly.
- **basedpyright has pre-existing errors** — ~287 `reportMissingTypeArgument` errors across venue schemas. These are pre-existing in the codebase.
- The `.venv` is NOT committed (`.gitignore`). The `uv.lock` IS committed. `scripts/setup.sh` creates the venv from the lockfile.
- Always activate the venv before running commands: `source .venv/bin/activate`.

---

## Path to 100% test completion for unified-api-contracts

### Current state (baseline)

| Metric                        | Value                                      |
| ----------------------------- | ------------------------------------------ |
| Total tests collected         | **573**                                    |
| Passing (`PASSED`)            | **485**                                    |
| Failing (`FAILED`)            | **79** (all in `test_ac_uic_alignment.py`) |
| Expected failures (`xfailed`) | **4** (3 in alignment, 1 elsewhere)        |
| Skipped                       | **5** (live API, VCR placeholder, etc.)    |
| **Effective pass rate**       | **84.6%** (485/573)                        |

Every single failure is caused by one thing: `tests/test_ac_uic_alignment.py` imports `unified_internal_contracts`, which is not (and must not be) a dependency of this Tier 0 library.

### The architectural problem

`unified-api-contracts` is **Tier 0** — a leaf library with zero workspace/path dependencies. Its `pyproject.toml` enforces this:

```
LOCAL_DEPS=()  # Tier 0: zero path dependencies
```

However, `tests/test_ac_uic_alignment.py` contains 82 tests that `from unified_internal_contracts import ...` to compare schemas across the two libraries. This creates three problems:

1. **Always-failing tests**: These 79 tests can never pass in API contracts' own CI, quality gates, or isolated dev environments because `unified_internal_contracts` is not installed and cannot be added without breaking Tier 0.
2. **Circular dependency risk**: If `unified_internal_contracts` already depends on `unified_api_contracts` (it should — UIC is a higher-tier consumer), then adding UIC as a test dependency of API contracts creates a circular dependency.
3. **Lint violations**: The test file has 42 `N814` naming convention errors (`CamelCase imported as CONSTANT`), which cause `ruff check` on the `tests/` directory to fail. The quality gates script works around this by only running `tests/unit/`.

### The fix: move alignment tests to unified-internal-contracts

Since `unified-internal-contracts` already has `unified-api-contracts` as a dependency, UIC is the correct place for cross-library alignment tests. The dependency arrow flows:

```
unified-api-contracts (Tier 0, leaf)
        ↑
unified-internal-contracts (Tier 1, depends on AC)
        ↑
unified-trading-services, UMI, UOI (Tier 2+)
```

Alignment tests belong in the **higher-tier repo** that already has both libraries available. Concretely:

#### Step 1: Move `test_ac_uic_alignment.py` to `unified-internal-contracts`

Move the entire file `tests/test_ac_uic_alignment.py` (82 tests) from `unified-api-contracts` to `unified-internal-contracts/tests/test_ac_uic_alignment.py`. The tests require zero changes — they already import from both `unified_api_contracts.internal.*` and `unified_internal_contracts.*`.

**What moves (all 82 tests across 10 test classes):**

| Test class                       | Tests                | What it checks                                                                                                                                          |
| -------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TestMLEnumAlignment`            | 4                    | `ModelType`, `TargetType` enum member parity                                                                                                            |
| `TestMLModelAlignment`           | 8                    | `ModelVariantConfig`, `ModelMetadata`, `MLConfigDict`, `InferenceRequest/Result`, `TrainingJobRequest/Result`, `TrainingPeriod` field parity            |
| `TestEventsEnumAlignment`        | 3                    | `LifecycleEventType`, `EventSeverity`, `ServiceMode` enum parity                                                                                        |
| `TestEventsModelAlignment`       | 19                   | 19 event detail/envelope models field parity                                                                                                            |
| `TestEventsModuleLevelConstants` | 1 (xfail)            | `REQUIRED_EVENT_FIELDS` presence in AC                                                                                                                  |
| `TestFeaturesAlignment`          | 4 + 1 xfail + 1 skip | `DeltaOneFeatureRecord`, `OptionsIvRecord`, `FuturesTermStructureRecord`, `FeatureSnapshotRequest`, `CrossTimeframeFeatures`, `CrossInstrumentFeatures` |
| `TestPubsubAlignment`            | 16                   | `InternalPubSubTopic` + 15 message models field parity                                                                                                  |
| `TestRiskAlignment`              | 14                   | `RiskStatus`, `AlertType`, `PositionSide` enums + 11 risk models                                                                                        |
| `TestErrorSchemaAlignment`       | 5 (1 xfail)          | `ErrorCategory`, `ErrorSeverity`, `ErrorRecoveryStrategy`, `ErrorContext`, `EnhancedError`                                                              |
| `TestMessagingTopicAlignment`    | 2                    | `MessagingTopic` ↔ `InternalPubSubTopic` parity                                                                                                         |

#### Step 2: Delete `test_ac_uic_alignment.py` from unified-api-contracts

After the move is confirmed working in UIC's test suite, delete the file from this repo.

#### Step 3: Verify unified-api-contracts reaches 100%

After removing the file, the test suite should look like:

| Metric        | Before | After                           |
| ------------- | ------ | ------------------------------- |
| Total tests   | 573    | 491                             |
| Passing       | 485    | 485                             |
| Failing       | 79     | **0**                           |
| xfailed       | 4      | 1                               |
| Skipped       | 5      | 5                               |
| **Pass rate** | 84.6%  | **100%** (excluding xfail/skip) |

The 42 `N814` ruff lint errors also disappear, allowing `ruff check` to pass on the full `tests/` directory.

#### Step 4: Update quality gates to run full test suite

Once alignment tests are gone, `scripts/quality-gates.sh` can run `tests/` instead of `tests/unit/`:

```bash
# Before (line 113 of quality-gates.sh):
$PYTHON_CMD -m pytest tests/unit/ $PARGS $COV || exit 1

# After:
$PYTHON_CMD -m pytest tests/ $PARGS $COV || exit 1
```

This picks up the VCR tests, schema validation tests, contract coverage tests, and normalization tests that currently only run outside quality gates.

### Additional items for full clean-up (optional, lower priority)

| Item                                                                          | Files affected                                 | Impact                                                                                                                                                            |
| ----------------------------------------------------------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Add `httpx` to `[dev]` dependencies                                           | `pyproject.toml`                               | VCR tests (`tests/vcr/`) currently require manual `uv pip install httpx`; adding it to dev deps makes them always runnable                                        |
| Fix basedpyright `reportMissingTypeArgument`                                  | ~287 instances across venue `schemas.py` files | Change `dict` → `dict[str, ...]`, `list` → `list[...]` for strict type checking                                                                                   |
| Resolve 3 `xfail` items in alignment tests (before moving to UIC)             | `test_ac_uic_alignment.py`                     | `REQUIRED_EVENT_FIELDS`, `CrossTimeframeFeatures`, `EnhancedError.correlation_id` — known drift that AC should either adopt or document as intentional divergence |
| Consolidate `unified_api_contracts/internal/` vs `unified_internal_contracts` | `internal/` module                             | Long-term: decide whether AC's `internal/` module is the SSOT (and UIC re-exports), or UIC is the SSOT (and AC drops the mirror). Eliminates drift entirely.      |

### Summary

The single highest-impact change is **moving `test_ac_uic_alignment.py` from this repo to `unified-internal-contracts`**. This:

- Takes `unified-api-contracts` from 84.6% → **100% pass rate**
- Eliminates all 42 ruff `N814` lint violations
- Respects Tier 0 architecture (no upward dependencies, not even in tests)
- Avoids circular dependency risk
- Tests still run — just in the repo that actually has both libraries available
- Alignment tests in UIC will catch drift in either direction on every UIC CI run

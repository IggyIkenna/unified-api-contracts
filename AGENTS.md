# AGENTS.md

## Cursor Cloud specific instructions

This is a **pure Python schema library** (no running services, no databases, no Docker). It provides Pydantic v2 schemas for external trading APIs.

### Requirements

- **Python 3.13** (strictly `>=3.13,<3.14` — enforced by quality gates)
- **uv** package manager (lockfile: `uv.lock`)
- **ripgrep** (`rg`) — required by `scripts/quality-gates.sh`

### Key commands

Commands are documented in the `Makefile` and `README.md`. Quick reference:

| Task | Command |
|------|---------|
| Install deps | `uv pip install -e ".[dev]"` |
| Lint (source) | `ruff check unified_api_contracts/` |
| Lint + fix | `ruff check --fix unified_api_contracts/ tests/` |
| Unit tests | `pytest tests/unit/ -v -n 2 --timeout=60` |
| All tests | `pytest tests/ -v` |
| Type check | `basedpyright unified_api_contracts/` |
| Full quality gates | `bash scripts/quality-gates.sh` |

### Non-obvious caveats

- **Quality gates run `tests/unit/` only** — the full `tests/` directory includes alignment tests (`test_ac_uic_alignment.py`) that require the sibling `unified_internal_contracts` repo, which is unavailable in isolation. Expect ~79 failures from that file when running `pytest tests/`.
- **VCR tests require `httpx`** — not in `[dev]` dependencies but needed for `tests/vcr/`. Install with `uv pip install httpx` if you need those tests.
- **Pre-existing lint errors in tests** — `tests/test_ac_uic_alignment.py` has ~42 `N814` naming convention violations. These are pre-existing and will cause `ruff check` on tests to fail; the source directory (`unified_api_contracts/`) lints cleanly.
- **basedpyright has pre-existing errors** — ~287 `reportMissingTypeArgument` errors across venue schemas. These are pre-existing in the codebase.
- The venv must use Python 3.13: `uv venv .venv --python python3.13`.
- Always activate the venv before running commands: `source .venv/bin/activate`.

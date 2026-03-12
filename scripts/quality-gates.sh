#!/usr/bin/env bash
# Repo-specific settings only. Body: unified-trading-pm/scripts/quality-gates-base/base-library.sh
# SSOT: unified-trading-codex/06-coding-standards/quality-gates-library-template.sh
#
# Instructions for a new library:
#   1. Copy this to scripts/quality-gates.sh in your repo (rollout-quality-gates-unified.py does this)
#   2. SOURCE_DIR, PACKAGE_NAME, and MIN_COVERAGE are set automatically by rollout (floor=80)
#   3. Add LOCAL_DEPS entries if your library has local editable deps
PACKAGE_NAME="unified-api-contracts"
SOURCE_DIR="unified_api_contracts"
MIN_COVERAGE=84
PYTEST_WORKERS=${PYTEST_WORKERS:-2}
LOCAL_DEPS=()
WORKSPACE_ROOT="$(cd "$(git rev-parse --show-toplevel)/.." && pwd)"

# Exclude testing utilities that must use broad except Exception for best-effort introspection.
# detect_cassette_drift.py walks the full UAC package and must tolerate import errors from
# optional SDK deps and any Pydantic validation error during drift scanning.
# Documented in QUALITY_GATE_BYPASS_AUDIT.md § 2.7.
BROAD_EXCEPT_EXTRA_EXCLUDES=(
    "unified_api_contracts/testing/detect_cassette_drift.py"
)

source "${WORKSPACE_ROOT}/unified-trading-pm/scripts/quality-gates-base/base-library.sh"

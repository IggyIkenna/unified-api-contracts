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
UAC_CANONICAL_EXEMPT=true  # UAC is the schema repo -- internal imports are allowed

# venue_mapping.py uses .get() defaults for safe dataclass field defaults (not os.getenv fallback)
# cassette_orphan_checker.py + mock_replay.py are test tooling (not production code)
EMPTY_STR_EXCLUDE_GLOBS=("!**/venue_mapping.py" "!**/cassette_orphan_checker.py" "!**/mock_replay.py")
EMPTY_DICT_LIST_EXCLUDE_GLOBS=("!**/venue_mapping.py" "!**/mock_replay.py")
PRINT_EXCLUDE_GLOBS=("!**/cassette_orphan_checker.py")

WORKSPACE_ROOT="$(cd "$(git rev-parse --show-toplevel)/.." && pwd)"
source "${WORKSPACE_ROOT}/unified-trading-pm/scripts/quality-gates-base/base-library.sh"

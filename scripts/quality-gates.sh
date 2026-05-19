#!/usr/bin/env bash
# Repo-specific settings only. Body: unified-trading-pm/scripts/quality-gates-base/base-library.sh
# SSOT: unified-trading-pm/codex/06-coding-standards/quality-gates-library-template.sh
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
BROAD_EXCEPT_EXTRA_EXCLUDES=("**/venue_context.py" "**/mapping_resolver.py")
# data_source_continuity.py defines VIX_PROD_BUCKET/VIX_DEV_BUCKET as module-level string constants;
# defi_prediction_instrument_seeds.py docstring cites live GCS bucket names as provenance for Wave 8G seeds.
# generators/cefi.py: real_backfill_sample_uri is documentation of live GCS path shape, not runtime config.
GCP_PROJECT_ID_EXCLUDE_GLOBS=(
    "**/data_source_continuity.py"
    "**/defi_prediction_instrument_seeds.py"
    "**/generators/cefi.py"
)
# UAC's suite now covers 228-instance catalogue x cassette parity across 80+ external
# sources; the default 300s budget is too tight. 600s accommodates the combined surface
# without masking runaway regressions (a 60% overrun would still trip).
MAX_DURATION=600
WORKSPACE_ROOT="$(cd "$(git rev-parse --show-toplevel)/.." && pwd)"
source "${WORKSPACE_ROOT}/unified-trading-pm/scripts/quality-gates-base/base-library.sh"

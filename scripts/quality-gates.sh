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
BROAD_EXCEPT_EXTRA_EXCLUDES=("**/venue_context.py" "**/mapping_resolver.py")
# Internal testing uses lazy imports to avoid hard UTL dep
INSIDE_EXTRA_EXCLUDES=("**/internal/testing/**" "**/mapping_resolver.py")
# __init__.py is 998L of re-exports (T0 facade); errors/defi.py is 1224L of error class defs
SIZE_EXTRA_EXCLUDES=("./${SOURCE_DIR}/__init__.py" "./${SOURCE_DIR}/canonical/crosscutting/errors/defi.py" "./${SOURCE_DIR}/internal/__init__.py" "./${SOURCE_DIR}/internal/testing/*")
# pygments CVE-2026-4539: no fix version available (2.19.2 is latest); transitive via pytest+rich
PIP_AUDIT_EXTRA_ARGS="--ignore-vuln CVE-2026-4539"
# data_source_continuity.py defines VIX_PROD_BUCKET/VIX_DEV_BUCKET as module-level string constants
GCP_PROJECT_ID_EXCLUDE_GLOBS=("!**/registry/data_source_continuity.py")
WORKSPACE_ROOT="$(cd "$(git rev-parse --show-toplevel)/.." && pwd)"
source "${WORKSPACE_ROOT}/unified-trading-pm/scripts/quality-gates-base/base-library.sh"

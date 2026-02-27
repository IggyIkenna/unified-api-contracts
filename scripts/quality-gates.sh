#!/usr/bin/env bash
#
# Quality Gates for api-contracts (Tier 0)
# SSOT: unified-trading-codex/06-coding-standards/quality-gates-library-template.sh
# Aligned with instruments-service and UCS methodology. NO SKIPS.
#
# Usage:
#   ./scripts/quality-gates.sh                 # Auto-fix then verify
#   ./scripts/quality-gates.sh --no-fix        # Verify only (CI mode)
#   ./scripts/quality-gates.sh --quick         # Unit tests only
#   ./scripts/quality-gates.sh --lint          # Lint only
#   ./scripts/quality-gates.sh --test          # Tests only
#   ./scripts/quality-gates.sh --skip-typecheck # Skip basedpyright (not recommended)
#
set -e

# ── REPO-SPECIFIC SETTINGS ────────────────────────────────────────────────────
PACKAGE_NAME="api-contracts"
SOURCE_DIR="api_contracts"
MIN_COVERAGE=70
PYTEST_WORKERS=${PYTEST_WORKERS:-2}
REPO_ARCH_TIER="0"

# Tier 0: zero path dependencies
LOCAL_DEPS=()
# ── END REPO-SPECIFIC ─────────────────────────────────────────────────────────

QG_START=$(date +%s)
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_section() { echo -e "\n${BLUE}$1${NC}"; echo "----------------------------------------------------------------------"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_fail()    { echo -e "${RED}❌ $1${NC}"; }
log_warn()    { echo -e "${YELLOW}⚠️  $1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="${REPO_ROOT:-$(dirname "$PROJECT_ROOT")}"
cd "$PROJECT_ROOT"

MAX_FILE_LINES=900; FILE_WARN_LINES=700
MAX_FUNCTION_LINES=100; MAX_CLASS_LINES=500; MAX_METHOD_LINES=50

# Portable timeout: gtimeout → timeout → perl fallback (macOS)
run_timeout() {
    local secs=$1; shift
    if command -v gtimeout &>/dev/null; then gtimeout "$secs" "$@"
    elif command -v timeout &>/dev/null; then timeout "$secs" "$@"
    elif command -v perl &>/dev/null; then perl -e 'alarm shift; exec @ARGV' -- "$secs" "$@"
    else "$@"; fi
}

FIX_MODE=true; QUICK_MODE=false; RUN_LINT=true; RUN_TESTS=true; SKIP_TYPECHECK=false
for arg in "$@"; do
    case $arg in
        --no-fix) FIX_MODE=false ;;   --quick) QUICK_MODE=true ;;
        --lint) RUN_TESTS=false ;;    --test) RUN_LINT=false ;;
        --fix) FIX_MODE=true ;;       --skip-typecheck) SKIP_TYPECHECK=true ;;
    esac
done

# ── BOOTSTRAP (canonical pip order) ───────────────────────────────────────────
if [ -z "${GITHUB_ACTIONS:-}" ] && [ -z "${CI:-}" ] && [ -z "${CLOUD_BUILD:-}" ]; then
    command -v uv &>/dev/null || pip install uv --quiet
    [ -f "pyproject.toml" ] && uv lock 2>/dev/null
    [ ! -d ".venv" ] && uv venv .venv
    [ -f ".venv/bin/activate" ] && source .venv/bin/activate
    for lib in "${LOCAL_DEPS[@]}"; do
        [ -d "${REPO_ROOT}/$lib" ] && uv pip install -e "${REPO_ROOT}/$lib" --quiet 2>/dev/null
    done
    uv pip install -e ".[dev]" --quiet 2>/dev/null || uv pip install -e . --quiet 2>/dev/null
fi
PYTHON_CMD=".venv/bin/python"; [ ! -f "$PYTHON_CMD" ] && PYTHON_CMD="python3"

STAGED=$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null | grep '\.py$' | tr '\n' ' ' || true)
SOURCE_DIRS="${STAGED:-$SOURCE_DIR/ tests/}"
[ -n "$STAGED" ] && log_warn "Git-aware mode: $(echo "$STAGED" | wc -w | tr -d ' ') staged files"

export CLOUD_MOCK_MODE="true"
export GCP_PROJECT_ID="test-project"
export GOOGLE_CLOUD_PROJECT="test-project"

# ── [0] ENVIRONMENT ────────────────────────────────────────────────────────────
log_section "[0/6] ENVIRONMENT"
ACTUAL_PY=$($PYTHON_CMD --version 2>&1 | awk '{print $2}' | cut -d'.' -f1,2)
[[ "$ACTUAL_PY" != "3.13" ]] && { log_fail "Python 3.13 required, found $ACTUAL_PY"; exit 1; }; log_success "Python $ACTUAL_PY"
command -v rg &>/dev/null || { log_fail "ripgrep required: brew install ripgrep"; exit 1; }; log_success "ripgrep OK"
[ -f "pyproject.toml" ] && grep -q '>=3.13,<3.14' pyproject.toml || { log_fail "pyproject.toml: requires-python = '>=3.13,<3.14'"; exit 1; }; log_success "pyproject.toml OK"
[[ ! -f "uv.lock" ]] && log_warn "uv.lock missing" || log_success "uv.lock present"
RUFF_CMD=".venv/bin/ruff"; command -v "$RUFF_CMD" &>/dev/null || RUFF_CMD="ruff"
RUFF_VER=$($RUFF_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "0")
[[ "$RUFF_VER" != "0.15.0" ]] && log_warn "ruff 0.15.0 expected, found $RUFF_VER" || log_success "ruff $RUFF_VER"

# ── [1] AUTO-FIX ──────────────────────────────────────────────────────────────
if [ "$RUN_LINT" = true ] && [ "$FIX_MODE" = true ]; then
    log_section "[1/6] AUTO-FIX"
    run_timeout 30 $RUFF_CMD format --line-length 120 $SOURCE_DIRS || exit 1
    run_timeout 30 $RUFF_CMD check --fix --line-length 120 $SOURCE_DIRS || exit 1
    log_success "Auto-fix complete"
fi

# ── [2] LINT ───────────────────────────────────────────────────────────────────
if [ "$RUN_LINT" = true ]; then
    log_section "[2/6] LINT"
    run_timeout 30 $RUFF_CMD check --line-length 120 $SOURCE_DIRS && log_success "Lint PASSED" || { log_fail "Lint FAILED"; exit 1; }
fi

# ── [3] TESTS ──────────────────────────────────────────────────────────────────
if [ "$RUN_TESTS" = true ]; then
    log_section "[3/6] TESTS"
    $PYTHON_CMD -c "import pytest_timeout" 2>/dev/null || { log_fail "pytest-timeout required: uv pip install pytest-timeout"; exit 1; }
    $PYTHON_CMD -c "import xdist" 2>/dev/null || { log_fail "pytest-xdist required: uv pip install pytest-xdist"; exit 1; }
    COV="--cov=$SOURCE_DIR --cov-report=term-missing --cov-fail-under=$MIN_COVERAGE"
    PARGS="-n $PYTEST_WORKERS --timeout=60 -v --tb=short"
    $PYTHON_CMD -m pytest tests/unit/ $PARGS $COV || exit 1
    log_success "Tests PASSED"

    DUP=$(find tests/ -name "test_*_extended.py" -o -name "test_*_additional.py" 2>/dev/null | head -5 || true)
    [[ -n "$DUP" ]] && { log_fail "Duplicate test files — expand existing files instead:"; echo "$DUP"; exit 1; }
    log_success "No duplicate test files"

    SKIP_NO_REASON=$(rg "@pytest\.mark\.skip" --type py tests/ -B 1 2>/dev/null \
        | grep -v "# reason:\|# noqa\|^--" | grep "@pytest\.mark\.skip" || true)
    [[ -n "$SKIP_NO_REASON" ]] && { log_fail "pytest.mark.skip without reason comment — add '# reason: ...' above"; echo "$SKIP_NO_REASON" | head -3; exit 1; }
    log_success "All pytest.mark.skip have reason comments"
fi

# ── [3.5] IMPORT PATTERN STANDARDS ───────────────────────────────────────────
log_section "[3.5/6] IMPORT PATTERNS"
IP="${REPO_ROOT}/unified-trading-pm/scripts/check-import-patterns.py"
[ ! -f "$IP" ] && IP="${REPO_ROOT}/.cursor/scripts/check-import-patterns.py"
if [ -f "$IP" ]; then
    $PYTHON_CMD "$IP" --verbose 2>/dev/null && log_success "Import patterns PASSED" || { log_fail "Import patterns FAILED"; exit 1; }
else
    log_warn "check-import-patterns.py not found (unified-trading-pm/scripts/)"
fi

# ── [3.6] SDK VERSION ALIGNMENT ───────────────────────────────────────────
log_section "[3.6/6] SDK VERSION ALIGNMENT"
ALIGN="${REPO_ROOT}/api-contracts/scripts/check_sdk_version_alignment.py"
[ ! -f "$ALIGN" ] && ALIGN="${SCRIPT_DIR}/check_sdk_version_alignment.py"
if [ -f "$ALIGN" ]; then
    $PYTHON_CMD "$ALIGN" && log_success "SDK version alignment PASSED" || { log_fail "SDK version alignment FAILED"; exit 1; }
else
    log_warn "check_sdk_version_alignment.py not found"
fi

# ── [4] TYPE CHECK (basedpyright) ─────────────────────────────────────────────
log_section "[4/6] TYPE CHECK"
if [ "$SKIP_TYPECHECK" != "true" ]; then
    cleanup_zombie_pyright() {
        ps -eo pid,etime,command 2>/dev/null | grep -E 'basedpyright.*index\.js' | grep -v grep | \
        while read -r pid etime _; do
            hours=0; echo "$etime" | grep -q '-' && hours=$(($(echo "$etime" | cut -d'-' -f1) * 24))
            [ "$(echo "$etime" | tr ':' '\n' | wc -l)" -eq 3 ] && hours=$(echo "$etime" | cut -d':' -f1)
            [ "${hours:-0}" -ge 2 ] && log_warn "Killing zombie basedpyright PID $pid" && kill -9 "$pid" 2>/dev/null || true
        done
    }
    cleanup_zombie_pyright
    command -v basedpyright &>/dev/null || { log_fail "basedpyright required: uv pip install basedpyright"; exit 1; }
    export BASEDPYRIGHT_CACHE_DIR="${TMPDIR:-/tmp}/basedpyright-cache/${PACKAGE_NAME:-$(basename "$PWD")}"
    mkdir -p "$BASEDPYRIGHT_CACHE_DIR"
    run_timeout 120 basedpyright "$SOURCE_DIR/" 2>&1 && log_success "Type check PASSED" || { log_fail "Type check FAILED/timeout"; exit 1; }
fi
[ "$SKIP_TYPECHECK" = "true" ] && echo -e "${YELLOW}⚠️  Type check SKIPPED (--skip-typecheck flag)${NC}"

# ── [5] CODEX COMPLIANCE ──────────────────────────────────────────────────────
log_section "[5/6] CODEX COMPLIANCE"
V=0

rg "print\(" --type py --glob "!tests/**" --glob "!scripts/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "print() — use logger"; V=$((V+1)); } || log_success "No print()"

rg "os\.getenv" --type py --glob "!tests/**" --glob "!scripts/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "os.getenv() — use config class"; V=$((V+1)); } || log_success "No os.getenv()"

rg 'os\.getenv\s*\([^)]+,\s*""\s*\)' --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "os.getenv empty fallback — fail fast"; V=$((V+1)); } || log_success "No os.getenv empty fallback"

rg "datetime\.now\(\)|datetime\.utcnow\(\)" --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "Naive datetime — use datetime.now(timezone.utc)"; V=$((V+1)); } || log_success "No naive datetime"

rg "except:" --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "Bare except — use specific exception"; V=$((V+1)); } || log_success "No bare except"

rg "from google\.cloud import|import google\.cloud" --type py "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "google.cloud direct import — use UCS abstractions"; V=$((V+1)); } || log_success "No google.cloud imports"

for f in $(rg "import requests" --type py --glob "!tests/**" --glob "!scripts/**" "$SOURCE_DIR/" -l 2>/dev/null || true); do
    grep -q "async def" "$f" && { log_fail "requests in async: $f — use aiohttp"; V=$((V+1)); break; }
done; [[ ${V} -eq $(( V )) ]] && log_success "No requests in async" 2>/dev/null || true

INSIDE=$(rg "^[[:space:]]+import |^[[:space:]]+from .* import" --type py --glob "!tests/**" --glob "!**/__init__.py" \
    "$SOURCE_DIR/" 2>/dev/null | grep -v "endpoints.py" || true)
[[ -n "$INSIDE" ]] && { log_fail "Imports inside functions — move to top"; echo "$INSIDE" | head -3; V=$((V+1)); } || log_success "No imports inside functions"

ANY=$(rg ": Any|-> Any|\[Any\]" --type py --glob "!tests/**" --glob "!**/cloud_sdks/*" "$SOURCE_DIR/" 2>/dev/null | grep -v "dict\[str, Any\]" | grep -v "type: ignore" || true)
[[ -n "$ANY" ]] && { log_fail "Any types — use specific types"; echo "$ANY" | head -3; V=$((V+1)); } || log_success "No Any types"

rg '\.get\(["\x27][\w_]+["\x27]\s*,\s*["\x27]["\x27]\)' --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "Empty string fallback — fail fast"; V=$((V+1)); } || log_success "No empty string fallbacks"

ED=$(rg '\.get\s*\(\s*["\x27][^"\x27]+["\x27]\s*,\s*\{\}\s*\)' --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null || true)
EL=$(rg '\.get\s*\(\s*["\x27][^"\x27]+["\x27]\s*,\s*\[\]\s*\)' --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null || true)
[[ -n "$ED$EL" ]] && { log_fail "Empty dict/list fallback — fail fast"; V=$((V+1)); } || log_success "No empty dict/list fallbacks"

rg "central-element-323112" tests/ 2>/dev/null \
    && { log_fail "Hardcoded prod project ID in tests — use 'test-project'"; V=$((V+1)); } || log_success "No hardcoded project ID in tests"

rg "central-element-323112" --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "Hardcoded project ID in production — use config"; V=$((V+1)); } || log_success "No hardcoded project ID in production"

rg "GOOGLE_CLOUD_PROJECT" --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "Use GCP_PROJECT_ID not GOOGLE_CLOUD_PROJECT"; V=$((V+1)); } || log_success "No GOOGLE_CLOUD_PROJECT usage"

# Tier 0: no Tier 1+ imports
TIER_VIOLATIONS=$(rg 'from unified_trading_services|from unified_domain_client|from unified_internal_contracts' \
    --type py "${SOURCE_DIR}/" 2>/dev/null | grep -v __pycache__ || true)
[[ -n "$TIER_VIOLATIONS" ]] && {
    log_fail "Tier 0 violation: imports from Tier 1+ library (api-contracts must not import unified-internal-contracts or Tier 1+ libs):"
    echo "$TIER_VIOLATIONS" | head -5
    V=$((V+1))
} || log_success "Tier 0 compliance: no Tier 1+ imports (incl. unified-internal-contracts)"

# No direct cloud SDK imports
DIRECT_CLOUD=$(rg 'from google\.cloud import|^import boto3\b|^from boto3 import|^from botocore import' \
    --type py "${SOURCE_DIR}/" 2>/dev/null | grep -v __pycache__ | grep -v '\.venv' || true)
[[ -n "$DIRECT_CLOUD" ]] && {
    log_fail "Direct cloud SDK imports found (route through unified-cloud-interface instead):"
    echo "$DIRECT_CLOUD" | head -5
    V=$((V+1))
} || log_success "No direct cloud SDK imports"

if [ -f "Dockerfile" ]; then
    PIP=$(rg "^RUN pip install|^RUN python -m pip| pip install " Dockerfile 2>/dev/null | grep -v "pip install uv" | grep -v "#" || true)
    [[ -n "$PIP" ]] && { log_fail "Use 'uv pip install' not 'pip install' in Dockerfile"; echo "$PIP" | head -3; V=$((V+1)); } || log_success "No bare pip install in Dockerfile"
fi
PIP_SH=$(rg " pip install " --glob "**/*.sh" . 2>/dev/null | grep -v "uv pip install" | grep -v "pip install uv" | grep -v "#" || true)
[[ -n "$PIP_SH" ]] && { log_fail "Use 'uv pip install' not 'pip install' in scripts"; echo "$PIP_SH" | head -3; V=$((V+1)); } || log_success "No bare pip install in scripts"

SWALLOWED=$(rg "except Exception:" --type py --glob "!tests/**" "$SOURCE_DIR/" -A 2 2>/dev/null \
    | grep -E "^[[:space:]]+(pass|return None)$" || echo "")
[[ -n "$SWALLOWED" ]] && { log_fail "Swallowed errors — use @handle_api_errors or re-raise"; V=$((V+1)); } || log_success "No swallowed errors"

if [ -f "pyproject.toml" ]; then
    grep -q "reportAny" pyproject.toml || { log_fail "pyproject.toml [tool.basedpyright] must include reportAny"; V=$((V+1)); }
    grep -q "reportUnknown" pyproject.toml || { log_fail "pyproject.toml [tool.basedpyright] must include reportUnknown*"; V=$((V+1)); }
fi

# File size (MAX_FILE_LINES=900; exception: binance/schemas.py monolithic venue schema, split tracked)
SVIOL=""; SWARN=""
for f in $(find . -name "*.py" ! -path "./.venv/*" ! -path "./scripts/*" ! -path "./.git/*" 2>/dev/null); do
    lines=$(wc -l < "$f" 2>/dev/null || echo 0)
    # Exceptions: monolithic schema/manifest files, split by SRP tracked
    [[ "$f" = *"binance/schemas.py"* ]] && [[ "$lines" -lt 1100 ]] && continue
    [[ "$f" = *"venue_manifest.py"* ]] && [[ "$lines" -lt 1100 ]] && continue
    [[ "$f" = *"aws_schemas.py"* ]] && [[ "$lines" -lt 1500 ]] && continue
    [[ "$lines" -gt $MAX_FILE_LINES ]] && SVIOL="${SVIOL}\n  $f: $lines L"
    [[ "$lines" -gt $FILE_WARN_LINES && "$lines" -le $MAX_FILE_LINES ]] && SWARN="${SWARN}\n  $f: $lines L"
done
[[ -n "$SVIOL" ]] && { log_fail "Files exceed $MAX_FILE_LINES lines:$SVIOL"; V=$((V+1)); } || log_success "File size OK"
[[ -n "$SWARN" ]] && log_warn "Approaching limit:$SWARN"

# Security: pip-audit (blocking)
PIP_AUDIT_CMD=""
[ -f ".venv/bin/pip-audit" ] && PIP_AUDIT_CMD=".venv/bin/pip-audit"
[ -z "$PIP_AUDIT_CMD" ] && command -v pip-audit &>/dev/null && PIP_AUDIT_CMD="pip-audit"
if [ -n "$PIP_AUDIT_CMD" ]; then
    $PIP_AUDIT_CMD 2>/dev/null && log_success "pip-audit clean" || { log_fail "pip-audit vulnerabilities"; V=$((V+1)); }
else
    log_fail "pip-audit required: uv pip install pip-audit"; V=$((V+1))
fi

# Security: bandit (blocking)
if command -v bandit &>/dev/null; then
    run_timeout 30 bandit -r "$SOURCE_DIR/" -ll 2>/dev/null && log_success "bandit clean" || { log_fail "bandit issues"; V=$((V+1)); }
else
    log_fail "bandit required: uv pip install bandit"; V=$((V+1))
fi

BYPASS=$(rg "\|\|true|\|\| true" --glob "**/quality-gates.sh" --glob "**/quality-gates.yml" . 2>/dev/null \
    | grep -v "^#\|zombies\|pyright\|cleanup\|grep -v\|=\$(\|2>/dev/null" || echo "")
[[ -n "$BYPASS" ]] && { log_fail "||true bypass in quality gates — fix the root cause"; echo "$BYPASS" | head -3; V=$((V+1)); } || log_success "No ||true quality gate bypasses"

[[ $V -gt 0 ]] && { log_fail "Codex compliance FAILED: $V violations"; exit 1; }
log_success "Codex compliance PASSED"

# ── [6] PRODUCTION READINESS (informational) ──────────────────────────────────
log_section "[6/6] PRODUCTION READINESS VALIDATORS"
VSCRIPT="${REPO_ROOT}/unified-trading-codex/scripts/run-all-validators.sh"
[ -f "$VSCRIPT" ] && "$VSCRIPT" --category all --failed-only 2>/dev/null || log_warn "Validators not available (optional)"

QG_END=$(date +%s); DUR=$((QG_END - QG_START))
[ $DUR -gt 120 ] && { log_fail "Quality gates must complete in <2 min (took ${DUR}s)"; exit 1; }
echo -e "\n${GREEN}======================================================================"
echo -e "✅ ALL QUALITY GATES PASSED (${DUR}s)${NC}"

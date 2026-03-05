#!/usr/bin/env bash
#
# Quality Gates Template — Python Library
# SSOT: unified-trading-codex/06-coding-standards/quality-gates-library-template.sh
#
# Canonical reference: unified-trading-library/scripts/quality-gates.sh
# Aligned with service template checks; libraries: no test_event_logging, conditional Dockerfile pip check.
#
# Instructions for a new library:
#   1. Copy this to scripts/quality-gates.sh in your repo
#   2. Set PACKAGE_NAME, SOURCE_DIR, LOCAL_DEPS below
#   3. Ensure pyproject.toml has [tool.basedpyright] with reportAny and reportUnknown* (see quality-gates.md)
#   4. Run once; add bypass exceptions to QUALITY_GATE_BYPASS_AUDIT.md (not inline here)
#
# Requirements (must be in pyproject.toml [project.optional-dependencies] dev):
#   ruff==0.15.0, basedpyright, pytest, pytest-cov, pytest-xdist, pytest-timeout,
#   pip-audit, bandit
#
# Usage:
#   ./scripts/quality-gates.sh                 # Auto-fix then verify
#   ./scripts/quality-gates.sh --no-fix        # Verify only (CI mode)
#   ./scripts/quality-gates.sh --quick         # Unit tests only
#   ./scripts/quality-gates.sh --lint          # Lint only
#   ./scripts/quality-gates.sh --test          # Tests only
#   ./scripts/quality-gates.sh --skip-typecheck # Skip basedpyright type checking
#
set -e

# ── REPO-SPECIFIC SETTINGS ────────────────────────────────────────────────────
PACKAGE_NAME="unified-api-contracts"         # e.g. unified-trading-library
SOURCE_DIR="unified_api_contracts"           # e.g. unified_trading_library  (underscore form)
MIN_COVERAGE=70
PYTEST_WORKERS=${PYTEST_WORKERS:-2}

# Path dependencies (libraries may have path deps to unified-api-contracts, unified-config-interface, etc.)
LOCAL_DEPS=(
    # "unified-api-contracts"
    # "unified-config-interface"
)
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

run_timeout() {
    local secs=$1; shift
    if command -v timeout &>/dev/null; then timeout "$secs" "$@"
    elif command -v gtimeout &>/dev/null; then gtimeout "$secs" "$@"
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

# ── BOOTSTRAP ─────────────────────────────────────────────────────────────────
if [ -z "${GITHUB_ACTIONS:-}" ] && [ -z "${CI:-}" ] && [ -z "${CLOUD_BUILD:-}" ]; then
    command -v uv &>/dev/null || { echo "uv not found — install it from https://docs.astral.sh/uv/"; exit 1; }
    uv lock 2>/dev/null || :
    WORKSPACE_VENV="${REPO_ROOT}/.venv-workspace"
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    elif [ -f "${WORKSPACE_VENV}/bin/activate" ]; then
        source "${WORKSPACE_VENV}/bin/activate"
    else
        [ ! -d ".venv" ] && uv venv .venv
        [ -f ".venv/bin/activate" ] && source .venv/bin/activate || :
        for lib in "${LOCAL_DEPS[@]}"; do
            [ -d "${REPO_ROOT}/$lib" ] && uv pip install -e "${REPO_ROOT}/$lib" --quiet 2>/dev/null || :
        done
        uv pip install -e ".[dev]" --quiet 2>/dev/null || uv pip install -e . --quiet 2>/dev/null || :
    fi
fi
PYTHON_CMD=".venv/bin/python"
[ ! -f "$PYTHON_CMD" ] && [ -f "${REPO_ROOT}/.venv-workspace/bin/python" ] && PYTHON_CMD="${REPO_ROOT}/.venv-workspace/bin/python"
[ ! -f "$PYTHON_CMD" ] && PYTHON_CMD="python3"

STAGED=$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null | grep '\.py$' | tr '\n' ' ' || :)
SOURCE_DIRS="${STAGED:-$SOURCE_DIR/ tests/}"
[ -n "$STAGED" ] && log_warn "Git-aware mode: $(echo "$STAGED" | wc -w | tr -d ' ') staged files"

export CLOUD_MOCK_MODE="true"; export GCP_PROJECT_ID="test-project"

# ── [0] ENVIRONMENT ────────────────────────────────────────────────────────────
log_section "[0/6] ENVIRONMENT"
ACTUAL_PY=$($PYTHON_CMD --version 2>&1 | awk '{print $2}' | cut -d'.' -f1,2)
[[ "$ACTUAL_PY" != "3.13" ]] && { log_fail "Python 3.13 required, found $ACTUAL_PY"; exit 1; }; log_success "Python $ACTUAL_PY"
command -v rg &>/dev/null || { log_fail "ripgrep required: brew install ripgrep"; exit 1; }; log_success "ripgrep OK"
[ -f "pyproject.toml" ] && grep -q '>=3.13,<3.14' pyproject.toml || { log_fail "pyproject.toml: requires-python = '>=3.13,<3.14'"; exit 1; }; log_success "pyproject.toml OK"
[[ ! -f "uv.lock" ]] && log_warn "uv.lock missing" || log_success "uv.lock present"
RUFF_CMD=".venv/bin/ruff"; [ ! -f "$RUFF_CMD" ] && [ -f "${REPO_ROOT}/.venv-workspace/bin/ruff" ] && RUFF_CMD="${REPO_ROOT}/.venv-workspace/bin/ruff"; command -v "$RUFF_CMD" &>/dev/null || RUFF_CMD="ruff"
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
    COV="--cov=$SOURCE_DIR --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=$MIN_COVERAGE"
    PARGS="-n $PYTEST_WORKERS --timeout=60 -v --tb=short"
    $PYTHON_CMD -m pytest tests/unit/ $PARGS $COV || exit 1
    log_success "Tests PASSED"

    # DUP: No duplicate test files (test_*_extended.py, test_*_additional.py)
    DUP=$(find tests/ -name "test_*_extended.py" -o -name "test_*_additional.py" 2>/dev/null | head -5 || :)
    [[ -n "$DUP" ]] && { log_fail "Duplicate test files — expand existing files instead:"; echo "$DUP"; exit 1; }
    log_success "No duplicate test files"

    # SKIP_NO_REASON: @pytest.mark.skip must have a reason comment on the preceding line
    SKIP_NO_REASON=$(rg "@pytest\.mark\.skip" --type py tests/ -B 1 2>/dev/null \
        | grep -v "# reason:\|# noqa\|^--" | grep "@pytest\.mark\.skip" || :)
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

# ── [4] TYPE CHECK (basedpyright) ─────────────────────────────────────────────
log_section "[4/6] TYPE CHECK"
if [ "$SKIP_TYPECHECK" != "true" ]; then
    cleanup_zombie_pyright() {
        ps -eo pid,etime,command 2>/dev/null | grep -E 'basedpyright.*index\.js' | grep -v grep | \
        while read -r pid etime _; do
            hours=0; echo "$etime" | grep -q '-' && hours=$(($(echo "$etime" | cut -d'-' -f1) * 24))
            [ "$(echo "$etime" | tr ':' '\n' | wc -l)" -eq 3 ] && hours=$(echo "$etime" | cut -d':' -f1)
            [ "${hours:-0}" -ge 2 ] && log_warn "Killing zombie basedpyright PID $pid" && kill -9 "$pid" 2>/dev/null || :
        done
    }
    cleanup_zombie_pyright
    command -v basedpyright &>/dev/null || { log_fail "basedpyright required: uv add basedpyright"; exit 1; }
    export BASEDPYRIGHT_CACHE_DIR="${TMPDIR:-/tmp}/basedpyright-cache/${PACKAGE_NAME:-$(basename "$PWD")}"
    mkdir -p "$BASEDPYRIGHT_CACHE_DIR"
    run_timeout 120 basedpyright "$SOURCE_DIR/" 2>&1 && log_success "Type check PASSED" || { log_fail "Type check FAILED/timeout"; exit 1; }
fi
[ "$SKIP_TYPECHECK" = "true" ] && echo -e "${YELLOW}⚠️  Type check SKIPPED (--skip-typecheck flag)${NC}"

# ── [5] CODEX COMPLIANCE ──────────────────────────────────────────────────────
# Same 9 checks as service template; libraries: conditional pip check (Dockerfile may not exist).
log_section "[5/6] CODEX COMPLIANCE"
V=0

rg "print\(" --type py --glob "!tests/**" --glob "!scripts/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "print() — use logger"; ((V++)); } || log_success "No print()"

rg "os\.getenv" --type py --glob "!tests/**" --glob "!scripts/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "os.getenv() — use config class"; ((V++)); } || log_success "No os.getenv()"

rg 'os\.getenv\s*\([^)]+,\s*""\s*\)' --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "os.getenv empty fallback — fail fast"; ((V++)); } || log_success "No os.getenv empty fallback"

rg "datetime\.now\(\)|datetime\.utcnow\(\)" --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "Naive datetime — use datetime.now(timezone.utc)"; ((V++)); } || log_success "No naive datetime"

rg "except:" --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "Bare except — use specific exception"; ((V++)); } || log_success "No bare except"

rg "from google\.cloud import|import google\.cloud" --type py "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "google.cloud direct import — use UCS abstractions"; ((V++)); } || log_success "No google.cloud imports"

for f in $(rg "import requests" --type py --glob "!tests/**" --glob "!scripts/**" "$SOURCE_DIR/" -l 2>/dev/null || :); do
    grep -q "async def" "$f" && { log_fail "requests in async: $f — use aiohttp"; ((V++)); break; }
done; [[ ${V} -eq $(( V )) ]] && log_success "No requests in async" 2>/dev/null || :

for f in $(rg "asyncio\.run\(" --type py --glob "!tests/**" --glob "!scripts/**" "$SOURCE_DIR/" -l 2>/dev/null || :); do
    grep -q "for \|while " "$f" && { log_fail "asyncio.run() in loop: $f — use asyncio.gather()"; ((V++)); break; }
done

INSIDE=$(rg "^[[:space:]]+import |^[[:space:]]+from .* import" --type py --glob "!tests/**" --glob "!**/__init__.py" \
    "$SOURCE_DIR/" 2>/dev/null || :)
[[ -n "$INSIDE" ]] && { log_fail "Imports inside functions — move to top"; echo "$INSIDE" | head -3; ((V++)); } || log_success "No imports inside functions"

ANY=$(rg ": Any|-> Any|\[Any\]" --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null | grep -v "type: ignore" || :)
[[ -n "$ANY" ]] && { log_fail "Any types (including dict[str, Any]) — use Pydantic models or specific types"; echo "$ANY" | head -3; ((V++)); } || log_success "No Any types"

# Untyped API responses — response.json() must go through model_validate(), not raw dict access
RAW_JSON=$(rg 'response\.json\(\)|await response\.json\(\)' --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null \
    | grep -v 'model_validate\|cast(dict' || :)
[[ -n "$RAW_JSON" ]] && { log_fail "Raw response.json() — parse through Pydantic model_validate()"; echo "$RAW_JSON" | head -3; ((V++)); } || log_success "No raw response.json()"

rg '\.get\(["\x27][\w_]+["\x27]\s*,\s*["\x27]["\x27]\)' --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "Empty string fallback — fail fast"; ((V++)); } || log_success "No empty string fallbacks"

ED=$(rg '\.get\s*\(\s*["\x27][^"\x27]+["\x27]\s*,\s*\{\}\s*\)' --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null || :)
EL=$(rg '\.get\s*\(\s*["\x27][^"\x27]+["\x27]\s*,\s*\[\]\s*\)' --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null || :)
[[ -n "$ED$EL" ]] && { log_fail "Empty dict/list fallback — fail fast"; ((V++)); } || log_success "No empty dict/list fallbacks"

rg "central-element-323112" tests/ 2>/dev/null \
    && { log_fail "Hardcoded prod project ID in tests — use 'test-project'"; ((V++)); } || log_success "No hardcoded project ID in tests"

rg "central-element-323112" --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "Hardcoded project ID in production — use config"; ((V++)); } || log_success "No hardcoded project ID in production"

# 1. GOOGLE_CLOUD_PROJECT check — use GCP_PROJECT_ID instead
rg "GOOGLE_CLOUD_PROJECT" --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null \
    && { log_fail "Use GCP_PROJECT_ID not GOOGLE_CLOUD_PROJECT (no exceptions — remove from config class)"; ((V++)); } || log_success "No GOOGLE_CLOUD_PROJECT usage"

# Domain clients must come from unified_domain_client, not unified_trading_library
UCS_DOMAIN=$(rg 'from unified_trading_library import[^#]*?(InstrumentsDomainClient|ExecutionDomainClient|MarketCandleDataDomainClient|MarketTickDataDomainClient|create_instruments_client|create_execution_client|create_features_client|create_market_candle_data_client|create_market_tick_data_client)' \
    --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null || :)
[[ -n "$UCS_DOMAIN" ]] && { log_fail "Domain clients must come from unified_domain_client, not unified_trading_library"; echo "$UCS_DOMAIN" | head -5; ((V++)); } || log_success "Domain clients imported from unified_domain_client"

# No domain imports from UCS
DOMAIN_FROM_UCS=$(rg 'from unified_trading_library import.*(market_category|DomainValidation|UnifiedCloudServicesConfig)' \
    --type py "$SOURCE_DIR/" 2>/dev/null || :)
[[ -n "$DOMAIN_FROM_UCS" ]] && { log_fail "Service imports domain symbols from UCS — use unified_domain_client instead"; echo "$DOMAIN_FROM_UCS" | head -5; ((V++)); } || log_success "No domain imports from UCS"

# setup_events/setup_service uses sink= in production
SETUP_NO_SINK=$(rg 'setup_(events|service)\s*\(' --type py \
    --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null | grep -v 'sink=' || :)
[[ -n "$SETUP_NO_SINK" ]] && { log_fail "setup_events()/setup_service() called without sink= in production code"; echo "$SETUP_NO_SINK" | head -5; ((V++)); } || log_success "setup_service() uses sink= in all production call sites"

BAD_AUTH_SKIP=$(rg 'pytest\.skip.*[Cc]redential|pytest\.skip.*GOOGLE_APPLICATION_CREDENTIALS|if not.*gcp_credentials.*pytest\.skip\|if not.*cred_file.*pytest\.skip' \
    --type py tests/ 2>/dev/null \
    | grep -v "_skip_integration_without_creds\|No GCP credentials.*skipping integration\|No GCP credentials.*skipping Secret Manager\|Could not create/access" \
    || :)
[[ -n "$BAD_AUTH_SKIP" ]] && { log_fail "Tests skip due to missing credential file — use google.auth.default() + @pytest.mark.integration instead"; echo "$BAD_AUTH_SKIP" | head -5; ((V++)); } || log_success "No credential-file skip patterns in tests"

[[ -f ".env.example" ]] && rg "GOOGLE_APPLICATION_CREDENTIALS" .env.example 2>/dev/null \
    && { log_fail ".env.example contains GOOGLE_APPLICATION_CREDENTIALS — remove it (use ADC, not SA key files)"; ((V++)); } || log_success "No GOOGLE_APPLICATION_CREDENTIALS in .env.example"

DI=$(rg 'from unified_[a-z_]+\.[a-zA-Z0-9_.]+\s+import' --type py --glob "!tests/**" --glob "!**/__init__.py" "$SOURCE_DIR/" 2>/dev/null \
    | grep -v "from ${SOURCE_DIR}\." || :)
[[ -n "$DI" ]] && { log_fail "Deep unified lib imports — use top-level"; echo "$DI" | head -3; ((V++)); } || log_success "No deep imports"

# 2. EL_OLD — old event logging import pattern
EL_OLD=$(rg "from unified_trading_library[. ].*(log_event|setup_events|setup_cloud_logging|observability)" --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null || :)
[[ -n "$EL_OLD" ]] && { log_fail "Old event logging import — use 'from unified_events_interface import ...'"; echo "$EL_OLD" | head -3; ((V++)); } || log_success "Event logging imports from unified_events_interface"

# ============================================================
# STEP 5.5 — No direct cloud SDK imports (must route through UCLI/UCS)
# ============================================================
DIRECT_CLOUD=$(rg 'from google\.cloud import|^import boto3\b|^from boto3 import|^from botocore import' \
    --type py "${SOURCE_DIR}/" 2>/dev/null | grep -v __pycache__ | grep -v '\.venv' || :)
[[ -n "$DIRECT_CLOUD" ]] && {
    log_fail "Direct cloud SDK imports found (route through unified-cloud-interface instead):"
    echo "$DIRECT_CLOUD" | head -5
    ((V++))
} || log_success "No direct cloud SDK imports"

# ============================================================
# STEP 5.6 — Architecture Tier Compliance
# ============================================================
# Read tier from pyproject.toml [tool.quality-gates] repo_arch_tier if env var not set
if [ -z "${REPO_ARCH_TIER:-}" ] && [ -f "pyproject.toml" ]; then
    _TOML_TIER=$(grep -A5 '\[tool\.quality-gates\]' pyproject.toml 2>/dev/null | grep 'repo_arch_tier' | grep -oE '"[^"]*"|[0-9]+' | tr -d '"' | head -1 || :)
    REPO_ARCH_TIER="${_TOML_TIER:-library}"
else
    REPO_ARCH_TIER="${REPO_ARCH_TIER:-library}"
fi
if [[ "$REPO_ARCH_TIER" == "0" ]]; then
    TIER_VIOLATIONS=$(rg 'from unified_trading_library|from unified_domain_client|from unified_trading_library' \
        --type py "${SOURCE_DIR}/" 2>/dev/null | grep -v __pycache__ || :)
    [[ -n "$TIER_VIOLATIONS" ]] && {
        log_fail "Tier 0 violation: imports from Tier 1+ library:"
        echo "$TIER_VIOLATIONS" | head -5
        ((V++))
    } || log_success "Tier 0 compliance: no Tier 1+ imports"
elif [[ "$REPO_ARCH_TIER" == "2" ]]; then
    TIER_VIOLATIONS=$(rg 'from unified_trading_library|from unified_trading_library' \
        --type py "${SOURCE_DIR}/" 2>/dev/null | grep -v __pycache__ || :)
    [[ -n "$TIER_VIOLATIONS" ]] && {
        log_fail "Tier 2 violation: imports from Tier 1 (unified-trading-library/unified-trading-library):"
        echo "$TIER_VIOLATIONS" | head -5
        ((V++))
    } || log_success "Tier 2 compliance: no Tier 1 imports"
else
    log_success "Tier compliance skipped (REPO_ARCH_TIER=$REPO_ARCH_TIER)"
fi

# 3. PIP — pip install vs uv pip install (conditional: only if Dockerfile or .sh scripts exist)
if [ -f "Dockerfile" ]; then
    PIP=$(rg "^RUN pip install|^RUN python -m pip| pip install " Dockerfile 2>/dev/null | grep -v "pip install uv" | grep -v "#" || :)
    [[ -n "$PIP" ]] && { log_fail "Use 'uv pip install' not 'pip install' in Dockerfile"; echo "$PIP" | head -3; ((V++)); } || log_success "No bare pip install in Dockerfile"
fi
PIP_SH=$(rg " pip install " --glob "**/*.sh" . 2>/dev/null | grep -v "pip install uv\|uv pip install" | grep -v "#" || :)
[[ -n "$PIP_SH" ]] && { log_fail "Use 'uv pip install' not 'pip install' in scripts"; echo "$PIP_SH" | head -3; ((V++)); } || log_success "No bare pip install in scripts"

BE=$(rg "except Exception:" --type py --glob "!tests/**" "$SOURCE_DIR/" 2>/dev/null || :)
[[ -n "$BE" ]] && { log_warn "broad except Exception — document in QUALITY_GATE_BYPASS_AUDIT.md"; ((V++)); } || log_success "No broad except Exception"

# 4. SWALLOWED — except Exception: pass detection
SWALLOWED=$(rg "except Exception:" --type py --glob "!tests/**" "$SOURCE_DIR/" -A 2 2>/dev/null \
    | grep -E "^[[:space:]]+(pass|return None)$" || :)
[[ -n "$SWALLOWED" ]] && { log_fail "Swallowed errors — use @handle_api_errors or re-raise"; ((V++)); } || log_success "No swallowed errors"

# 8. 9. reportAny and reportUnknown* in basedpyright — verify pyproject.toml config
if [ -f "pyproject.toml" ]; then
    grep -q "reportAny" pyproject.toml || { log_fail "pyproject.toml [tool.basedpyright] must include reportAny"; ((V++)); }
    grep -q "reportUnknown" pyproject.toml || { log_fail "pyproject.toml [tool.basedpyright] must include reportUnknown*"; ((V++)); }
fi

# File size (exceptions: see QUALITY_GATE_BYPASS_AUDIT.md §2.5)
SVIOL=""; SWARN=""
for f in $(find . -name "*.py" ! -path "./.venv/*" ! -path "./scripts/*" ! -path "./.git/*" ! -path "./build/*" ! -path "*/sports/canonical/features.py" 2>/dev/null); do
    lines=$(wc -l < "$f" 2>/dev/null || echo 0)
    [[ "$lines" -gt $MAX_FILE_LINES ]] && SVIOL="${SVIOL}\n  $f: $lines L"
    [[ "$lines" -gt $FILE_WARN_LINES && "$lines" -le $MAX_FILE_LINES ]] && SWARN="${SWARN}\n  $f: $lines L"
done
[[ -n "$SVIOL" ]] && { log_fail "Files exceed $MAX_FILE_LINES lines:$SVIOL"; ((V++)); } || log_success "File size OK"
[[ -n "$SWARN" ]] && log_warn "Approaching limit:$SWARN"

# Function/class/method size (exceptions: see QUALITY_GATE_BYPASS_AUDIT.md §2.5)
FSIZES=""
for f in $(find . -name "*.py" ! -path "./.venv/*" ! -path "./scripts/*" ! -path "./.git/*" ! -path "./build/*" ! -path "./tests/*" ! -path "*/sports/canonical/features.py" 2>/dev/null); do
    out=$($PYTHON_CMD -c "
import ast, sys
p=sys.argv[1]
try:
  with open(p,'r',encoding='utf-8') as fp: tree=ast.parse(fp.read())
  def v(n,par=None):
    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
      l=(n.end_lineno or n.lineno)-n.lineno+1
      if isinstance(par,ast.ClassDef): l>$MAX_METHOD_LINES and print(f'  {p}:{n.lineno}:{par.name}.{n.name}(): {l}L')
      elif l>$MAX_FUNCTION_LINES: print(f'  {p}:{n.lineno}:{n.name}(): {l}L')
    elif isinstance(n,ast.ClassDef):
      l=(n.end_lineno or n.lineno)-n.lineno+1
      l>$MAX_CLASS_LINES and print(f'  {p}:{n.lineno}:{n.name}: {l}L')
    for c in ast.iter_child_nodes(n): v(c,n if isinstance(n,ast.ClassDef) else par)
  v(tree)
except: pass
" "$f" 2>/dev/null || :)
    [[ -n "$out" ]] && FSIZES="${FSIZES}\n${out}"
done
[[ -n "$FSIZES" ]] && { log_fail "Function/class/method size exceeded:$FSIZES"; ((V++)); } || log_success "Function/class/method size OK"

# Security: pip-audit
if command -v pip-audit &>/dev/null; then
    pip-audit 2>/dev/null && log_success "pip-audit clean" || { log_fail "pip-audit vulnerabilities"; ((V++)); }
else
    log_fail "pip-audit required: uv add pip-audit"; ((V++))
fi

# Security: bandit
if command -v bandit &>/dev/null; then
    run_timeout 30 bandit -r "$SOURCE_DIR/" -ll 2>/dev/null && log_success "bandit clean" || { log_fail "bandit issues"; ((V++)); }
else
    log_fail "bandit required: uv add bandit"; ((V++))
fi

# 7. BYPASS — ||true in quality gate scripts
BYPASS=$(rg "\|\|true|\|\| true" --glob "**/quality-gates.sh" --glob "**/quality-gates.yml" . 2>/dev/null \
    | grep -v "^#\|zombies\|pyright\|cleanup\|log_fail\|:#" || :)
[[ -n "$BYPASS" ]] && { log_fail "||true bypass in quality gates — fix the root cause"; echo "$BYPASS" | head -3; ((V++)); } || log_success "No ||true quality gate bypasses"

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

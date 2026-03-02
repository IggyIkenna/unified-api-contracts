#!/usr/bin/env bash
#
# Dev environment setup for unified-api-contracts
#
# Usage:
#   ./scripts/setup.sh           # Full setup (idempotent, safe to re-run)
#   ./scripts/setup.sh --check   # Verify environment only, no installs
#
# Fast path: when .venv exists with Python 3.13 and uv.lock hasn't changed,
# `uv sync` completes in ~20ms (audits installed packages, installs nothing).
#
# What this script does:
#   1. Verifies Python 3.13 is available (with install instructions if not)
#   2. Installs uv package manager if missing
#   3. Checks for ripgrep (required by quality-gates.sh)
#   4. Creates .venv with Python 3.13 (or validates existing one)
#   5. Runs `uv sync --extra dev` to install from uv.lock (lockfile-pinned)
#
# The .venv is NOT committed (it's in .gitignore). The uv.lock IS committed
# and pins every dependency version. `uv sync` reads the lockfile, so:
#   - No new deps?  → ~20ms audit, installs nothing
#   - New deps?     → installs only the diff
#   - Wrong Python? → recreates venv, reinstalls everything
#
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_ok()   { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_fail() { echo -e "${RED}❌ $1${NC}"; }
log_info() { echo -e "${BLUE}→ $1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

CHECK_ONLY=false
for arg in "$@"; do
    case $arg in
        --check) CHECK_ONLY=true ;;
    esac
done

ERRORS=0

# ── [1] Python 3.13 ──────────────────────────────────────────────────────────
log_info "Checking Python 3.13..."

PYTHON_CMD=""
for candidate in python3.13 python3 python; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" --version 2>&1 | awk '{print $2}' | cut -d'.' -f1,2)
        if [[ "$ver" == "3.13" ]]; then
            PYTHON_CMD="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    log_fail "Python 3.13 not found (requires >=3.13,<3.14)"
    echo ""
    echo "    Install options:"
    echo "      Ubuntu/Debian:  sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.13 python3.13-venv python3.13-dev"
    echo "      macOS (brew):   brew install python@3.13"
    echo "      pyenv:          pyenv install 3.13 && pyenv local 3.13"
    echo "      mise:           mise install python@3.13 && mise use python@3.13"
    echo ""
    ERRORS=$((ERRORS + 1))
else
    log_ok "Python 3.13 found: $($PYTHON_CMD --version) ($PYTHON_CMD)"
fi

# ── [2] uv ────────────────────────────────────────────────────────────────────
log_info "Checking uv..."

export PATH="$HOME/.local/bin:$PATH"

if ! command -v uv &>/dev/null; then
    if [[ "$CHECK_ONLY" == "true" ]]; then
        log_fail "uv not found"
        ERRORS=$((ERRORS + 1))
    else
        log_warn "uv not found — installing..."
        pip install uv --quiet 2>/dev/null || pip3 install uv --quiet 2>/dev/null
        export PATH="$HOME/.local/bin:$PATH"
        if command -v uv &>/dev/null; then
            log_ok "uv installed: $(uv --version)"
        else
            log_fail "Failed to install uv"
            ERRORS=$((ERRORS + 1))
        fi
    fi
else
    log_ok "uv found: $(uv --version)"
fi

# ── [3] ripgrep ───────────────────────────────────────────────────────────────
log_info "Checking ripgrep..."

if ! command -v rg &>/dev/null; then
    log_warn "ripgrep (rg) not found — required by quality-gates.sh"
    echo "    Install: sudo apt install ripgrep  OR  brew install ripgrep"
else
    log_ok "ripgrep found: $(rg --version | head -1)"
fi

# ── [4] Virtual environment + dependencies ────────────────────────────────────
if [[ "$CHECK_ONLY" == "true" ]]; then
    if [[ -d ".venv" ]]; then
        VENV_PY=$(.venv/bin/python --version 2>&1 | awk '{print $2}' | cut -d'.' -f1,2)
        if [[ "$VENV_PY" == "3.13" ]]; then
            log_ok ".venv exists with Python $VENV_PY"
        else
            log_fail ".venv exists but uses Python $VENV_PY (need 3.13)"
            ERRORS=$((ERRORS + 1))
        fi
    else
        log_fail ".venv not found"
        ERRORS=$((ERRORS + 1))
    fi
else
    if [[ -z "$PYTHON_CMD" ]]; then
        log_fail "Cannot create venv — Python 3.13 not found (see above)"
        ERRORS=$((ERRORS + 1))
    else
        # Handle wrong-version venv
        if [[ -d ".venv" ]]; then
            VENV_PY=$(.venv/bin/python --version 2>&1 | awk '{print $2}' | cut -d'.' -f1,2)
            if [[ "$VENV_PY" != "3.13" ]]; then
                log_warn ".venv uses Python $VENV_PY — recreating with 3.13..."
                rm -rf .venv
            fi
        fi

        # uv sync: creates venv if needed, installs from uv.lock, no-op if up to date
        log_info "Syncing dependencies from uv.lock..."
        SYNC_START=$(date +%s%N 2>/dev/null || date +%s)
        uv sync --extra dev --python "$PYTHON_CMD"
        SYNC_END=$(date +%s%N 2>/dev/null || date +%s)

        # Calculate duration for user feedback
        if [[ "$SYNC_START" =~ ^[0-9]{10,}$ ]]; then
            SYNC_MS=$(( (SYNC_END - SYNC_START) / 1000000 ))
            log_ok "Dependencies synced (${SYNC_MS}ms)"
        else
            log_ok "Dependencies synced"
        fi
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
if [[ $ERRORS -gt 0 ]]; then
    log_fail "Setup incomplete — $ERRORS issue(s) above need manual resolution"
    exit 1
else
    log_ok "Environment ready"
    echo ""
    echo "    Activate:        source .venv/bin/activate"
    echo "    Run tests:       pytest tests/unit/ -v -n 2 --timeout=60"
    echo "    Run lint:        ruff check unified_api_contracts/"
    echo "    Quality gates:   bash scripts/quality-gates.sh"
    echo ""
fi

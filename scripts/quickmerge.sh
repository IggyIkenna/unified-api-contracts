#!/bin/bash
# quickmerge: Push changes through a PR with auto-merge
#
# Library template (api-contracts: no path deps).
#
# Usage:
#   ./scripts/quickmerge.sh "commit message"
#   ./scripts/quickmerge.sh "commit message" --auto-branch
#   ./scripts/quickmerge.sh "commit message" --quick
#
# Pipeline: dep validation → pre-flight → quality gates → act → PR

set -e

REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/.." && pwd))"
REPO_NAME=$(basename "$REPO_DIR")
WORKSPACE_ROOT="$(cd "$REPO_DIR/.." && pwd)"

COMMIT_MSG="chore: automated update"
AUTO_BRANCH=false
QUICK=false
SKIP_TESTS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --auto-branch) AUTO_BRANCH=true; shift ;;
        --quick) QUICK=true; shift ;;
        --skip-tests) SKIP_TESTS="--skip-tests"; shift ;;
        *) COMMIT_MSG="$1"; shift ;;
    esac
done

cd "$REPO_DIR"

git fetch origin main --quiet 2>/dev/null || true
if [ -z "$(git status --porcelain)" ] && git diff origin/main --quiet 2>/dev/null; then
    echo "[$REPO_NAME] Nothing to commit — exiting fast"
    exit 0
fi

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
fi

if [ -f "pyproject.toml" ]; then
    command -v uv >/dev/null 2>&1 || pip install uv --quiet
    uv pip install -e ".[dev]" --quiet 2>/dev/null || uv pip install -e . --quiet 2>/dev/null || true
fi

echo "=========================================="
echo "STAGE 1: Dependency Validation"
echo "=========================================="
echo "✅ No .dependency-matrix.json (library, no path deps)"
echo ""

if [ "$QUICK" != true ] && [ -f "$WORKSPACE_ROOT/.cursor/scripts/pre-flight-audit.sh" ]; then
    echo "=========================================="
    echo "STAGE 2: Pre-flight Audit"
    echo "=========================================="
    if bash "$WORKSPACE_ROOT/.cursor/scripts/pre-flight-audit.sh" "$REPO_NAME"; then
        echo "[$REPO_NAME] ✅ Pre-flight audit PASSED"
    else
        echo "[$REPO_NAME] ❌ Pre-flight audit FAILED"
        exit 1
    fi
    echo ""
elif [ "$QUICK" = true ]; then
    echo "[$REPO_NAME] --quick: Skipping pre-flight audit"
    echo ""
fi

if [ "$AUTO_BRANCH" = true ]; then
    PREFIX=$(echo "$COMMIT_MSG" | grep -oE '^(feat|fix|refactor|chore|docs|test|style|perf|ci|build)' || echo "fix")
    SLUG=$(echo "$COMMIT_MSG" | sed 's/^[^:]*: //' | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]//g' | cut -c1-20)
    DEP_BRANCH="${PREFIX}-${SLUG}-$(date +%Y%m%d-%H%M)"
    echo "[$REPO_NAME] Auto-branch: $DEP_BRANCH"
fi

if [ -z "$(git status --porcelain)" ]; then
    echo "[$REPO_NAME] No changes to commit"
    exit 0
fi

echo "=========================================="
echo "STAGE 3: Local Quality Gates"
echo "=========================================="
bash scripts/quality-gates.sh $SKIP_TESTS
if ! bash scripts/quality-gates.sh --no-fix $SKIP_TESTS; then
    echo "[$REPO_NAME] ❌ Quality gates FAILED"
    exit 1
fi
echo "[$REPO_NAME] ✅ Quality gates PASSED"
echo ""

if [ "$QUICK" != true ] && command -v act &>/dev/null; then
    echo "=========================================="
    echo "STAGE 4: Act Simulation"
    echo "=========================================="
    ACT_SECRETS=""
    [ -f ~/.secrets ] && ACT_SECRETS="--secret-file ~/.secrets"
    if act -j quality-gates $ACT_SECRETS 2>/dev/null; then
        echo "[$REPO_NAME] ✅ Act simulation PASSED"
    else
        echo "[$REPO_NAME] ⚠️  Act simulation failed (continuing)"
    fi
    echo ""
fi

echo "=========================================="
echo "STAGE 5: Create PR"
echo "=========================================="
RESTORE_STASH=0
if [ -n "$(git status --porcelain)" ]; then
    git stash push -u -m "quickmerge-$$" --quiet
    RESTORE_STASH=1
fi

git fetch origin main --quiet 2>/dev/null || true
BRANCH="${DEP_BRANCH:-auto/$(date +%Y%m%d-%H%M%S)-$$}"
git checkout -b "$BRANCH" origin/main --quiet

if [ "$RESTORE_STASH" = 1 ] && git stash list | grep -q "quickmerge-$$"; then
    git stash pop --quiet
fi

git add -A
git commit -m "$COMMIT_MSG" --quiet
git push -u origin "$BRANCH" --quiet 2>/dev/null

PR_URL=$(gh pr create --title "$COMMIT_MSG" --body "Automated PR. Will auto-merge once quality gates pass." --base main --head "$BRANCH" 2>/dev/null)
PR_NUM=$(echo "$PR_URL" | grep -o "[0-9]*$" || echo "")
[ -n "$PR_NUM" ] && gh pr merge "$PR_NUM" --auto --squash --delete-branch 2>/dev/null || true

echo "[$REPO_NAME] PR created: $PR_URL"
git checkout main --quiet 2>/dev/null || true
git pull --quiet 2>/dev/null || true

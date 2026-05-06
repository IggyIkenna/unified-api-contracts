<!-- POST_PLAN_BANNER_2026_05_06_FINAL -->

> **Post-2026-05-06** — read [`../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md`](../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md) before code/doc changes informed by this doc. The post-plan-reality doc summarizes the 10 cross-cutting principles codified in workspace `CLAUDE.md` (live=batch, no double SSOT, three-category empty-output decision A/B/C, cluster validation MANDATORY at `record_captured`, `available_at` per-row write-time, prediction lifecycle, temporary state must have named successor, per-VM shard isolation, multi-axis shard-vs-display distinction) plus the active plans (`writegate_honest_coverage_endtoend_2026_05_06.plan.md`, `predictions_canonical_question_group_polymarket_migration_2026_05_06.plan.md`, `data_status_multi_axis_shard_propagation_2026_05_06.plan.md`). If this doc disagrees with the active plans, the plans win. Flag conflicts to user — don't decide unilaterally.

# iCloud Repo Migration — Agent Prompt

Use this prompt to migrate a git repo from iCloud Drive to local `~/Code` with clean commits. Run per-repo via agents.

---

## QUICK START: Copy this to agent

```
REPO_PATH="/path/to/your/repo"   # <-- SET THIS

cd "$REPO_PATH"
ROOT=$(git rev-parse --show-toplevel)
git checkout -B main
git status -sb

# Ensure .gitignore has: .venv/ venv/ __pycache__/ *.pyc .pytest_cache/ .mypy_cache/ .ruff_cache/ .cache/ node_modules/ .next/ dist/ build/ .turbo/ coverage/ .nyc_output/ .DS_Store .venv-workspace/
# Ensure .cursorignore has: **/.venv/** **/venv/** **/node_modules/** **/.next/** **/dist/** **/build/** **/.turbo/** **/__pycache__/** **/.cache/** **/.venv-workspace/**

# Remove tracked junk if any:
git ls-files -z -- ".venv/*" "venv/*" "__pycache__/*" "node_modules/*" ".next/*" "dist/*" "build/*" ".turbo/*" ".venv-workspace/*" | wc -c
# If non-zero: git rm -r --cached --ignore-unmatch .venv venv __pycache__ node_modules .next dist build .turbo .venv-workspace

git add .gitignore .cursorignore && git add -A
git diff --cached --stat   # sanity check
git commit -m "WIP: savepoint (pre-move from iCloud)" --no-verify
git push origin main

# Clone to ~/Code:
REPO_NAME=$(basename "$ROOT")
REMOTE_URL=$(git remote get-url origin)
DST="$HOME/Code/unified-trading-system-repos/$REPO_NAME"
mkdir -p "$(dirname "$DST")"
rm -rf "$DST"
git clone "$REMOTE_URL" "$DST"
cd "$DST" && git checkout main && git rev-parse HEAD
```

---

## CONTEXT

- Repo lives on iCloud Drive (slow).
- Goal: commit only real source/config, push to remote, then clone to `~/Code` for fast local work.
- Avoid full recursive scans (`find .`, `du` on whole repo).
- Use targeted checks only.

---

## PROMPT (copy to agent)

```
We are in a git repo on iCloud Drive (slow). Goal: commit only real source/config changes, push to remote, then clone to ~/Code for fast local work.

RULES:
- Avoid full recursive scans. Do NOT run `find .` or `du` on the whole repo.
- Use targeted checks only.
- Bypass hooks with `--no-verify` when committing.
- DO push at the end (we use remote as the fast copy mechanism).

STEPS:

1) Identify repo root + force main at current HEAD:
   - ROOT=$(git rev-parse --show-toplevel)
   - git checkout -B main
   - git status -sb

2) Ensure .gitignore exists and includes (append if missing):
   # Python
   .venv/
   venv/
   __pycache__/
   *.pyc
   .pytest_cache/
   .mypy_cache/
   .ruff_cache/
   .cache/
   # Node / UI
   node_modules/
   .next/
   dist/
   build/
   .turbo/
   # Coverage
   coverage/
   .nyc_output/
   # OS
   .DS_Store
   # Workspace
   .venv-workspace/

3) Ensure .cursorignore exists and includes:
   **/.venv/**
   **/venv/**
   **/node_modules/**
   **/.next/**
   **/dist/**
   **/build/**
   **/.turbo/**
   **/__pycache__/**
   **/.cache/**
   **/.venv-workspace/**

4) CRITICAL: detect whether junk dirs are ALREADY TRACKED (no filesystem scan):
   Run:
   git ls-files -z -- ".venv/*" "venv/*" "__pycache__/*" "node_modules/*" ".next/*" "dist/*" "build/*" ".turbo/*" ".venv-workspace/*" | wc -c
   If non-zero, remove from index (cached only, not disk):
   git rm -r --cached --ignore-unmatch .venv venv __pycache__ node_modules .next dist build .turbo .venv-workspace

5) Stage in safe order:
   git add .gitignore .cursorignore
   git add -A

6) Sanity check before commit:
   git status -sb
   git diff --cached --stat
   If the stat looks huge/unexpected (e.g. millions of lines from .venv), STOP and report.

7) Commit locally to main (no push yet):
   git commit -m "WIP: savepoint (pre-move from iCloud)" --no-verify

8) Push to remote:
   git push origin main

9) Clone to ~/Code (run from local machine, not iCloud):
   REPO_NAME=$(basename "$ROOT")
   REMOTE_URL=$(git remote get-url origin)
   DST="$HOME/Code/unified-trading-system-repos/$REPO_NAME"
   mkdir -p "$(dirname "$DST")"
   rm -rf "$DST"
   git clone "$REMOTE_URL" "$DST"
   cd "$DST" && git checkout main && git rev-parse HEAD

OUTPUT REQUIRED:
- Current branch + commit hash after push
- Whether tracked junk was found and removed (step 4)
- Cached diff stat lines (insertions/deletions)
- Push success/failure
- Clone destination path
```

---

## VARIATIONS

### If remote doesn't exist or push fails

Fallback: use **git bundle** (create on iCloud, copy single file, clone from bundle):

```bash
# In iCloud repo
git bundle create /tmp/REPO_NAME.bundle --all

# Copy /tmp/REPO_NAME.bundle to local (manual or cp)
# Then:
git clone /tmp/REPO_NAME.bundle "$HOME/Code/unified-trading-system-repos/REPO_NAME"
```

### If repo has no remote

Add remote first:

```bash
git remote add origin <URL>
git push -u origin main
```

### Batch for 61 repos

**Option A: One agent per repo**

- Launch 4–8 agents in parallel, each with `REPO_PATH` set to a different repo.
- Prepend to prompt: "REPO_PATH=/path/to/repo-X. cd $REPO_PATH. Then execute steps 1–9."

**Option B: Single agent with loop**

- Provide list of repo paths.
- Agent loops: for each path, cd there, run steps 1–8 (through push).
- Step 9 (clone): run once at end, looping over remote URLs from each repo.

**Option C: Clone-only batch (after all pushes done)**

```bash
# After all 61 repos have been pushed from iCloud
BASE="$HOME/Code/unified-trading-system-repos"
mkdir -p "$BASE"
# For each repo, if you have remote URLs:
while read url; do
  name=$(basename "$url" .git)
  git clone "$url" "$BASE/$name"
done < repo_urls.txt
```

---

## REFERENCE: What we did for unified-api-contracts

- Branch: main
- Commit: 7a18e01
- Tracked junk: none found
- Push: success (2768b20..7a18e01 main -> main)
- Remote: github.com:IggyIkenna/unified-api-contracts.git

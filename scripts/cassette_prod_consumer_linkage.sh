#!/usr/bin/env bash
# STEP 5.86: cassette_prod_consumer_linkage — fail if any cassette has no prod consumer.
#
# Delegates to unified_api_contracts.testing.cassette_orphan_checker which:
#   (a) scans external/<venue>/mocks/*.yaml for all cassettes
#   (b) scans workspace service repos for production imports / URL references
#   (c) applies tests/cassette_orphan_allowlist.yaml for documented exceptions
#   (d) exits 1 if any unallowlisted orphan cassette remains
#
# The allowlist check (step c) is enforced by the pytest integration in
# tests/test_cassette_orphan_checker.py (runs in QG STEP 3). This script
# provides a standalone shell-level failpoint that can be invoked without pytest.
#
# SSOT: plans/active/canary_coverage_qg_enforcement_2026_05_20.md Phase 2
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
ALLOWLIST="${REPO_ROOT}/tests/cassette_orphan_allowlist.yaml"

cd "$REPO_ROOT"

# Run orphan checker (exit 0 = clean; exit 1 = orphans found)
# Pipe through allowlist filtering in Python.
python3 - <<'PYEOF'
import sys
from pathlib import Path
import yaml

repo_root = Path.cwd()
sys.path.insert(0, str(repo_root))

from unified_api_contracts.testing.cassette_orphan_checker import (
    collect_all_cassette_files,
    scan_production_cassette_references,
    find_orphan_cassettes,
)

allowlist_path = repo_root / "tests" / "cassette_orphan_allowlist.yaml"
allowlist_data = yaml.safe_load(allowlist_path.read_text()) or {}
allowed_paths: set[str] = {entry["path"] for entry in allowlist_data.get("allowed", [])}

cassette_map = collect_all_cassette_files()
total = sum(len(v) for v in cassette_map.values())
referenced = scan_production_cassette_references(cassette_map=cassette_map)
orphans = find_orphan_cassettes(cassette_map, set(referenced.keys()))

unallowlisted = [
    (venue, path) for venue, path in orphans
    if f"{venue}/mocks/{path.name}" not in allowed_paths
]

print(f"[STEP 5.86] Scanned {total} cassettes across {len(cassette_map)} venues")
if unallowlisted:
    print(f"[STEP 5.86] FAIL: {len(unallowlisted)} unallowlisted orphan cassette(s):")
    for venue, path in unallowlisted:
        print(f"  {venue}/mocks/{path.name}")
    print("  Fix: add to tests/cassette_orphan_allowlist.yaml (with reason + acked_by) OR delete the cassette.")
    sys.exit(1)
else:
    allowlisted_count = len(orphans) - len(unallowlisted)
    print(f"[STEP 5.86] OK: no unallowlisted orphans ({allowlisted_count} allowlisted)")
    sys.exit(0)
PYEOF

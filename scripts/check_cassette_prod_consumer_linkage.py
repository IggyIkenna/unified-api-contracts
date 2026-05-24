#!/usr/bin/env python3
"""STEP 5.86: cassette_prod_consumer_linkage — fail if any cassette has no prod consumer.

Delegates to unified_api_contracts.testing.cassette_orphan_checker:
  (a) Scans external/<venue>/mocks/*.yaml for all cassettes.
  (b) Scans workspace service repos for production imports / URL references.
  (c) Applies tests/cassette_orphan_allowlist.yaml for documented exceptions.
  (d) Exits 1 if any unallowlisted orphan cassette remains.

The allowlist filtering mirrors the strict assertion in
tests/test_cassette_orphan_checker.py::TestIntegrationOrphanCheck::test_no_unallowlisted_orphans
which runs as part of QG STEP 3 (pytest sweep). This script provides a
standalone shell-level failpoint callable without pytest.

SSOT: plans/active/canary_coverage_qg_enforcement_2026_05_20.md Phase 2
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(_REPO_ROOT))

from unified_api_contracts.testing.cassette_orphan_checker import (  # noqa: E402 — after sys.path.insert
    collect_all_cassette_files,
    find_orphan_cassettes,
    scan_production_cassette_references,
)


def main() -> int:
    # Production consumers of external-source cassettes live in SIBLING repos (MTDS /
    # features / instruments adapters). In per-repo CI (workspace-qg renders dep_repos="")
    # only this repo is checked out, so the workspace consumer-scan finds nothing and every
    # such cassette looks orphan. Cross-repo consumer linkage is validated under local
    # quality-gates.sh / the full-workspace SIT job; skip when siblings are absent rather
    # than emit false orphans. (Mirrors the test_no_unallowlisted_orphans pytest guard.)
    _workspace_root = _REPO_ROOT.parent
    if not (_workspace_root / "market-tick-data-service").is_dir():
        print(
            "[STEP 5.86] SKIP: sibling consumer repos not checked out (per-repo CI); "
            "cassette→prod-consumer linkage is validated in the full-workspace SIT"
        )
        return 0

    allowlist_path = _REPO_ROOT / "tests" / "cassette_orphan_allowlist.yaml"
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
        return 1

    allowlisted_count = len(orphans) - len(unallowlisted)
    print(f"[STEP 5.86] OK: no unallowlisted orphans ({allowlisted_count} allowlisted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

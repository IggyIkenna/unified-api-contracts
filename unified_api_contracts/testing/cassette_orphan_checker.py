"""Cassette orphan checker for UAC.

Scans for:
1. Orphan cassettes: YAML files in external/<venue>/mocks/ that have no
   corresponding test referencing them (by filename).
2. Missing cassettes: Test files that reference cassette filenames that
   do not exist in any external/<venue>/mocks/ directory.

Usage as a script::

    python -m unified_api_contracts.testing.cassette_orphan_checker

Usage in quality-gates.sh::

    python -m unified_api_contracts.testing.cassette_orphan_checker --warn-only

Usage from Python::

    from unified_api_contracts.testing.cassette_orphan_checker import (
        find_orphan_cassettes,
        find_missing_cassettes,
        scan_test_cassette_references,
    )
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Root of the UAC package
_PKG_ROOT: Path = Path(__file__).resolve().parents[1]
_EXTERNAL_ROOT: Path = _PKG_ROOT / "external"
_REPO_ROOT: Path = _PKG_ROOT.parent


def collect_all_cassette_files() -> dict[str, list[Path]]:
    """Collect all cassette YAML files grouped by venue.

    Returns:
        Dict mapping venue name to list of cassette Paths.
    """
    result: dict[str, list[Path]] = {}
    for venue_dir in sorted(_EXTERNAL_ROOT.iterdir()):
        if not venue_dir.is_dir():
            continue
        mocks_dir = venue_dir / "mocks"
        if not mocks_dir.is_dir():
            continue
        yamls = sorted(mocks_dir.glob("*.yaml"))
        if yamls:
            result[venue_dir.name] = yamls
    return result


def scan_test_cassette_references(test_root: Path) -> set[str]:
    """Scan Python test files for cassette filename references.

    Looks for patterns like:
    - "auth_test.yaml"
    - 'meta_and_asset_ctxs.yaml'
    - load_cassette("venue", "filename.yaml")
    - get_cassette_path("venue", "filename.yaml")
    - Path references ending in .yaml

    Returns:
        Set of cassette filenames (just the name, no path).
    """
    referenced: set[str] = set()
    yaml_pattern = re.compile(r"""['"]([a-zA-Z0-9_.-]+\.yaml)['"]""")

    test_dirs = [test_root / "tests"] if (test_root / "tests").is_dir() else [test_root]
    for test_dir in test_dirs:
        for py_file in test_dir.rglob("*.py"):
            # Skip __pycache__ and .venv
            if "__pycache__" in str(py_file) or ".venv" in str(py_file):
                continue
            content = py_file.read_text(encoding="utf-8", errors="replace")
            matches = yaml_pattern.findall(content)
            referenced.update(matches)

    return referenced


def find_orphan_cassettes(
    cassette_map: dict[str, list[Path]],
    referenced_names: set[str],
) -> list[tuple[str, Path]]:
    """Find cassettes that exist on disk but have no test reference.

    Returns:
        List of (venue, cassette_path) tuples for orphan cassettes.
    """
    orphans: list[tuple[str, Path]] = []
    for venue, paths in cassette_map.items():
        for cassette_path in paths:
            if cassette_path.name not in referenced_names:
                orphans.append((venue, cassette_path))
    return orphans


def find_missing_cassettes(
    cassette_map: dict[str, list[Path]],
    referenced_names: set[str],
) -> list[str]:
    """Find cassette names referenced in tests that do not exist on disk.

    Returns:
        List of cassette filenames that are referenced but missing.
    """
    all_cassette_names: set[str] = set()
    for paths in cassette_map.values():
        for p in paths:
            all_cassette_names.add(p.name)

    missing: list[str] = []
    for name in sorted(referenced_names):
        # Only check .yaml files that look like cassette names
        if name.endswith(".yaml") and name not in all_cassette_names:
            # Exclude known non-cassette YAML references (config files, etc.)
            if any(
                skip in name.lower()
                for skip in ["config", "settings", "pyproject", "docker"]
            ):
                continue
            missing.append(name)
    return missing


def run_orphan_check(warn_only: bool = True) -> int:
    """Run the full orphan check and print results.

    Args:
        warn_only: If True, orphans produce warnings (exit 0).
                   If False, orphans produce errors (exit 1).

    Returns:
        Exit code (0 = clean, 1 = issues found in strict mode).
    """
    cassette_map = collect_all_cassette_files()
    total_cassettes = sum(len(v) for v in cassette_map.values())

    # Scan both UAC tests and workspace-level test references
    referenced = scan_test_cassette_references(_REPO_ROOT)

    orphans = find_orphan_cassettes(cassette_map, referenced)
    missing = find_missing_cassettes(cassette_map, referenced)

    print(f"[cassette-orphan-check] Scanned {total_cassettes} cassettes "
          f"across {len(cassette_map)} venues")
    print(f"[cassette-orphan-check] Found {len(referenced)} cassette "
          f"references in test files")

    exit_code = 0

    if orphans:
        level = "WARN" if warn_only else "FAIL"
        print(f"\n[cassette-orphan-check] {level}: {len(orphans)} orphan "
              f"cassette(s) with no test reference:")
        for venue, path in orphans:
            print(f"  {venue}/mocks/{path.name}")
        if not warn_only:
            exit_code = 1
    else:
        print("[cassette-orphan-check] No orphan cassettes found.")

    if missing:
        level = "WARN" if warn_only else "FAIL"
        print(f"\n[cassette-orphan-check] {level}: {len(missing)} cassette "
              f"reference(s) with no matching file:")
        for name in missing:
            print(f"  {name}")
        if not warn_only:
            exit_code = 1
    else:
        print("[cassette-orphan-check] No missing cassette references found.")

    return exit_code


if __name__ == "__main__":
    warn_only = "--warn-only" in sys.argv or "--warn" in sys.argv
    sys.exit(run_orphan_check(warn_only=warn_only))

"""Cassette orphan checker for UAC.

Scans for:
1. Orphan cassettes: YAML files in external/<venue>/mocks/ that have no
   corresponding **production** consumer (a file in a service repo that
   references either the venue's deep-path import, a pydantic class defined
   in the venue's external module, or the cassette's URL host).
2. Missing cassettes: Test files reference cassette filenames that do not
   exist in any external/<venue>/mocks/ directory.

The orphan definition is intentionally PRODUCTION-centric (per the
2026-05-20 canary-coverage QG enforcement plan): a cassette only
exists to protect a real prod consumer from upstream drift. Test-file
references alone are NOT sufficient — a cassette that is only ever
read by a UAC unit test (and never by a real adapter / handler /
connector) is a prod-orphan and should be allowlisted with a documented
reason or deleted.

Usage as a script::

    python -m unified_api_contracts.testing.cassette_orphan_checker

Usage in quality-gates.sh::

    python -m unified_api_contracts.testing.cassette_orphan_checker --warn-only

Usage from Python::

    from unified_api_contracts.testing.cassette_orphan_checker import (
        find_orphan_cassettes,
        find_missing_cassettes,
        scan_production_cassette_references,
    )
"""

from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

import yaml

# Root of the UAC package
_PKG_ROOT: Path = Path(__file__).resolve().parents[1]
_EXTERNAL_ROOT: Path = _PKG_ROOT / "external"
_REPO_ROOT: Path = _PKG_ROOT.parent
# Workspace root is the parent of all service repos. UAC may live at
# <workspace>/unified-api-contracts OR at <workspace>/.tabs/<N>/unified-api-contracts
# (per-tab worktree layout). The workspace root is the first ancestor that
# contains both `unified-api-contracts/` AND another `*-service/` sibling.
_WORKSPACE_ROOT: Path = _REPO_ROOT.parent


# Directory names whose presence ANYWHERE in a file's path-parts-below-the-root
# excludes the file. We only exclude clearly-non-production locations.
# NOTE: we intentionally do NOT include `.tabs` here — when UAC is run from
# inside a `.tabs/<N>/` worktree the workspace-root walk legitimately passes
# through `.tabs/<N>/`. Per-tab isolation is enforced by choosing the
# workspace_root, not by part-name exclusion.
_DEFAULT_EXCLUDE_DIRS: tuple[str, ...] = (
    ".venv",
    ".venv-workspace",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
    ".git",
    "tests",
)


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


def _venue_external_classes(venue: str) -> set[str]:
    """Return the set of pydantic class names defined under external/<venue>/*.py."""
    venue_dir = _EXTERNAL_ROOT / venue
    classes: set[str] = set()
    if not venue_dir.is_dir():
        return classes
    class_re = re.compile(r"^class\s+([A-Z][A-Za-z0-9_]*)\s*[(:\s]", re.MULTILINE)
    for py in venue_dir.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        try:
            content = py.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        classes.update(class_re.findall(content))
    return classes


def _cassette_hosts(cassette_path: Path) -> set[str]:
    """Return the set of URL hosts referenced inside a cassette YAML.

    Walks the cassette's ``interactions[*].request.uri`` (vcrpy format) and
    extracts the hostname. If YAML parsing fails OR no interactions field is
    present, falls back to a tightly-scoped regex that only looks at lines
    starting with ``uri:`` / ``url:`` (a vcrpy structural anchor) — this
    avoids harvesting every documentation URL inside a cassette body
    (otherwise a cassette with embedded markdown can contribute thousands of
    bogus hosts and torpedo the workspace-wide scan).
    """
    hosts: set[str] = set()
    try:
        content = cassette_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return hosts
    parsed = False
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        data = None
    if isinstance(data, dict):
        interactions = data.get("interactions")
        if isinstance(interactions, list):
            parsed = True
            for inter in interactions:
                if not isinstance(inter, dict):
                    continue
                req = inter.get("request")
                if not isinstance(req, dict):
                    continue
                uri = req.get("uri") or req.get("url")
                if isinstance(uri, str):
                    m = re.match(r"https?://([^/:]+)", uri)
                    if m:
                        hosts.add(m.group(1).lower())
    if not parsed:
        # Anchored fallback — only URIs on vcrpy structural lines.
        for m in re.finditer(
            r"^\s*(?:uri|url):\s*['\"]?(https?://([A-Za-z0-9_.-]+))",
            content,
            re.MULTILINE,
        ):
            hosts.add(m.group(2).lower())
    return hosts


def _iter_python_files(root: Path, exclude_dirs: tuple[str, ...]) -> list[Path]:
    """Yield every .py file under root, skipping excluded directory names.

    Only the path components BELOW ``root`` are checked against ``exclude_dirs``,
    so workspace-prefix names (e.g. ``.tabs``) cannot accidentally exclude an
    otherwise-legitimate production file.
    """
    results: list[Path] = []
    if not root.is_dir():
        return results
    root_resolved = root.resolve()
    for path in root.rglob("*.py"):
        try:
            rel = path.resolve().relative_to(root_resolved)
        except ValueError:
            continue
        if any(ex in rel.parts for ex in exclude_dirs):
            continue
        results.append(path)
    return results


def _default_production_paths() -> list[Path]:
    """Return service-repo directories that constitute the "production" surface.

    A directory is treated as a service repo if it sits at workspace root
    AND contains a ``pyproject.toml`` AND a same-named Python package
    directory (e.g. ``market-tick-data-service/market_tick_data_service/``).

    UAC itself is **excluded** — UAC owns the cassettes; scanning UAC's own
    capability declarations / external module bodies would self-reference
    every venue cassette and mask real prod-orphans (capability declarations
    are *intent to support a venue*, not *production consumer of its data*).
    """
    candidates: list[Path] = []
    if not _WORKSPACE_ROOT.is_dir():
        return candidates
    for child in sorted(_WORKSPACE_ROOT.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name in _DEFAULT_EXCLUDE_DIRS:
            continue
        if child.name == "unified-api-contracts":
            continue  # self-reference; cassettes live here.
        pkg_name = child.name.replace("-", "_")
        pkg_dir = child / pkg_name
        if (child / "pyproject.toml").is_file() and pkg_dir.is_dir():
            candidates.append(pkg_dir)
    return candidates


def scan_production_cassette_references(
    production_paths: list[Path] | None = None,
    cassette_map: dict[str, list[Path]] | None = None,
) -> dict[tuple[str, str], set[Path]]:
    """Scan production source for evidence each cassette has a real consumer.

    A cassette is considered "production-referenced" if ANY production-path
    file matches at least one of:
      (a) ``from unified_api_contracts.<venue>`` deep-path import
      (b) any pydantic class name defined under ``external/<venue>/*.py``
      (c) any URL host parsed from the cassette's ``request.uri`` field

    Args:
        production_paths: List of directory roots to scan. Defaults to
            every `<service>/<service_pkg>/` discovered under workspace root.
        cassette_map: Pre-collected cassette map (see :func:`collect_all_cassette_files`).

    Returns:
        Dict mapping (venue, cassette filename) -> set of production-file paths
        that reference it. Cassettes absent from the dict are prod-orphans.
        The key is (venue, name) and NOT name-only because cassette filenames
        like ``ticker.yaml`` recur across venues; collapsing on name would
        attribute one venue's consumer to another's cassette.
    """
    if production_paths is None:
        production_paths = _default_production_paths()
    if cassette_map is None:
        cassette_map = collect_all_cassette_files()

    venues: list[str] = list(cassette_map.keys())

    # Per-venue cheap-substring evidence. We use plain ``in`` substring
    # checks (no regex) because the cost dominates over 4k+ production
    # files x 80+ venues. False positives are filtered by structure:
    #   - import token: ``from unified_api_contracts.<venue>`` is a long
    #     unique string; cheap substring check is precise.
    #   - class names: pydantic classes in ``external/<venue>/*.py`` are
    #     venue-prefixed by convention; substring check on the class
    #     identifier is precise enough (a same-substring identifier in
    #     another file is vanishingly rare; if it happens, the cassette
    #     becomes "referenced" — i.e. we err on the side of NOT flagging
    #     a false orphan, which is the right direction for a gate).
    venue_import_tokens: dict[str, str] = {venue: f"from unified_api_contracts.{venue}" for venue in venues}
    venue_class_names: dict[str, list[str]] = {}
    for venue in venues:
        classes = _venue_external_classes(venue)
        if classes:
            venue_class_names[venue] = sorted(classes)

    # Per-cassette hosts (parsed once).
    cassette_hosts: dict[Path, set[str]] = {}
    all_hosts: set[str] = set()
    for paths in cassette_map.values():
        for p in paths:
            hosts = _cassette_hosts(p)
            cassette_hosts[p] = hosts
            all_hosts.update(hosts)

    references: dict[tuple[str, str], set[Path]] = {}

    for root in production_paths:
        for py in _iter_python_files(root, _DEFAULT_EXCLUDE_DIRS):
            try:
                content = py.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                continue

            # Which venues does this file evidence?
            venues_hit: set[str] = set()
            for venue, token in venue_import_tokens.items():
                if token in content:
                    venues_hit.add(venue)
            for venue, classes in venue_class_names.items():
                if venue in venues_hit:
                    continue
                for cls in classes:
                    if cls in content:
                        venues_hit.add(venue)
                        break

            # Which hosts does this file mention? Single linear pass.
            file_hosts: set[str] = {h for h in all_hosts if h and h in content}

            for venue, cassettes in cassette_map.items():
                venue_hit = venue in venues_hit
                for cassette_path in cassettes:
                    key = (venue, cassette_path.name)
                    if venue_hit:
                        references.setdefault(key, set()).add(py)
                        continue
                    hosts = cassette_hosts.get(cassette_path, set())
                    if hosts and (hosts & file_hosts):
                        references.setdefault(key, set()).add(py)
    return references


def scan_test_cassette_references(
    test_root: Path | None = None,
    *,
    production_paths: list[Path] | None = None,
) -> set[str]:
    """Scan production source for cassette references (legacy signature).

    .. deprecated:: 2026-05-20
        The original implementation scanned TEST files for cassette
        filename references. That is the wrong target for orphan-detection:
        a cassette only protects a production consumer. This function now
        delegates to :func:`scan_production_cassette_references` and ignores
        ``test_root``. The ``test_root`` parameter is kept for backwards
        compatibility; pass ``production_paths`` explicitly for the new
        behaviour.

    Returns:
        Set of cassette filenames (no path) that are production-referenced
        by *some* venue. Note this loses the per-venue precision of
        :func:`scan_production_cassette_references` and may overstate
        coverage for cassette names like ``ticker.yaml`` that recur across
        venues. New callers should use the venue-aware function directly.
    """
    if test_root is not None and production_paths is None:
        warnings.warn(
            "scan_test_cassette_references(test_root=...) is deprecated; "
            "the checker now scans PRODUCTION paths (not test files). "
            "Use scan_production_cassette_references(production_paths=...) directly.",
            DeprecationWarning,
            stacklevel=2,
        )
    refs = scan_production_cassette_references(production_paths=production_paths)
    return {name for _venue, name in refs}


def find_orphan_cassettes(
    cassette_map: dict[str, list[Path]],
    referenced_names: set[str] | set[tuple[str, str]],
) -> list[tuple[str, Path]]:
    """Find cassettes that exist on disk but have no production reference.

    Accepts either:
    - A venue-aware set of ``(venue, name)`` tuples (preferred — keys returned
      by :func:`scan_production_cassette_references`).
    - A flat ``set[str]`` of cassette filenames (legacy — kept for
      backwards-compat callers; **loses per-venue precision** and may
      under-report orphans for cassette names like ``ticker.yaml``).

    Returns:
        List of (venue, cassette_path) tuples for orphan cassettes.
    """
    is_venue_aware = bool(referenced_names) and isinstance(next(iter(referenced_names)), tuple)
    orphans: list[tuple[str, Path]] = []
    for venue, paths in cassette_map.items():
        for cassette_path in paths:
            if is_venue_aware:
                key: object = (venue, cassette_path.name)
            else:
                key = cassette_path.name
            if key not in referenced_names:
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
            if any(skip in name.lower() for skip in ["config", "settings", "pyproject", "docker"]):
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

    referenced = scan_production_cassette_references(cassette_map=cassette_map)
    referenced_keys: set[tuple[str, str]] = set(referenced.keys())
    referenced_names: set[str] = {name for _v, name in referenced_keys}

    orphans = find_orphan_cassettes(cassette_map, referenced_keys)
    missing = find_missing_cassettes(cassette_map, referenced_names)

    print(f"[cassette-orphan-check] Scanned {total_cassettes} cassettes across {len(cassette_map)} venues")
    print(f"[cassette-orphan-check] Found {len(referenced_names)} cassette(s) with a production consumer")

    exit_code = 0

    if orphans:
        level = "WARN" if warn_only else "FAIL"
        print(f"\n[cassette-orphan-check] {level}: {len(orphans)} orphan cassette(s) with no production consumer:")
        for venue, path in orphans:
            print(f"  {venue}/mocks/{path.name}")
        if not warn_only:
            exit_code = 1
    else:
        print("[cassette-orphan-check] No orphan cassettes found.")

    if missing:
        level = "WARN" if warn_only else "FAIL"
        print(f"\n[cassette-orphan-check] {level}: {len(missing)} cassette reference(s) with no matching file:")
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

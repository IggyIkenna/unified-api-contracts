#!/usr/bin/env python3
"""STEP 5.87: prod_url_has_cassette — every production HTTP/WS host must have a cassette.

Algorithm:
1. Build "covered_hosts" from all cassette YAML files (VCR request.uri + WS ws_url).
2. Scan production Python source in workspace service repos for URL literals.
3. Extract unique hostnames from found URL strings.
4. Apply allowlist (scripts/quality-gates-allowlists/prod-url-no-cassette.txt).
5. Report any host not in covered_hosts and not in allowlist.

Exit 0 = all good. Exit 1 = uncovered hosts found.

SSOT: plans/active/canary_coverage_qg_enforcement_2026_05_20.md Phase 2
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

# ── Paths ────────────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXTERNAL_ROOT = _REPO_ROOT / "unified_api_contracts" / "external"
_ALLOWLIST_PATH = _REPO_ROOT / "scripts" / "quality-gates-allowlists" / "prod-url-no-cassette.txt"

# Workspace root: parent of the UAC repo (handles .tabs/<N>/ worktree layout)
_WORKSPACE_ROOT = _REPO_ROOT.parent

# Service repos to scan for URL literals (data-layer services only)
_SCAN_REPO_NAMES = (
    "market-tick-data-service",
    "instruments-service",
    "execution-service",
    "features-onchain-service",
)

# Python source subdirectories within each service repo to scan
_SCAN_SUBDIR_PATTERNS = (
    "*/adapters",
    "*/connectors",
    "*/handlers",
    "*/clients",
    "*/providers",
    "*/live",
    "*/batch",
)

# URL pattern — match http/https/ws/wss URLs in Python string literals
_URL_RE = re.compile(
    r"""(?:https?|wss?)://([a-zA-Z0-9][a-zA-Z0-9.\-]{2,}(?::[0-9]+)?)""",
)

# Strip port from host
_PORT_RE = re.compile(r":[0-9]+$")


def _load_allowlist() -> list[str]:
    """Load the no-cassette allowlist. Returns list of host patterns."""
    if not _ALLOWLIST_PATH.exists():
        return []
    lines = []
    for line in _ALLOWLIST_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def _host_is_allowlisted(host: str, allowlist: list[str]) -> bool:
    """Check if a hostname matches any allowlist entry (exact or suffix)."""
    host_lower = host.lower()
    for entry in allowlist:
        if entry.startswith("."):
            # Suffix match: .googleapis.com matches foo.googleapis.com
            if host_lower.endswith(entry.lower()):
                return True
        else:
            if host_lower == entry.lower():
                return True
    return False


def _extract_covered_hosts() -> set[str]:
    """Build set of hosts covered by existing UAC cassettes."""
    covered: set[str] = set()
    for cassette_path in _EXTERNAL_ROOT.glob("*/mocks/*.yaml"):
        try:
            data = yaml.safe_load(cassette_path.read_text()) or {}
        except yaml.YAMLError:
            continue

        # VCR format: interactions[].request.uri
        for interaction in data.get("interactions", []):
            uri = interaction.get("request", {}).get("uri", "")
            if uri:
                parsed = urlparse(uri)
                if parsed.hostname:
                    covered.add(_PORT_RE.sub("", parsed.hostname.lower()))

        # WS format: ws_url
        ws_url = data.get("ws_url", "")
        if ws_url:
            parsed = urlparse(ws_url)
            if parsed.hostname:
                covered.add(_PORT_RE.sub("", parsed.hostname.lower()))

    return covered


def _scan_service_repos() -> dict[str, set[str]]:
    """Scan production Python files in service repos for URL literals.

    Returns:
        Dict mapping each found URL host to the set of source files referencing it.
    """
    host_to_files: dict[str, set[str]] = {}

    for repo_name in _SCAN_REPO_NAMES:
        repo_dir = _WORKSPACE_ROOT / repo_name
        if not repo_dir.is_dir():
            # Try .tabs/<N>/<repo_name> layout
            for tabs_dir in _WORKSPACE_ROOT.glob(".tabs/*/*"):
                if tabs_dir.name == repo_name and tabs_dir.is_dir():
                    repo_dir = tabs_dir
                    break
            if not repo_dir.is_dir():
                continue

        # Collect Python files to scan
        py_files: list[Path] = []
        for subdir_pattern in _SCAN_SUBDIR_PATTERNS:
            for subdir in repo_dir.glob(subdir_pattern):
                if subdir.is_dir():
                    py_files.extend(subdir.rglob("*.py"))
        # Also scan top-level service package directly
        pkg_name = repo_name.replace("-", "_")
        pkg_dir = repo_dir / pkg_name
        if pkg_dir.is_dir():
            py_files.extend(pkg_dir.rglob("*.py"))

        seen: set[Path] = set()
        for py_file in py_files:
            if py_file in seen:
                continue
            seen.add(py_file)

            # Skip tests, migrations, generated files
            parts = py_file.parts
            if any(p in parts for p in ("tests", "test", "migrations", ".venv", "__pycache__")):
                continue

            try:
                content = py_file.read_text(errors="replace")
            except OSError:
                continue

            for match in _URL_RE.finditer(content):
                raw_host = match.group(1)
                host = _PORT_RE.sub("", raw_host).lower()
                # Skip template variables like {host}, {endpoint}
                if "{" in host or "}" in host:
                    continue
                # Skip example/placeholder hosts
                if host in ("example.com", "example.org", "your-host.com", "hostname"):
                    continue
                host_to_files.setdefault(host, set()).add(str(py_file.relative_to(_WORKSPACE_ROOT)))

    return host_to_files


def main(warn_only: bool = False) -> int:
    covered_hosts = _extract_covered_hosts()
    allowlist = _load_allowlist()
    host_to_files = _scan_service_repos()

    scanned_repos = [r for r in _SCAN_REPO_NAMES if (_WORKSPACE_ROOT / r).is_dir()]
    print(f"[STEP 5.87] Covered hosts from cassettes: {len(covered_hosts)}")
    print(f"[STEP 5.87] Scanned repos: {', '.join(scanned_repos) or '(none found in workspace)'}")
    print(f"[STEP 5.87] Unique prod URL hosts found: {len(host_to_files)}")

    uncovered: list[tuple[str, list[str]]] = []
    for host, files in sorted(host_to_files.items()):
        if host in covered_hosts:
            continue
        if _host_is_allowlisted(host, allowlist):
            continue
        uncovered.append((host, sorted(files)[:2]))  # show up to 2 example files

    if uncovered:
        level = "WARN" if warn_only else "FAIL"
        print(f"\n[STEP 5.87] {level}: {len(uncovered)} production URL host(s) have no UAC cassette:")
        for host, example_files in uncovered[:30]:  # cap output to 30 hosts
            print(f"  {host}")
            for f in example_files:
                print(f"      in: {f}")
        if len(uncovered) > 30:
            print(f"  ... and {len(uncovered) - 30} more (run script directly for full list)")
        print(
            "\n  Fix options:"
            "\n    (a) Add a cassette at external/<venue>/mocks/<endpoint>.yaml"
            "\n    (b) Add the host to scripts/quality-gates-allowlists/prod-url-no-cassette.txt"
            "          (with a comment explaining why no cassette is needed)"
        )
        return 0 if warn_only else 1

    print(f"[STEP 5.87] OK: all {len(host_to_files)} production URL hosts have cassette coverage or are allowlisted")
    return 0


if __name__ == "__main__":
    warn_only = "--warn-only" in sys.argv or "--warn" in sys.argv
    sys.exit(main(warn_only=warn_only))

#!/usr/bin/env python3
# Epic: infrastructure_master
# Lifecycle: permanent
# Delete-when: NA
"""
Check SDK version alignment between api-contracts and its interface consumers.

Parses api-contracts pyproject.toml [schema-validation] for pinned SDK versions.
For each interface, reads their pyproject.toml and extracts SDK deps (databento,
tardis-client, ccxt, ib_insync). FAILs (exit 1) if:
- Interface uses SDK version X and api-contracts has no schemas for that version
- Version ranges don't overlap (for databento, ccxt, ib_insync, tardis-client)

Interfaces without SDK deps: skip SDK alignment for those packages.

Does NOT check a consumer's declared api-contracts version range against api-contracts'
own version — that concern is superseded by
unified-trading-pm/scripts/cicd/assert_version_coherence.py's _check_dep_floors() (wired
into PM's quality-gates.sh), which resolves api-contracts' current version from
workspace-manifest.json's git-tag-aware versions{} cache. A version-overlap check used to
live here but was removed 2026-08-03: it read api-contracts' own version from this repo's
pyproject.toml [project].version, which is always "" (api-contracts is version_source:
git-tag, i.e. dynamic/hatch-vcs — no committed version line), so the check silently no-op'd
for every consumer; it was also independently broken by a dependency-key mismatch (it
looked up the literal key "api-contracts", but every real consumer's pyproject.toml
declares the dependency as "unified-api-contracts"), so it never fired even on a non-empty
version. Not wired into any workflow at the time of removal (grep-confirmed).

Path resolution: interfaces at ../repo_name relative to api-contracts root.
Use --interface-path to check a single interface (path resolved relative to cwd).
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import tomllib
from pathlib import Path
from typing import cast

logger = logging.getLogger(__name__)

# SDK package -> api-contracts schema module (must exist)
SDK_TO_SCHEMA_MODULE: dict[str, str] = {
    "databento": "unified_api_contracts.databento",
    "tardis-client": "unified_api_contracts.tardis",
    "tardis_client": "unified_api_contracts.tardis",
    "ccxt": "unified_api_contracts.ccxt",
    "ib_insync": "unified_api_contracts.ibkr",
}

# All api-contracts consumers (relative to api-contracts root)
INTERFACES: list[tuple[str, Path]] = [
    ("unified-market-interface", Path("../unified-market-interface")),
    ("unified-trade-execution-interface", Path("../unified-trade-execution-interface")),
    ("unified-reference-data-interface", Path("../unified-reference-data-interface")),
    ("unified-cloud-interface", Path("../unified-cloud-interface")),
    ("unified-trading-library", Path("../unified-trading-library")),
    ("market-tick-data-handler", Path("../market-tick-data-handler")),
    ("instruments-service", Path("../instruments-service")),
    ("execution-services", Path("../execution-services")),
    # pnl-attribution-service archived — consolidated into strategy-service/pnl
    ("ml-inference-service", Path("../ml-inference-service")),
    ("ml-training-service", Path("../ml-training-service")),
    ("features-volatility-service", Path("../features-volatility-service")),
    ("features-onchain-service", Path("../features-onchain-service")),
    # position-balance-monitor-service archived — consolidated into strategy-service/position
    ("features-calendar-service", Path("../features-calendar-service")),
    ("features-delta-one-service", Path("../features-delta-one-service")),
    # risk-and-exposure-service archived — consolidated into strategy-service/risk
    ("strategy-service", Path("../strategy-service")),
    ("alerting-service", Path("../alerting-service")),
    ("market-data-processing-service", Path("../market-data-processing-service")),
]


def _repo_root() -> Path:
    """api-contracts repo root (parent of scripts/)."""
    root = Path(__file__).resolve().parent.parent
    assert (root / "unified_api_contracts").is_dir(), f"Expected api_contracts at {root}"
    return root


def _parse_deps_from_pyproject(path: Path) -> dict[str, str]:
    """Parse [project] dependencies from pyproject.toml. Returns pkg -> spec."""
    if not path.exists():
        return {}
    with path.open("rb") as f:
        data = cast(dict[str, object], tomllib.load(f))
    deps: dict[str, str] = {}
    project = data.get("project")
    deps_list: list[str] = cast(list[str], project.get("dependencies", [])) if isinstance(project, dict) else []
    for spec in deps_list:
        pkg = re.split(r"[>=<~!]", spec)[0].strip()
        deps[pkg] = spec
    return deps


def _parse_schema_validation_deps(root: Path) -> dict[str, str]:
    """Parse [schema-validation] optional deps from api-contracts pyproject.toml."""
    path = root / "pyproject.toml"
    if not path.exists():
        return {}
    with path.open("rb") as f:
        data = cast(dict[str, object], tomllib.load(f))
    deps: dict[str, str] = {}
    project = data.get("project")
    opt_deps: dict[str, object] | None = (
        cast(dict[str, object], project.get("optional-dependencies", {})) if isinstance(project, dict) else None
    )
    schema_deps: list[str] = (
        cast(list[str], opt_deps.get("schema-validation", [])) if isinstance(opt_deps, dict) else []
    )
    for spec in schema_deps:
        pkg = re.split(r"[>=<~!]", spec)[0].strip()
        deps[pkg] = spec
    return deps


def _extract_version_spec(spec: str) -> str:
    """Extract version part from 'pkg>=1.0' or 'pkg>=1.0,<2.0'."""
    m = re.match(r"^[a-zA-Z0-9_.-]+(.*)$", spec.strip())
    return m.group(1).strip() if m and m.group(1).strip() else spec


def _version_ranges_overlap(api_spec: str, iface_spec: str) -> bool:
    """Check if two version specs overlap using `packaging`."""
    api_ver = _extract_version_spec(api_spec)
    iface_ver = _extract_version_spec(iface_spec)
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version

    api_ss = SpecifierSet(api_ver)
    iface_ss = SpecifierSet(iface_ver)
    # Try a version that satisfies api-contracts; if it also satisfies interface, overlap
    for candidate in _candidate_versions(api_ver):
        try:
            v = Version(candidate)
            if api_ss.contains(v) and iface_ss.contains(v):
                return True
        except (ConnectionError, TimeoutError, OSError, ValueError) as e:
            logger.warning("Skipping item during version ranges overlap: %s", e)
            continue
    # Try a version that satisfies interface
    for candidate in _candidate_versions(iface_ver):
        try:
            v = Version(candidate)
            if api_ss.contains(v) and iface_ss.contains(v):
                return True
        except (ConnectionError, TimeoutError, OSError, ValueError) as e:
            logger.warning("Skipping item during version ranges overlap: %s", e)
            continue
    return False


def _candidate_versions(spec: str) -> list[str]:
    """Extract candidate versions from spec for overlap check."""
    candidates: list[str] = []
    # >=X.Y.Z -> try X.Y.Z
    m = re.search(r">=\s*([\d.]+)", spec)
    if m:
        candidates.append(m.group(1))
    # ==X.Y.Z
    m = re.search(r"==\s*([\d.]+)", spec)
    if m:
        candidates.append(m.group(1))
    # ~=X.Y.Z -> try X.Y.Z
    m = re.search(r"~=\s*([\d.]+)", spec)
    if m:
        candidates.append(m.group(1))
    return candidates


def _schema_module_exists(root: Path, module: str) -> bool:
    """Check that the schema module exists (e.g. unified_api_contracts/ccxt/ or .../external/ccxt/)."""
    parts = module.split(".")
    if parts[0] != "unified_api_contracts":
        return False
    # Venue/SDK modules mostly live under external/; check both locations.
    base = root / "unified_api_contracts"
    subdir = base / parts[1]
    if not subdir.exists():
        subdir = base / "external" / parts[1]
    return (subdir / "schemas.py").exists() or (subdir / "__init__.py").exists()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check SDK version alignment between api-contracts and consumers.")
    parser.add_argument(
        "--interface-path",
        type=str,
        default=None,
        metavar="PATH",
        help="Check only this interface (path resolved relative to cwd). When omitted, check all INTERFACES.",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    root = _repo_root()
    api_deps = _parse_schema_validation_deps(root)
    errors: list[str] = []

    if args.interface_path is not None:
        iface_path = Path(args.interface_path).resolve()
        if not iface_path.exists():
            logger.error(f"ERROR: interface path does not exist: {iface_path}")
            return 1
        if not iface_path.is_dir():
            logger.info(
                f"ERROR: --interface-path must be a directory: {iface_path}",
                file=sys.stderr,
            )
            return 1
        if not (iface_path / "pyproject.toml").exists():
            logger.info(
                f"ERROR: no pyproject.toml at {iface_path}",
                file=sys.stderr,
            )
            return 1
        interfaces_to_check: list[tuple[str, Path]] = [
            (iface_path.name, iface_path),
        ]
    else:
        interfaces_to_check = [(name, (root / rel_path).resolve()) for name, rel_path in INTERFACES]

    for iface_name, iface_path in interfaces_to_check:
        if not iface_path.exists() or not (iface_path / "pyproject.toml").exists():
            continue
        iface_deps = _parse_deps_from_pyproject(iface_path / "pyproject.toml")
        if not iface_deps:
            continue

        # SDK alignment (skip for interfaces that don't have those SDK deps)
        for sdk_pkg, schema_module in SDK_TO_SCHEMA_MODULE.items():
            if sdk_pkg not in iface_deps:
                continue
            iface_spec = iface_deps[sdk_pkg]

            # api-contracts must have schemas for this SDK
            if not _schema_module_exists(root, schema_module):
                errors.append(f"{iface_name}: uses {sdk_pkg} but api-contracts has no schemas for {schema_module}")
                continue

            # api-contracts must have this SDK in schema-validation
            if sdk_pkg not in api_deps:
                errors.append(
                    f"{iface_name}: uses {sdk_pkg} but api-contracts [schema-validation] "
                    f"does not pin {sdk_pkg} (add to pyproject.toml)"
                )
                continue

            api_spec = api_deps[sdk_pkg]
            if not _version_ranges_overlap(api_spec, iface_spec):
                errors.append(f"{iface_name}: {sdk_pkg} {iface_spec} does not overlap with api-contracts {api_spec}")

    if errors:
        for e in errors:
            logger.error(f"ERROR: {e}")
        return 1
    logger.info("SDK version alignment OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Check that all public classes defined in UAC core source files are exported in __all__.

Algorithm:
1. Parse UAC __all__ from unified_api_contracts/__init__.py
2. AST-scan scoped source directories (core schemas + normalised contracts)
3. Collect public class definitions (name doesn't start with _)
4. Report classes defined in source but absent from __all__
5. Exit 1 if any non-exempt missing classes found

Scope: scans only core directories where classes ARE expected to be promoted to __all__:
  - unified_api_contracts/schemas/
  - unified_api_contracts/unified_normalised_contracts/
  - unified_api_contracts/trading_schemas.py

Intentionally NOT scanned (vendor-specific, narrow use):
  - unified_api_contracts_external/  — 40+ venue subdirs; classes here are deliberately
    NOT promoted to top-level __all__ unless explicitly curated

Usage:
    python scripts/check_uac_completeness.py
    python scripts/check_uac_completeness.py --missing-only   # print only missing class names
    python scripts/check_uac_completeness.py --workspace /path/to/workspace

Exit code: 0 if all non-exempt public UAC core classes are in __all__, 1 otherwise.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
UAC_ROOT = Path(__file__).resolve().parent.parent

# Directories to skip during AST scanning.
EXCLUDE_DIRS = frozenset(
    {
        ".venv",
        ".venv-workspace",
        "venv",
        "build",
        "dist",
        "node_modules",
        ".git",
        ".ruff_cache",
        ".pytest_cache",
        "__pycache__",
        "tests",
    }
)

# Directories within unified_api_contracts/ to scan (relative to package root).
# unified_api_contracts_external/ is deliberately excluded — vendor-specific schemas
# are not expected to be promoted to top-level __all__ unless curated.
SCAN_SUBDIRS: list[str] = [
    "schemas",
    "unified_normalised_contracts",
]

# Individual files to scan at the package root level.
SCAN_FILES: list[str] = [
    "trading_schemas.py",
    "canonical_mappings.py",
]

# Classes intentionally NOT in top-level __all__.
# Categories:
#   internal-base: abstract/private base class, not part of public surface
#   normalizer-impl: internal normalizer implementation class (not a schema)
#   narrow-util: narrow utility class used only internally
EXEMPT_MISSING: frozenset[str] = frozenset(
    [
        # internal-base: private base classes used by the schema hierarchy
        "_CanonicalBase",
        "_ExternalBase",
        "_NormalisedBase",
        # normalizer-impl: NormalizerBase and concrete normalizer classes live in
        # unified_normalised_contracts/normalize/ — these are implementation, not schemas
        "NormalizerBase",
        "BinanceFuturesNormalizer",
        "BinanceSpotNormalizer",
        "BybitFuturesNormalizer",
        "BybitSpotNormalizer",
        "CoinbaseNormalizer",
        "DeribitNormalizer",
        "HyperliquidNormalizer",
        "IBKRNormalizer",
        "OKXFuturesNormalizer",
        "OKXSpotNormalizer",
        "BetfairNormalizer",
        "PolymarketNormalizer",
        # narrow-util: version sentinel types not exported at surface level
        "SchemaVersion",
    ]
)


def get_uac_all() -> set[str]:
    """Return the set of names exported in UAC __all__."""
    init_path = UAC_ROOT / "unified_api_contracts" / "__init__.py"
    src = init_path.read_text()
    all_match = re.search(r"__all__\s*=\s*\[(.*?)\]", src, re.DOTALL)
    if not all_match:
        raise RuntimeError("Could not parse __all__ from UAC __init__.py")
    names = re.findall(r'"(\w+)"', all_match.group(1))
    return set(names)


def _is_public_class(name: str) -> bool:
    """Return True if the class name represents a public symbol (no leading underscore)."""
    return not name.startswith("_")


def collect_defined_classes(pkg_root: Path) -> dict[str, str]:
    """AST-scan scoped UAC source directories and return {class_name: relative_file_path}.

    Skips __init__.py files — they re-export, not define.
    Only scans SCAN_SUBDIRS and SCAN_FILES (not unified_api_contracts_external/).
    """
    defined: dict[str, str] = {}

    def _scan_file(py_file: Path) -> None:
        if py_file.name == "__init__.py":
            return
        if any(part in EXCLUDE_DIRS for part in py_file.parts):
            return
        try:
            tree = ast.parse(py_file.read_text(), filename=str(py_file))
        except SyntaxError:
            return
        rel = str(py_file.relative_to(UAC_ROOT))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and _is_public_class(node.name) and node.name not in defined:
                defined[node.name] = rel

    # Scan subdirectories
    for subdir_name in SCAN_SUBDIRS:
        subdir = pkg_root / subdir_name
        if subdir.exists():
            for py_file in subdir.rglob("*.py"):
                _scan_file(py_file)

    # Scan individual root-level files
    for filename in SCAN_FILES:
        py_file = pkg_root / filename
        if py_file.exists():
            _scan_file(py_file)

    return defined


def main() -> int:
    global UAC_ROOT
    parser = argparse.ArgumentParser(description="Check UAC public class completeness in __all__")
    parser.add_argument("--missing-only", action="store_true", help="Print only missing class names (one per line)")
    parser.add_argument("--workspace", default=str(WORKSPACE), help="Workspace root path")
    args = parser.parse_args()

    UAC_ROOT = Path(args.workspace) / "unified-api-contracts"

    print("Loading UAC __all__...", file=sys.stderr)
    exported = get_uac_all()
    print(f"Found {len(exported)} exported names in __all__.", file=sys.stderr)

    print("Scanning UAC core source for public class definitions...", file=sys.stderr)
    pkg_root = UAC_ROOT / "unified_api_contracts"
    defined = collect_defined_classes(pkg_root)
    print(f"Found {len(defined)} public class definitions in scoped source.", file=sys.stderr)

    non_exempt_defined = {name: path for name, path in defined.items() if name not in EXEMPT_MISSING}
    missing = {name: path for name, path in non_exempt_defined.items() if name not in exported}
    exempt_missing = {name: path for name, path in defined.items() if name in EXEMPT_MISSING}

    if args.missing_only:
        for name in sorted(missing):
            print(name)
        return 1 if missing else 0

    print("\n=== UAC Completeness Report ===", file=sys.stderr)
    print(f"  Exported in __all__:   {len(exported)}", file=sys.stderr)
    print(f"  Defined in source:     {len(defined)}", file=sys.stderr)
    print(f"  Exempt (not required): {len(exempt_missing)}", file=sys.stderr)
    print(f"  Missing from __all__:  {len(missing)}", file=sys.stderr)

    if exempt_missing:
        print(
            f"\nExempt (internal base/normalizer, {len(exempt_missing)} classes):",
            file=sys.stderr,
        )
        for name in sorted(exempt_missing):
            print(f"  - {name}  [{exempt_missing[name]}]", file=sys.stderr)

    if missing:
        print(
            f"\nMISSING from __all__ ({len(missing)} classes — add or exempt):",
            file=sys.stderr,
        )
        for name in sorted(missing):
            print(f"  - {name}  [{missing[name]}]", file=sys.stderr)
        return 1

    print(
        "\nAll non-exempt public UAC core classes are exported in __all__.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

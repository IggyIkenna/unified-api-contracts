#!/usr/bin/env python3
"""Check schema organization: flag UAC schemas that should be in UIC (internal-only).

Schemas in unified_api_contracts/schemas/ must be used in at least one of:
  (a) normalize_utils/
  (b) external/
  (c) tests/

If not used in any of these, the schema is internal-only and should live in UIC.
Exception: files with # SCHEMA_UAC_REQUIRED at top are skipped.

Exit 0 if all OK, 1 if violations.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(
    __import__("os").environ.get("WORKSPACE_ROOT", "/Users/ikennaigboaka/Code/unified-trading-system-repos")
)
REPO_ROOT = WORKSPACE_ROOT / "unified-api-contracts"
SCHEMAS_DIR = REPO_ROOT / "unified_api_contracts" / "schemas"
NORMALIZE_UTILS_DIR = REPO_ROOT / "unified_api_contracts" / "normalize_utils"
EXTERNAL_DIR = REPO_ROOT / "unified_api_contracts" / "external"
TESTS_DIR = REPO_ROOT / "tests"

# Directories to search for schema usage (relative to REPO_ROOT)
SEARCH_DIRS = [
    NORMALIZE_UTILS_DIR,
    EXTERNAL_DIR,
    TESTS_DIR,
]


def has_schema_uac_required(filepath: Path) -> bool:
    """Check if file has # SCHEMA_UAC_REQUIRED in first 20 lines."""
    try:
        text = filepath.read_text(encoding="utf-8")
        for line in text.splitlines()[:20]:
            if "SCHEMA_UAC_REQUIRED" in line and "#" in line:
                return True
    except OSError:
        pass
    return False


def is_schema_class(node: ast.ClassDef) -> bool:
    """True if class is BaseModel, TypedDict, or @dataclass."""
    # BaseModel: class Foo(BaseModel)
    for base in node.bases:
        if isinstance(base, ast.Name):
            if base.id in ("BaseModel", "TypedDict"):
                return True
        if isinstance(base, ast.Attribute):
            if base.attr in ("BaseModel", "TypedDict"):
                return True
    # @dataclass
    for deco in node.decorator_list:
        if isinstance(deco, ast.Name) and deco.id == "dataclass":
            return True
        if isinstance(deco, ast.Call):
            if isinstance(deco.func, ast.Name) and deco.func.id == "dataclass":
                return True
    return False


def collect_schemas() -> list[tuple[Path, str]]:
    """Return [(filepath, class_name), ...] for all schema classes in schemas/."""
    results: list[tuple[Path, str]] = []
    for pyfile in sorted(SCHEMAS_DIR.glob("*.py")):
        if pyfile.name == "__init__.py":
            continue
        try:
            tree = ast.parse(pyfile.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and is_schema_class(node):
                results.append((pyfile, node.name))
    return results


def grep_usage(class_name: str, search_dirs: list[Path]) -> bool:
    """Return True if class_name appears in any of search_dirs (excluding schemas/ and __pycache__)."""
    # Search for class name as identifier: import, type hint, instantiation, etc.
    pattern = rf"\b{re.escape(class_name)}\b"
    for d in search_dirs:
        if not d.exists():
            continue
        try:
            r = subprocess.run(
                ["rg", "-l", pattern, str(d), "--type", "py", "-g", "!__pycache__"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if r.returncode == 0 and r.stdout.strip():
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return False


def main() -> int:
    schemas = collect_schemas()
    violations: list[str] = []
    exempt_files = {p for p in SCHEMAS_DIR.glob("*.py") if has_schema_uac_required(p)}

    for filepath, class_name in schemas:
        if filepath in exempt_files:
            continue
        if grep_usage(class_name, SEARCH_DIRS):
            continue
        rel = filepath.relative_to(REPO_ROOT)
        violations.append(f"{rel}:{class_name}")

    if violations:
        print("Schemas not used in normalization, external mapping, or UAC tests (should be in UIC):")
        for v in sorted(violations):
            print(f"  {v}")
        return 1
    print("All schemas OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

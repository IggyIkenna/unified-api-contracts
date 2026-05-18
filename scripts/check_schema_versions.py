"""Check that schema_version field defaults match their module-level version constants.

Scans UAC canonical/domain.py and execution.py for:
  - CANONICAL_*_VERSION = "x.y.z" constants
  - Pydantic class fields: schema_version: str = CANONICAL_*_VERSION

Verifies that each field default references the declared constant (not a hard-coded
string that could drift after a future version bump).

Exits with the number of mismatches found (0 = pass).

Usage:
  python3 scripts/check_schema_versions.py           # prints report, exits with count
  python3 scripts/check_schema_versions.py --quiet   # exits with count only
"""

from __future__ import annotations

import ast
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_NORMALISED = _REPO_ROOT / "unified_api_contracts" / "canonical"

def _get_files() -> list[Path]:
    """Collect all canonical schema files that may contain CANONICAL_*_VERSION constants."""
    files: list[Path] = []
    domain_dir = _NORMALISED / "domain"
    if domain_dir.is_dir():
        files.extend(f for f in sorted(domain_dir.glob("*.py")) if not f.name.startswith("_"))
    execution = _NORMALISED / "execution.py"
    if execution.exists():
        files.append(execution)
    return files


_FILES = _get_files()

_QUIET = "--quiet" in sys.argv


def _collect_constants(tree: ast.Module) -> dict[str, str]:
    """Return {constant_name: value} for all CANONICAL_*_VERSION = "..." assignments."""
    constants: dict[str, str] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id.startswith("CANONICAL_")
            and node.targets[0].id.endswith("_VERSION")
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            constants[node.targets[0].id] = node.value.value
    return constants


def _collect_schema_version_defaults(tree: ast.Module) -> dict[str, str]:
    """Return {ClassName: default_value_or_name} for every `schema_version` field default.

    For `schema_version: str = "1.0.0"` → {"ClassName": "1.0.0"}  (hard-coded — bad)
    For `schema_version: str = CANONICAL_BET_ORDER_VERSION` → {"ClassName": "CANONICAL_BET_ORDER_VERSION"}
    """
    defaults: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, ast.AnnAssign):
                continue
            if not (isinstance(item.target, ast.Name) and item.target.id == "schema_version"):
                continue
            if item.value is None:
                continue
            if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                defaults[node.name] = item.value.value  # hard-coded string
            elif isinstance(item.value, ast.Name):
                defaults[node.name] = item.value.id  # references a constant
    return defaults


def check_file(path: Path, all_constants: dict[str, str]) -> int:
    """Return the number of mismatches found in a single file."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    constants = _collect_constants(tree)
    defaults = _collect_schema_version_defaults(tree)
    mismatches = 0
    for class_name, default in defaults.items():
        if default in all_constants:
            # Good: references a constant name
            pass
        elif default in constants:
            # Good: references a constant defined in the same file
            pass
        else:
            # Bad: hard-coded string or reference to unknown constant
            if not _QUIET:
                logger.info(
                    f"MISMATCH  {path.name}:{class_name} — schema_version default "
                    f"'{default}' does not reference a CANONICAL_*_VERSION constant"
                )
            mismatches += 1
    return mismatches


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    # Collect all constants from all scanned files first (cross-file reference support)
    all_constants: dict[str, str] = {}
    trees: dict[Path, ast.Module] = {}
    for p in _FILES:
        if not p.exists():
            if not _QUIET:
                logger.info(f"SKIP  {p} (not found)")
            continue
        source = p.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(p))
        trees[p] = tree
        all_constants.update(_collect_constants(tree))

    total_mismatches = 0
    for p, tree in trees.items():
        defaults = _collect_schema_version_defaults(tree)
        for class_name, default in defaults.items():
            if default in all_constants:
                if not _QUIET:
                    logger.info(f"OK        {p.name}:{class_name} → {default} = {all_constants[default]!r}")
            else:
                if not _QUIET:
                    logger.info(
                        f"MISMATCH  {p.name}:{class_name} — schema_version default "
                        f"'{default}' does not reference a CANONICAL_*_VERSION constant"
                    )
                total_mismatches += 1

    if not _QUIET:
        status = "PASS" if total_mismatches == 0 else "FAIL"
        logger.info(f"\n{status}: {total_mismatches} mismatch(es) found")
    else:
        logger.info("%s", total_mismatches)
    return total_mismatches


if __name__ == "__main__":
    sys.exit(main())

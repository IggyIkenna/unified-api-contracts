"""One-shot script: add __api_version__ = "..." to every external schema file.

Reads provider_api_versions.yaml, then for each provider inserts the constant
immediately after the module docstring (or at line 1 if there is no docstring).

Safe to re-run: skips any file that already contains __api_version__.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = REPO_ROOT / "unified_api_contracts" / "provider_api_versions.yaml"
EXTERNAL_DIR = REPO_ROOT / "unified_api_contracts" / "unified_api_contracts_external"

# Files to skip (not external API schema files)
SKIP_DIRS = {"__pycache__", "cloud_sdks", "examples", "mocks"}
SKIP_FILES = {"__init__.py"}


def _insertion_point(lines: list[str]) -> int:
    """Return the line index AFTER the module-level docstring (0-based).

    If no docstring, returns 0 (insert at very top).
    """
    if not lines:
        return 0

    # Detect if the first non-empty line starts a docstring
    first_content = 0
    while first_content < len(lines) and not lines[first_content].strip():
        first_content += 1

    if first_content >= len(lines):
        return 0

    stripped = lines[first_content].strip()
    if not (stripped.startswith('"""') or stripped.startswith("'''")):
        return 0  # no docstring; insert at top

    quote = stripped[:3]
    # Check if the docstring ends on the same line
    rest = stripped[3:]
    if rest.endswith(quote) and len(rest) >= 3:
        # Single-line docstring
        return first_content + 1

    # Multi-line: scan forward for the closing triple-quote
    for i in range(first_content + 1, len(lines)):
        if quote in lines[i]:
            return i + 1

    # Malformed docstring — insert after first line
    return first_content + 1


def _add_version(file_path: Path, api_version: str) -> bool:
    """Insert __api_version__ into *file_path*. Returns True if file was modified."""
    text = file_path.read_text(encoding="utf-8")
    if "__api_version__" in text:
        return False  # already present

    lines = text.splitlines(keepends=True)
    idx = _insertion_point(lines)

    constant_line = f'\n__api_version__ = "{api_version}"  # matches provider_api_versions.yaml\n'
    lines.insert(idx, constant_line)
    file_path.write_text("".join(lines), encoding="utf-8")
    return True


def main() -> int:
    with YAML_PATH.open() as fh:
        manifest = yaml.safe_load(fh)

    providers = manifest.get("providers", {})
    modified = 0
    skipped = 0
    missing = []

    for provider_name, info in providers.items():
        api_version: str = info.get("api_version", "v1")
        provider_dir = EXTERNAL_DIR / provider_name

        if not provider_dir.is_dir():
            missing.append(provider_name)
            continue

        py_files = [
            f
            for f in sorted(provider_dir.iterdir())
            if f.suffix == ".py" and f.name not in SKIP_FILES and not f.name.startswith("__")
        ]

        if not py_files:
            print(f"  WARN: no schema .py files in {provider_name}/")
            continue

        for py_file in py_files:
            changed = _add_version(py_file, api_version)
            if changed:
                modified += 1
                print(f"  + {provider_name}/{py_file.name}  __api_version__ = {api_version!r}")
            else:
                skipped += 1

    print(f"\nDone: {modified} files modified, {skipped} already had __api_version__.")
    if missing:
        print(f"WARN: {len(missing)} provider(s) in YAML but no directory: {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

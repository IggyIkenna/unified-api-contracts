"""Boundary test: UAC must not import from UIC (would be a circular dependency).

Import direction rule:
    UIC → UAC canonical layer is PERMITTED (UIC re-exports UAC canonical types).
    UAC → UIC is FORBIDDEN (would create a circular dependency).

This test walks all UAC Python source files and asserts that none of them
import from ``unified_api_contracts.internal``.

Owned here (UIC) because it protects UIC's import boundary.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# UAC repo lives as a sibling of UIC in the workspace
# parents[3] = unified-trading-system-repos (workspace root)
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
UAC_SOURCE_ROOT = _WORKSPACE_ROOT / "unified-api-contracts" / "unified_api_contracts"
FORBIDDEN_IMPORT = "unified_api_contracts.internal"


def _all_uac_python_files() -> list[Path]:
    if not UAC_SOURCE_ROOT.exists():
        return []
    return [p for p in UAC_SOURCE_ROOT.rglob("*.py") if "__pycache__" not in p.parts and ".venv" not in str(p)]


@pytest.mark.parametrize(
    "py_file",
    _all_uac_python_files(),
    ids=lambda p: str(p.relative_to(UAC_SOURCE_ROOT)),
)
def test_uac_does_not_import_uic(py_file: Path) -> None:
    """Each UAC source file must not import from unified_api_contracts.internal."""
    source = py_file.read_text()
    assert FORBIDDEN_IMPORT not in source, (
        f"{py_file.relative_to(UAC_SOURCE_ROOT)} imports from unified_api_contracts.internal.\n"
        "UAC → UIC imports are FORBIDDEN to prevent circular dependencies.\n"
        "Move any shared types to UAC canonical/ instead."
    )

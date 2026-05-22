"""Boundary test: UAC must not import from UTL/UIC (would be circular dependencies).

Import direction rule:
    UTL (unified_trading_library) → UAC is PERMITTED (UTL re-exports UAC canonical types).
    UAC → UTL is FORBIDDEN (would create a circular dependency).

This test walks all UAC Python source files and asserts that none of them
import from ``unified_trading_library``.

Note: ``unified_api_contracts.internal`` is UAC's own internal subpackage (merged from
the former unified-internal-contracts repo). UAC source files importing from their own
``internal/`` subpackage is the intended facade pattern — NOT a circular dependency.
The original FORBIDDEN_IMPORT was mistakenly set to ``unified_api_contracts.internal``
(UAC's own package) instead of ``unified_trading_library`` (the actual up-stream dep
that would form a cycle). Fixed 2026-05-22.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import unified_api_contracts

UAC_SOURCE_ROOT = Path(unified_api_contracts.__file__).resolve().parent
FORBIDDEN_PACKAGES = (
    "unified_trading_library",
    "unified_cloud_interface",
)
# Match actual import statements only, not docstring/comment references.
_IMPORT_RE = re.compile(
    r"^(?:from|import)\s+(" + "|".join(re.escape(p) for p in FORBIDDEN_PACKAGES) + r")[\s.,]",
    re.MULTILINE,
)


def _all_uac_python_files() -> list[Path]:
    return [p for p in UAC_SOURCE_ROOT.rglob("*.py") if "__pycache__" not in p.parts and ".venv" not in p.parts]


@pytest.mark.parametrize("py_file", _all_uac_python_files(), ids=lambda p: str(p.relative_to(UAC_SOURCE_ROOT)))
def test_uac_does_not_import_utl(py_file: Path) -> None:
    """UAC source files must not import from UTL or UIC (circular dependency prevention)."""
    source = py_file.read_text()
    match = _IMPORT_RE.search(source)
    assert match is None, (
        f"{py_file.relative_to(UAC_SOURCE_ROOT)} imports from {match.group(1) if match else '?'}.\n"
        "UAC → UTL/UIC imports are FORBIDDEN: those packages depend on UAC, so importing\n"
        "them from UAC would create a circular dependency. Move shared types to UAC instead."
    )

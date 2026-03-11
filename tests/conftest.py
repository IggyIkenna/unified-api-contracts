"""Pytest configuration for unified-api-contracts.

Provides:
- Optional mock for unified_config_interface.get_secret when UCI is present (e.g. workspace)
- Hypothesis profiles: default (fast, few examples), ci (more examples for CI)
- sys.path setup for scripts/ directory (needed by test_schema_version_matrix.py)
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from hypothesis import settings

# Ensure scripts/ and repo root are importable — needed by test_schema_version_matrix.py
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
for _p in (str(_SCRIPTS_DIR), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Fast local runs; CI can set HYPOTHESIS_PROFILE=ci for more examples
settings.register_profile("default", max_examples=25, deadline=None)
settings.register_profile("ci", max_examples=200, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "default"))


@pytest.fixture(autouse=True)
def mock_secret_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock | None:
    """Prevent real secret access when UCI is on the path (e.g. workspace). No-op otherwise."""
    import importlib.util

    if importlib.util.find_spec("unified_config_interface") is None:
        return None
    mock = MagicMock(return_value="fake-secret-value")
    monkeypatch.setattr("unified_config_interface.get_secret", mock, raising=False)
    return mock

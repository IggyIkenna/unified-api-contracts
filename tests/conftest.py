"""Pytest configuration for unified-api-contracts.

Provides:
- Optional mock for unified_trading_library.config_interface.get_secret when UCI is present (e.g. workspace)
- Hypothesis profiles: default (fast, few examples), ci (more examples for CI)
- sys.path setup for scripts/ directory (needed by test_schema_version_matrix.py)
- Network blocking via shared plugin (unified_api_contracts.testing.network_block_plugin)
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import aiohttp.streams
import pytest
from hypothesis import settings

# vcrpy 8.1.1 references aiohttp.streams.AsyncStreamReaderMixin which was removed
# in aiohttp>=3.14.0 (CVE-2026-34993 security bump). Patch it back as a no-op mixin
# so VCR stubs can define MockStream without AttributeError. Must run at import time,
# before any vcr.stubs.aiohttp_stubs import.
if not hasattr(aiohttp.streams, "AsyncStreamReaderMixin"):

    class _AsyncStreamReaderMixin:
        pass

    aiohttp.streams.AsyncStreamReaderMixin = _AsyncStreamReaderMixin  # type: ignore[attr-defined]

# Register the shared network-block plugin (--block-network + allow_network marker).
# This replaces the hand-rolled version that was previously duplicated here.
pytest_plugins = ["unified_api_contracts.testing.network_block_plugin"]

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

    try:
        spec = importlib.util.find_spec("unified_trading_library.config_interface")
    except ModuleNotFoundError:
        return None
    if spec is None:
        return None
    mock = MagicMock(return_value="fake-secret-value")
    monkeypatch.setattr("unified_trading_library.config_interface.get_secret", mock, raising=False)
    return mock

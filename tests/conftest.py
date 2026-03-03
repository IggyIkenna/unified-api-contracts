"""Pytest configuration for unified-api-contracts.

Provides:
- Optional mock for unified_config_interface.get_secret when UCI is present (e.g. workspace)
- Hypothesis profiles: default (fast, few examples), ci (more examples for CI)
"""

import os
from unittest.mock import MagicMock

import pytest
from hypothesis import settings

# Fast local runs; CI can set HYPOTHESIS_PROFILE=ci for more examples
settings.register_profile("default", max_examples=25, deadline=None)
settings.register_profile("ci", max_examples=200, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "default"))


@pytest.fixture(autouse=True)
def mock_secret_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock | None:
    """Prevent real secret access when UCI is on the path (e.g. workspace). No-op otherwise."""
    try:
        import unified_config_interface  # noqa: F401
    except ImportError:
        return None
    mock = MagicMock(return_value="fake-secret-value")
    monkeypatch.setattr("unified_config_interface.get_secret", mock, raising=False)
    return mock

"""Pytest configuration for unified-api-contracts.

Provides:
- Optional mock for unified_config_interface.get_secret when UCI is present (e.g. workspace)
- Hypothesis profiles: default (fast, few examples), ci (more examples for CI)
- sys.path setup for scripts/ directory (needed by test_schema_version_matrix.py)
- --block-network flag to block socket connections in CI (credential-free enforcement)
"""

import os
import socket
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


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command line options."""
    parser.addoption(
        "--block-network",
        action="store_true",
        default=False,
        help="Block all socket connections to enforce credential-free CI runs.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "allow_network: mark test as allowed to make network calls (opt-out of --block-network)",
    )


_original_connect = socket.socket.connect


def _blocked_connect(self: socket.socket, address: object) -> None:
    """Raise immediately unless the test has opted out via allow_network."""
    raise OSError(f"Network access blocked by --block-network: attempted connection to {address}")


@pytest.fixture(autouse=True)
def _enforce_block_network(request: pytest.FixtureRequest) -> object:
    """Block socket.connect for all tests when --block-network is active."""
    if not request.config.getoption("--block-network", default=False):
        yield
        return
    if request.node.get_closest_marker("allow_network"):
        yield
        return
    socket.socket.connect = _blocked_connect  # type: ignore[method-assign]
    yield
    socket.socket.connect = _original_connect  # type: ignore[method-assign]


@pytest.fixture(autouse=True)
def mock_secret_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock | None:
    """Prevent real secret access when UCI is on the path (e.g. workspace). No-op otherwise."""
    import importlib.util

    if importlib.util.find_spec("unified_config_interface") is None:
        return None
    mock = MagicMock(return_value="fake-secret-value")
    monkeypatch.setattr("unified_config_interface.get_secret", mock, raising=False)
    return mock

"""Pytest configuration for unified-internal-contracts.

Tier 0 library: no workspace dependencies to mock.
Provides standard session-scoped fixtures for test isolation.
"""

import os

import pytest

pytest_plugins = ["unified_api_contracts.testing.network_block_plugin"]


@pytest.fixture(scope="session", autouse=True)
def _set_test_env() -> object:
    """Set environment variables for test isolation."""
    os.environ.setdefault("CLOUD_MOCK_MODE", "true")
    os.environ.setdefault("GCP_PROJECT_ID", "test-project")
    yield None

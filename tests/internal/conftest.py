"""Pytest configuration for tests/internal/.

Tier 0 library: no workspace dependencies to mock.
Provides standard session-scoped fixtures for test isolation.

NOTE: pytest_plugins is declared in the root tests/conftest.py only
(pytest forbids it in non-root conftest files).
"""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def _set_test_env() -> object:
    """Set environment variables for test isolation."""
    os.environ.setdefault("CLOUD_MOCK_MODE", "true")
    os.environ.setdefault("GCP_PROJECT_ID", "test-project")
    yield None

"""Unit tests for scripts/generate_schema_version_matrix.py.

Tests the core logic with mock YAML data and mock schema modules.
Does NOT write real files or import live provider modules.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"

# Ensure the scripts directory is importable
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from generate_schema_version_matrix import (  # noqa: E402
    ProviderHealth,
    _compute_status,
    _import_schema_version,
    load_providers,
    write_matrix_md,
    write_svg,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_module(api_version: str) -> ModuleType:
    """Return a fake module with __api_version__ set."""
    mod = MagicMock(spec=ModuleType)
    mod.__api_version__ = api_version
    return mod


def _make_provider(
    name: str = "test_provider",
    yaml_version: str = "v1",
    schema_version: str = "v1",
    last_verified: str = "2026-03-09",
    yaml_status: str = "green",
    computed_status: str = "green",
    notes: str = "",
) -> ProviderHealth:
    return ProviderHealth(
        name=name,
        yaml_version=yaml_version,
        schema_version=schema_version,
        last_verified=last_verified,
        yaml_status=yaml_status,
        computed_status=computed_status,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# _compute_status tests
# ---------------------------------------------------------------------------


def test_green_status_when_versions_match() -> None:
    """Green when yaml_version == schema_version and verified recently."""
    result = _compute_status(
        yaml_version="v3",
        schema_version="v3",
        last_verified="2026-03-09",
        yaml_status="green",
    )
    assert result == "green"


def test_yellow_status_when_old_last_verified() -> None:
    """Yellow when last_verified is more than 90 days ago, even if versions match."""
    result = _compute_status(
        yaml_version="v2",
        schema_version="v2",
        last_verified="2025-01-01",  # well over 90 days before 2026-03-09
        yaml_status="green",
    )
    assert result == "yellow"


def test_red_status_when_version_mismatch() -> None:
    """Red when yaml_version differs from schema __api_version__."""
    result = _compute_status(
        yaml_version="v3",
        schema_version="v2",
        last_verified="2026-03-09",
        yaml_status="green",
    )
    assert result == "red"


def test_red_status_when_yaml_status_is_red() -> None:
    """Red when YAML status is explicitly red, even if versions match."""
    result = _compute_status(
        yaml_version="v1",
        schema_version="v1",
        last_verified="2026-03-09",
        yaml_status="red",
    )
    assert result == "red"


def test_na_schema_version_does_not_trigger_red() -> None:
    """N/A schema_version (import failed) should not count as mismatch."""
    result = _compute_status(
        yaml_version="v3",
        schema_version="N/A",
        last_verified="2026-03-09",
        yaml_status="green",
    )
    assert result == "green"


def test_yellow_preserved_when_yaml_status_yellow_and_recent() -> None:
    """Yellow in YAML with recent verification keeps yellow (not promoted to green)."""
    result = _compute_status(
        yaml_version="v1",
        schema_version="v1",
        last_verified="2026-03-09",
        yaml_status="yellow",
    )
    assert result == "yellow"


# ---------------------------------------------------------------------------
# _import_schema_version tests
# ---------------------------------------------------------------------------


def test_import_schema_version_returns_version_from_module() -> None:
    """Returns __api_version__ from the first importable module path."""
    mock_mod = _make_mock_module("v5")
    with patch("importlib.import_module", return_value=mock_mod):
        result = _import_schema_version("bybit")
    assert result == "v5"


def test_import_schema_version_returns_na_on_import_error() -> None:
    """Returns 'N/A' when all import paths fail."""
    with patch("importlib.import_module", side_effect=ImportError("not found")):
        result = _import_schema_version("nonexistent_provider")
    assert result == "N/A"


def test_import_schema_version_returns_na_for_skip_providers() -> None:
    """Returns 'N/A' for providers in _SKIP_MODULE_IMPORT without attempting import."""
    from generate_schema_version_matrix import _SKIP_MODULE_IMPORT

    skip_provider = next(iter(_SKIP_MODULE_IMPORT))
    with patch("importlib.import_module") as mock_import:
        result = _import_schema_version(skip_provider)
    assert result == "N/A"
    mock_import.assert_not_called()


# ---------------------------------------------------------------------------
# load_providers tests (using mock YAML data)
# ---------------------------------------------------------------------------

_MOCK_YAML_DATA = {
    "providers": {
        "binance": {
            "api_version": "v3",
            "spec_url": "https://binance-docs.github.io/",
            "last_verified": "2026-03-09",
            "status": "green",
        },
        "stale_provider": {
            "api_version": "v2",
            "spec_url": "",
            "last_verified": "2024-01-01",
            "status": "green",
        },
        "broken_provider": {
            "api_version": "v5",
            "spec_url": "",
            "last_verified": "2026-03-09",
            "status": "green",
        },
    }
}


def test_load_providers_green_when_versions_match() -> None:
    """load_providers marks green when YAML and schema versions match and recent."""
    mock_binance = _make_mock_module("v3")
    mock_stale = _make_mock_module("v2")
    mock_broken = _make_mock_module("v3")  # mismatches yaml "v5"

    def fake_import(path: str) -> ModuleType:
        if "binance" in path:
            return mock_binance
        if "stale_provider" in path:
            return mock_stale
        if "broken_provider" in path:
            return mock_broken
        raise ImportError(f"no module {path}")

    with (
        patch("generate_schema_version_matrix._read_yaml", return_value=_MOCK_YAML_DATA),
        patch("importlib.import_module", side_effect=fake_import),
    ):
        providers = load_providers()

    by_name = {p.name: p for p in providers}
    assert by_name["binance"].computed_status == "green"


def test_load_providers_yellow_when_stale() -> None:
    """load_providers marks yellow when last_verified > 90 days ago."""
    mock_stale = _make_mock_module("v2")

    def fake_import(path: str) -> ModuleType:
        if "stale_provider" in path:
            return mock_stale
        raise ImportError(f"no module {path}")

    with (
        patch("generate_schema_version_matrix._read_yaml", return_value=_MOCK_YAML_DATA),
        patch("importlib.import_module", side_effect=fake_import),
    ):
        providers = load_providers()

    by_name = {p.name: p for p in providers}
    assert by_name["stale_provider"].computed_status == "yellow"


def test_load_providers_red_when_version_mismatch() -> None:
    """load_providers marks red when schema __api_version__ != YAML api_version."""
    mock_broken = _make_mock_module("v3")  # YAML says v5

    def fake_import(path: str) -> ModuleType:
        if "broken_provider" in path:
            return mock_broken
        raise ImportError(f"no module {path}")

    with (
        patch("generate_schema_version_matrix._read_yaml", return_value=_MOCK_YAML_DATA),
        patch("importlib.import_module", side_effect=fake_import),
    ):
        providers = load_providers()

    by_name = {p.name: p for p in providers}
    assert by_name["broken_provider"].computed_status == "red"


# ---------------------------------------------------------------------------
# --count-red flag
# ---------------------------------------------------------------------------


def test_count_red_flag_output() -> None:
    """--count-red prints the integer count of red providers and exits 0."""
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPTS_DIR / "generate_schema_version_matrix.py"),
            "--count-red",
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    # Output should be a non-negative integer
    output = result.stdout.strip()
    assert output.isdigit(), f"Expected integer output, got: {output!r}"
    assert int(output) >= 0


# ---------------------------------------------------------------------------
# write_matrix_md / write_svg (smoke — use tmp_path)
# ---------------------------------------------------------------------------


def test_write_matrix_md_creates_file(tmp_path: Path) -> None:
    """write_matrix_md produces a valid markdown file."""
    import generate_schema_version_matrix as gm

    orig_md = gm._MATRIX_MD
    gm._MATRIX_MD = tmp_path / "SCHEMA_VERSION_MATRIX.md"

    try:
        providers = [
            _make_provider("binance", "v3", "v3", "2026-03-09", "green", "green"),
            _make_provider("bybit", "v5", "v5", "2026-01-01", "yellow", "yellow"),
            _make_provider("broken", "v3", "v2", "2026-03-09", "green", "red"),
        ]
        write_matrix_md(providers)
        content = gm._MATRIX_MD.read_text()
        assert "# Schema Version Matrix" in content
        assert "binance" in content
        assert "broken" in content
    finally:
        gm._MATRIX_MD = orig_md


def test_write_svg_creates_valid_svg(tmp_path: Path) -> None:
    """write_svg produces a file containing SVG markup."""
    import generate_schema_version_matrix as gm

    orig_svg = gm._SVG_PATH
    gm._SVG_PATH = tmp_path / "schema_health.svg"

    try:
        providers = [
            _make_provider("binance", "v3", "v3", "2026-03-09", "green", "green"),
            _make_provider("bybit", "v5", "v5", "2026-01-01", "yellow", "yellow"),
            _make_provider("broken", "v3", "v2", "2026-03-09", "green", "red"),
        ]
        write_svg(providers)
        content = gm._SVG_PATH.read_text()
        assert "<svg" in content
        assert "binance" in content
        assert "#f44336" in content  # red colour present
        assert "#4caf50" in content  # green colour present
    finally:
        gm._SVG_PATH = orig_svg

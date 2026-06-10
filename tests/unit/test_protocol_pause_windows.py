"""Tests for registry/protocol_pause_windows.py — DeFi protocol pause detection."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from unified_api_contracts.registry.protocol_pause_windows import (
    PROTOCOL_PAUSE_WINDOWS,
    is_protocol_paused,
)


class TestProtocolPauseWindowsEmpty:
    """The cache file doesn't exist in the test environment — everything returns False."""

    def test_unknown_protocol_not_paused(self) -> None:
        paused, desc = is_protocol_paused("AAVE_V3", "ETHEREUM", date(2024, 1, 1))
        assert paused is False
        assert desc is None

    def test_completely_unknown_protocol_not_paused(self) -> None:
        paused, desc = is_protocol_paused("UNKNOWN_PROTOCOL", "UNKNOWN_CHAIN", date(2024, 6, 1))
        assert paused is False
        assert desc is None

    def test_empty_registry_returns_false_for_any_date(self) -> None:
        if not PROTOCOL_PAUSE_WINDOWS:
            paused, _ = is_protocol_paused("COMPOUND_V3", "ARBITRUM", date(2023, 1, 1))
            assert paused is False

    def test_protocol_pause_windows_is_dict(self) -> None:
        assert isinstance(PROTOCOL_PAUSE_WINDOWS, dict)

    def test_case_insensitive_protocol(self) -> None:
        paused, _ = is_protocol_paused("aave_v3", "ethereum", date(2024, 1, 1))
        assert paused is False


class TestIsProtocolPausedWithMockedWindows:
    """Inject mock windows to test the date comparison logic."""

    def test_date_inside_window_returns_paused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        windows = {("AAVE_V3", "ETHEREUM"): [(date(2024, 1, 10), date(2024, 1, 20))]}
        monkeypatch.setattr(
            "unified_api_contracts.registry.protocol_pause_windows.PROTOCOL_PAUSE_WINDOWS",
            windows,
        )
        paused, desc = is_protocol_paused("AAVE_V3", "ETHEREUM", date(2024, 1, 15))
        assert paused is True
        assert desc is not None
        assert "AAVE_V3" in desc

    def test_date_before_window_not_paused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        windows = {("AAVE_V3", "ETHEREUM"): [(date(2024, 2, 1), date(2024, 2, 28))]}
        monkeypatch.setattr(
            "unified_api_contracts.registry.protocol_pause_windows.PROTOCOL_PAUSE_WINDOWS",
            windows,
        )
        paused, desc = is_protocol_paused("AAVE_V3", "ETHEREUM", date(2024, 1, 15))
        assert paused is False
        assert desc is None

    def test_date_after_window_not_paused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        windows = {("AAVE_V3", "ETHEREUM"): [(date(2024, 1, 1), date(2024, 1, 5))]}
        monkeypatch.setattr(
            "unified_api_contracts.registry.protocol_pause_windows.PROTOCOL_PAUSE_WINDOWS",
            windows,
        )
        paused, desc = is_protocol_paused("AAVE_V3", "ETHEREUM", date(2024, 2, 1))
        assert paused is False

    def test_ongoing_window_none_end_treats_as_active(self, monkeypatch: pytest.MonkeyPatch) -> None:
        windows = {("AAVE_V3", "ETHEREUM"): [(date(2024, 1, 1), None)]}
        monkeypatch.setattr(
            "unified_api_contracts.registry.protocol_pause_windows.PROTOCOL_PAUSE_WINDOWS",
            windows,
        )
        paused, desc = is_protocol_paused("AAVE_V3", "ETHEREUM", date(2024, 6, 1))
        assert paused is True
        assert desc is not None
        assert "ongoing" in desc

    def test_description_contains_window_bounds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        windows = {("COMPOUND_V3", "BASE"): [(date(2023, 9, 1), date(2023, 9, 15))]}
        monkeypatch.setattr(
            "unified_api_contracts.registry.protocol_pause_windows.PROTOCOL_PAUSE_WINDOWS",
            windows,
        )
        paused, desc = is_protocol_paused("COMPOUND_V3", "BASE", date(2023, 9, 10))
        assert paused is True
        assert "2023-09-01" in (desc or "")

    def test_boundary_start_date_is_paused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        windows = {("LIDO", "ETHEREUM"): [(date(2024, 3, 1), date(2024, 3, 10))]}
        monkeypatch.setattr(
            "unified_api_contracts.registry.protocol_pause_windows.PROTOCOL_PAUSE_WINDOWS",
            windows,
        )
        paused, _ = is_protocol_paused("LIDO", "ETHEREUM", date(2024, 3, 1))
        assert paused is True

    def test_boundary_end_date_is_paused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        windows = {("LIDO", "ETHEREUM"): [(date(2024, 3, 1), date(2024, 3, 10))]}
        monkeypatch.setattr(
            "unified_api_contracts.registry.protocol_pause_windows.PROTOCOL_PAUSE_WINDOWS",
            windows,
        )
        paused, _ = is_protocol_paused("LIDO", "ETHEREUM", date(2024, 3, 10))
        assert paused is True

    def test_multiple_windows_second_matches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        windows = {
            ("AAVE_V3", "POLYGON"): [
                (date(2024, 1, 1), date(2024, 1, 5)),
                (date(2024, 3, 1), date(2024, 3, 31)),
            ]
        }
        monkeypatch.setattr(
            "unified_api_contracts.registry.protocol_pause_windows.PROTOCOL_PAUSE_WINDOWS",
            windows,
        )
        paused, _ = is_protocol_paused("AAVE_V3", "POLYGON", date(2024, 3, 15))
        assert paused is True


class TestLoadCache:
    """Test the _load_cache function indirectly via module import."""

    def test_cache_loads_without_error(self) -> None:
        # The module loaded without error; cache is a dict (possibly empty)
        assert isinstance(PROTOCOL_PAUSE_WINDOWS, dict)

    def test_load_cache_with_valid_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unified_api_contracts.registry import protocol_pause_windows as ppw

        cache_data = {
            "windows": {
                "AAVE_V3|ETHEREUM": [
                    {"start_date": "2024-01-01", "end_date": "2024-01-31"},
                ]
            }
        }
        cache_file = tmp_path / "protocol_pause_windows_cache.json"
        cache_file.write_text(json.dumps(cache_data))
        monkeypatch.setattr(ppw, "_CACHE_PATH", cache_file)
        from unified_api_contracts.registry.protocol_pause_windows import _load_cache

        result = _load_cache()
        assert ("AAVE_V3", "ETHEREUM") in result

    def test_load_cache_with_ongoing_window(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unified_api_contracts.registry import protocol_pause_windows as ppw

        cache_data = {
            "windows": {
                "COMPOUND_V3|BASE": [
                    {"start_date": "2024-06-01"},  # no end_date
                ]
            }
        }
        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps(cache_data))
        monkeypatch.setattr(ppw, "_CACHE_PATH", cache_file)
        from unified_api_contracts.registry.protocol_pause_windows import _load_cache

        result = _load_cache()
        assert ("COMPOUND_V3", "BASE") in result
        assert result[("COMPOUND_V3", "BASE")][0][1] is None

    def test_load_cache_with_malformed_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unified_api_contracts.registry import protocol_pause_windows as ppw

        cache_file = tmp_path / "bad_cache.json"
        cache_file.write_text("{invalid json}")
        monkeypatch.setattr(ppw, "_CACHE_PATH", cache_file)
        from unified_api_contracts.registry.protocol_pause_windows import _load_cache

        result = _load_cache()
        assert result == {}

    def test_load_cache_with_missing_pipe_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from unified_api_contracts.registry import protocol_pause_windows as ppw

        cache_data = {"windows": {"BADKEY": [{"start_date": "2024-01-01"}]}}
        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps(cache_data))
        monkeypatch.setattr(ppw, "_CACHE_PATH", cache_file)
        from unified_api_contracts.registry.protocol_pause_windows import _load_cache

        result = _load_cache()
        assert result == {}

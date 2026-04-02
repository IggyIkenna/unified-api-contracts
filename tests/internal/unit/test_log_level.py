"""Unit tests for LogLevel StrEnum in unified-internal-contracts."""

from unified_api_contracts.internal import LogLevel
from unified_api_contracts.internal.modes import LogLevel as ModesLogLevel


def test_log_level_values() -> None:
    """Each LogLevel member maps to its expected uppercase string."""
    assert LogLevel.DEBUG == "DEBUG"
    assert LogLevel.INFO == "INFO"
    assert LogLevel.WARNING == "WARNING"
    assert LogLevel.ERROR == "ERROR"
    assert LogLevel.CRITICAL == "CRITICAL"


def test_log_level_is_str() -> None:
    """LogLevel members are valid strings (StrEnum)."""
    for member in LogLevel:
        assert isinstance(member, str)
        assert member == member.value


def test_log_level_member_count() -> None:
    """LogLevel has exactly 5 members."""
    assert len(LogLevel) == 5


def test_log_level_reexported_from_package_root() -> None:
    """LogLevel imported from package root is the same class as from modes."""
    assert LogLevel is ModesLogLevel


def test_log_level_string_comparison() -> None:
    """LogLevel members compare equal to plain strings."""
    assert LogLevel.DEBUG == "DEBUG"
    assert LogLevel.INFO == "INFO"
    assert LogLevel.WARNING != "ERROR"

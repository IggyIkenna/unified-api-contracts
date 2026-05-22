"""Unit tests for EmptyConfirmedReason closed-set taxonomy (writegate Phase 2.E).

data_status_comprehensive_test_coverage_2026_05_07.md B.1.

Invariants:
- EMPTY_CONFIRMED_REASONS is EXACTLY the set of all EmptyConfirmedReason member values.
- No reason string can be added to EMPTY_CONFIRMED_REASONS without also adding an enum member.
- All members are non-empty strings.
- All calendar/schedule-driven reasons carry the EXPECTED_ prefix; SOURCE_RETURNED_ZERO is the only non-prefixed member.
- LegacyBlankErrorReasonError carries a useful message referencing the closed set.
"""

from __future__ import annotations

import pytest

from unified_api_contracts import (
    EMPTY_CONFIRMED_REASONS,
    EXPECTED_EMPTY_REASON_PREFIX,
    EmptyConfirmedReason,
    LegacyBlankErrorReasonError,
)


def test_empty_confirmed_reasons_matches_enum_members() -> None:
    """EMPTY_CONFIRMED_REASONS is exactly the frozenset of all EmptyConfirmedReason values."""
    enum_values = frozenset(e.value for e in EmptyConfirmedReason)
    assert enum_values == EMPTY_CONFIRMED_REASONS, (
        f"EMPTY_CONFIRMED_REASONS ({len(EMPTY_CONFIRMED_REASONS)} entries) does not match "
        f"EmptyConfirmedReason ({len(enum_values)} members).\n"
        f"  Extra in EMPTY_CONFIRMED_REASONS (not in enum): {EMPTY_CONFIRMED_REASONS - enum_values}\n"
        f"  Missing from EMPTY_CONFIRMED_REASONS (in enum): {enum_values - EMPTY_CONFIRMED_REASONS}"
    )


def test_every_enum_member_is_a_nonempty_string() -> None:
    """All EmptyConfirmedReason members are non-empty string-valued (StrEnum contract)."""
    for member in EmptyConfirmedReason:
        assert isinstance(member.value, str), f"{member.name} value is not a str: {member.value!r}"
        assert member.value, f"{member.name} has an empty string value"


def test_expected_prefix_members_carry_expected_prefix() -> None:
    """All EXPECTED_* members start with EXPECTED_EMPTY_REASON_PREFIX.

    Non-prefixed members are a closed set:
    - SOURCE_RETURNED_ZERO: source returned zero rows (not a calendar skip)
    - NO_INPUT_AVAILABLE: upstream input had attempted_failed status
    - LEG_ABSENT_LEFT / LEG_ABSENT_RIGHT: cross-instrument paired calc leg absent
      (writegate_honest_coverage_endtoend_2026_05_06.md Phase 2.E.3)
    """
    allowed_non_prefixed = {"SOURCE_RETURNED_ZERO", "NO_INPUT_AVAILABLE", "LEG_ABSENT_LEFT", "LEG_ABSENT_RIGHT"}
    non_prefixed = {e.value for e in EmptyConfirmedReason if not e.value.startswith(EXPECTED_EMPTY_REASON_PREFIX)}
    unexpected_non_prefixed = non_prefixed - allowed_non_prefixed
    assert not unexpected_non_prefixed, (
        f"Non-EXPECTED_ reasons beyond the allowed set detected: {unexpected_non_prefixed}. "
        f"Calendar/schedule-driven reasons MUST start with '{EXPECTED_EMPTY_REASON_PREFIX}' so "
        f"downstream consumers can distinguish them from non-calendar empty reasons."
    )


@pytest.mark.parametrize("reason", list(EmptyConfirmedReason))
def test_every_enum_member_is_in_closed_set(reason: EmptyConfirmedReason) -> None:
    """Every EmptyConfirmedReason member value is present in EMPTY_CONFIRMED_REASONS."""
    assert reason.value in EMPTY_CONFIRMED_REASONS, (
        f"{reason.name} ({reason.value!r}) is in EmptyConfirmedReason but missing from "
        f"EMPTY_CONFIRMED_REASONS. Update the frozenset in honest_coverage.py."
    )


def test_ad_hoc_reasons_are_not_in_closed_set() -> None:
    """Common typos and ad-hoc strings are NOT in EMPTY_CONFIRMED_REASONS."""
    bad_reasons = [
        "",
        "holiday",
        "HOLIDAY",
        "weekend",
        "WEEKEND",
        "UNKNOWN_REASON_XYZ",
        "EXPECTED_",
        "source_returned_zero",
    ]
    for reason in bad_reasons:
        assert reason not in EMPTY_CONFIRMED_REASONS, (
            f"{reason!r} should NOT be in EMPTY_CONFIRMED_REASONS but was found."
        )


def test_legacy_blank_error_reason_error_message_references_closed_set() -> None:
    """LegacyBlankErrorReasonError message mentions EMPTY_CONFIRMED_REASONS and record_empty."""
    err = LegacyBlankErrorReasonError()
    msg = str(err)
    assert "EMPTY_CONFIRMED_REASONS" in msg
    assert "record_empty" in msg


def test_legacy_blank_error_reason_error_includes_callsite_hint() -> None:
    """LegacyBlankErrorReasonError with a callsite hint embeds it in the message."""
    hint = "instruments_service/engine/orchestrator.py:2315"
    err = LegacyBlankErrorReasonError(hint)
    assert hint in str(err)


def test_legacy_blank_error_reason_error_without_hint_has_no_brackets() -> None:
    """LegacyBlankErrorReasonError without a hint does not inject empty brackets."""
    err = LegacyBlankErrorReasonError()
    msg = str(err)
    assert " []" not in msg

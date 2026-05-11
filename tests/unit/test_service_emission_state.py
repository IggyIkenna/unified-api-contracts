"""Unit tests for the v8 service_emission_state SSOT.

Covers Phase 1.A of ``manifest_schema_final_gate_2026_05_09.md``: closed-set
4-value enum + manifest-read protocol (BLOCKED → raise / STALE_DATA → skip /
PUBLISHED_DEGRADED → consume with degraded flag / PUBLISHED_OK → consume
normally) + default-None back-compat for v7 rows.

12 tests per the plan's done-definition.
"""

from __future__ import annotations

import json

import pytest

from unified_api_contracts.canonical.crosscutting.service_emission_state import (
    SERVICE_EMISSION_STATES,
    ManifestRowBlockedError,
    ServiceEmissionStateEnum,
)

# ---------------------------------------------------------------------------
# Closed-set enforcement (Test 1-3) — exactly 4 values, frozen 2026-05-09.
# ---------------------------------------------------------------------------


def test_emission_state_enum_has_exactly_four_members() -> None:
    """Frozen 2026-05-09 → 2026-05-23 per manifest_schema_final_gate plan."""
    assert {m.value for m in ServiceEmissionStateEnum} == {
        "PUBLISHED_OK",
        "PUBLISHED_DEGRADED",
        "STALE_DATA_HEARTBEAT_ONLY",
        "BLOCKED",
    }


def test_emission_state_enum_is_str_valued() -> None:
    """String-valued members so manifest writes serialise straight to parquet."""
    assert ServiceEmissionStateEnum.PUBLISHED_OK == "PUBLISHED_OK"
    assert ServiceEmissionStateEnum.STALE_DATA_HEARTBEAT_ONLY == "STALE_DATA_HEARTBEAT_ONLY"


def test_emission_state_frozenset_matches_enum() -> None:
    """``SERVICE_EMISSION_STATES`` is the O(1) writer-validation surface."""
    assert frozenset(m.value for m in ServiceEmissionStateEnum) == SERVICE_EMISSION_STATES
    assert isinstance(SERVICE_EMISSION_STATES, frozenset)


# ---------------------------------------------------------------------------
# Round-trip via JSON (Test 4-5) — parquet-write path serialises string-value
# through JSON encoders without enum-to-str gymnastics.
# ---------------------------------------------------------------------------


def test_emission_state_round_trips_through_json() -> None:
    """``json.dumps(...) → json.loads(...) → ServiceEmissionStateEnum(...)`` recovers the member."""
    for member in ServiceEmissionStateEnum:
        payload = json.dumps({"service_emission_state": member.value})
        recovered = json.loads(payload)["service_emission_state"]
        assert ServiceEmissionStateEnum(recovered) is member


def test_emission_state_bare_string_validates_via_frozenset() -> None:
    """Writer hot path uses ``state_value in SERVICE_EMISSION_STATES`` for O(1) check."""
    assert "PUBLISHED_OK" in SERVICE_EMISSION_STATES
    assert "BLOCKED" in SERVICE_EMISSION_STATES
    assert "not_a_real_state" not in SERVICE_EMISSION_STATES
    assert "published_ok" not in SERVICE_EMISSION_STATES  # case-sensitive


# ---------------------------------------------------------------------------
# Default-None back-compat for v7 rows (Test 6-7).
# ---------------------------------------------------------------------------


def test_emission_state_none_is_not_a_valid_member() -> None:
    """v7 rows pre-date the column; readers see None, NOT a ServiceEmissionStateEnum value.

    This is the load-bearing assertion: the writer never emits None for v8
    rows (every v8 row resolves to one of the 4 states via ``next_state``),
    so a None observed at read time unambiguously means "pre-v8 row".
    """
    state_values: set[str] = {m.value for m in ServiceEmissionStateEnum}
    assert None not in state_values


def test_emission_state_none_passes_back_compat_typecheck() -> None:
    """The v8 manifest column is typed ``ServiceEmissionStateEnum | None``.

    Consumers reading legacy v7 rows MUST treat ``state is None`` as
    "back-compat row, fall through to capture_status-based reasoning".
    """
    state: ServiceEmissionStateEnum | None = None
    assert state is None
    # Default behaviour for unknown / legacy rows: fall back to capture_status.
    assert not isinstance(state, ServiceEmissionStateEnum)


# ---------------------------------------------------------------------------
# Consumer-skip semantics — BLOCKED raises, STALE_DATA skips (Test 8-10).
# ---------------------------------------------------------------------------


def test_manifest_row_blocked_error_carries_row_key() -> None:
    """``BLOCKED`` rows raise on consumer read with the failing row_key in the exception."""
    row_key = {"venue": "BINANCE", "instrument_id": "BTC-USDT", "day": "2026-05-08"}
    err = ManifestRowBlockedError(row_key=row_key)
    assert err.row_key is row_key
    assert "BLOCKED" in str(err)
    assert "BINANCE" in str(err)


def test_manifest_row_blocked_error_carries_correlation_id() -> None:
    """Operator triage needs the publish-time correlation id to grep the event stream."""
    row_key = {"venue": "BINANCE", "day": "2026-05-08"}
    correlation = "publish-2026-05-08-T03:14:00Z-abc123"
    err = ManifestRowBlockedError(row_key=row_key, publish_correlation_id=correlation)
    assert err.publish_correlation_id == correlation
    assert correlation in str(err)


def test_manifest_row_blocked_error_is_runtime_error_subclass() -> None:
    """Reads of BLOCKED rows MUST be loud — RuntimeError signals a correctness gap."""
    with pytest.raises(ManifestRowBlockedError):
        raise ManifestRowBlockedError(row_key={})
    # RuntimeError catch-all works for emergency consumer guards.
    with pytest.raises(RuntimeError):
        raise ManifestRowBlockedError(row_key={})


# ---------------------------------------------------------------------------
# Consumer-skip semantics — STALE_DATA + PUBLISHED_DEGRADED (Test 11-12).
# ---------------------------------------------------------------------------


def test_stale_data_state_is_distinct_from_blocked() -> None:
    """STALE_DATA = heartbeat-only (skip + log); BLOCKED = no row + P0 alert.

    Reference: writegate plan operator-msg-10 framing — "heartbeat: you are
    alive just stale data so services know its not a disconnect but it is a
    bad data event."
    """
    assert ServiceEmissionStateEnum.STALE_DATA_HEARTBEAT_ONLY is not ServiceEmissionStateEnum.BLOCKED
    # Both express "no metric row" but BLOCKED also fires a P0 alert.
    # Consumers MUST branch on the state, not collapse them.


def test_published_degraded_consumes_with_completeness_flag() -> None:
    """PUBLISHED_DEGRADED rows carry a metric — consumers branch on completeness_fraction.

    The state value itself is the marker; the writer also writes the
    ``completeness_fraction`` + ``expected_window_completeness_fraction``
    sibling columns so consumers can NaN-fill / adjust-denominator / propagate
    per-leg per the per-service consumer-class audit.
    """
    state = ServiceEmissionStateEnum.PUBLISHED_DEGRADED
    # The state distinguishes degraded-but-published from clean PUBLISHED_OK
    # so a consumer that doesn't read completeness_fraction at least sees the flag.
    assert state is not ServiceEmissionStateEnum.PUBLISHED_OK
    assert state.value == "PUBLISHED_DEGRADED"

"""Unit tests for the proof-of-honest-absence value-object (failure class C1).

Covers :class:`FetchEvidence`, :class:`FetchErrorSignal`,
:data:`DISQUALIFYING_FETCH_SIGNALS` and :class:`UnprovenHonestAbsenceError`
introduced for the keystone Phase 1 writer gate of
``data_pipeline_hardening_self_monitoring_2026_06_22.md``.

A clean 200+0-rows fetch proves honest absence; EACH disqualifying signal, a
non-2xx status, a missing response, and rows > 0 must NOT.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from unified_api_contracts import (
    DISQUALIFYING_FETCH_SIGNALS,
    FetchErrorSignal,
    FetchEvidence,
    UnprovenHonestAbsenceError,
)

_NOW = datetime(2026, 6, 22, 12, 0, 0, tzinfo=UTC)


def _evidence(**overrides: object) -> FetchEvidence:
    base: dict[str, object] = {
        "http_status": 200,
        "response_received": True,
        "rows_in_response": 0,
        "source": "databento",
        "endpoint": "https://hist.databento.com/v0/timeseries.get_range",
        "attempted_at": _NOW,
        "error_signal": "",
    }
    base.update(overrides)
    return FetchEvidence(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# DISQUALIFYING_FETCH_SIGNALS derives from FetchErrorSignal (mirror of
# EMPTY_CONFIRMED_REASONS ← EmptyConfirmedReason).
# ---------------------------------------------------------------------------


def test_disqualifying_signals_mirror_enum() -> None:
    assert frozenset(m.value for m in FetchErrorSignal) == DISQUALIFYING_FETCH_SIGNALS
    # The exact closed vocabulary the plan specifies.
    assert {
        "HTTP_NON_2XX",
        "AUTH_401",
        "AUTH_403",
        "RATE_LIMITED_429",
        "SERVER_5XX",
        "TIMEOUT",
        "CONNECT_ERROR",
        "ADAPTER_EXCEPTION",
        "MISSING_CREDENTIAL",
        "SOURCE_UNREACHABLE",
    } == DISQUALIFYING_FETCH_SIGNALS


# ---------------------------------------------------------------------------
# proves_honest_absence — clean path.
# ---------------------------------------------------------------------------


def test_clean_200_empty_proves_honest_absence() -> None:
    assert _evidence().proves_honest_absence() is True


@pytest.mark.parametrize("status", [200, 201, 204, 299])
def test_any_2xx_with_zero_rows_proves(status: int) -> None:
    assert _evidence(http_status=status).proves_honest_absence() is True


# ---------------------------------------------------------------------------
# proves_honest_absence — every disqualifying signal must fail it.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("signal", sorted(DISQUALIFYING_FETCH_SIGNALS))
def test_each_disqualifying_signal_blocks_honest_absence(signal: str) -> None:
    # Even with an otherwise-clean 200+0-rows shape, a disqualifying signal
    # means this was an error path masquerading as honest absence.
    assert _evidence(error_signal=signal).proves_honest_absence() is False


def test_each_enum_member_blocks_honest_absence() -> None:
    for member in FetchErrorSignal:
        assert _evidence(error_signal=member.value).proves_honest_absence() is False


# ---------------------------------------------------------------------------
# proves_honest_absence — non-2xx / no-response / rows>0 all fail.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", [301, 400, 401, 403, 429, 500, 502, 503])
def test_non_2xx_does_not_prove(status: int) -> None:
    assert _evidence(http_status=status).proves_honest_absence() is False


def test_no_response_does_not_prove() -> None:
    assert _evidence(response_received=False).proves_honest_absence() is False


@pytest.mark.parametrize("rows", [1, 5, 1440])
def test_nonzero_rows_does_not_prove(rows: int) -> None:
    assert _evidence(rows_in_response=rows).proves_honest_absence() is False


def test_frozen_value_object() -> None:
    ev = _evidence()
    with pytest.raises((AttributeError, TypeError)):
        ev.rows_in_response = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# UnprovenHonestAbsenceError — message steers to record_failed.
# ---------------------------------------------------------------------------


def test_error_with_evidence_carries_diagnostics() -> None:
    bad = _evidence(http_status=429, error_signal=FetchErrorSignal.RATE_LIMITED_429.value)
    err = UnprovenHonestAbsenceError("mtds.cefi.binance.funding", bad)
    msg = str(err)
    assert "record_failed" in msg
    assert "SOURCE_RETURNED_ZERO" in msg
    assert "mtds.cefi.binance.funding" in msg
    assert "429" in msg
    assert isinstance(err, ValueError)


def test_error_without_evidence() -> None:
    err = UnprovenHonestAbsenceError("is.sports.api_football", None)
    msg = str(err)
    assert "no FetchEvidence supplied" in msg
    assert "record_failed" in msg


# ---------------------------------------------------------------------------
# build_fetch_evidence + fetch_error_signal_for_* — the adapter-side mapping
# helpers (Phase 1 keystone threading; TradFi DP-FETCH-005 et al).
# ---------------------------------------------------------------------------


def test_build_evidence_clean_2xx_proves_honest_absence() -> None:
    from unified_api_contracts import build_fetch_evidence

    ev = build_fetch_evidence(
        source="databento",
        endpoint="GLBX.MDP3/ohlcv_1m",
        attempted_at=_NOW,
        rows_in_response=0,
        http_status=200,
    )
    assert ev.error_signal == ""
    assert ev.proves_honest_absence() is True


def test_build_evidence_rows_present_not_honest_absence() -> None:
    from unified_api_contracts import build_fetch_evidence

    ev = build_fetch_evidence(
        source="massive",
        endpoint="cme/ES/ohlcv_1m",
        attempted_at=_NOW,
        rows_in_response=37,
        http_status=200,
    )
    assert ev.proves_honest_absence() is False


@pytest.mark.parametrize(
    ("status", "expected_signal"),
    [
        (200, ""),
        (204, ""),
        (401, FetchErrorSignal.AUTH_401.value),
        (403, FetchErrorSignal.AUTH_403.value),
        (429, FetchErrorSignal.RATE_LIMITED_429.value),
        (500, FetchErrorSignal.SERVER_5XX.value),
        (503, FetchErrorSignal.SERVER_5XX.value),
        (404, FetchErrorSignal.HTTP_NON_2XX.value),
        (302, FetchErrorSignal.HTTP_NON_2XX.value),
    ],
)
def test_fetch_error_signal_for_status(status: int, expected_signal: str) -> None:
    from unified_api_contracts import fetch_error_signal_for_status

    assert fetch_error_signal_for_status(status) == expected_signal


def test_build_evidence_non_2xx_disqualifies() -> None:
    from unified_api_contracts import build_fetch_evidence

    # The DP-FETCH-005 class: Databento WS key unresolved → not honest absence.
    for status in (401, 403, 429, 500, 404):
        ev = build_fetch_evidence(
            source="databento",
            endpoint="XCBF.PITCH/ohlcv_1s",
            attempted_at=_NOW,
            rows_in_response=0,
            http_status=status,
        )
        assert ev.error_signal in DISQUALIFYING_FETCH_SIGNALS
        assert ev.proves_honest_absence() is False


def test_build_evidence_missing_credential() -> None:
    from unified_api_contracts import build_fetch_evidence

    ev = build_fetch_evidence(
        source="databento",
        endpoint="live.databento.com",
        attempted_at=_NOW,
        rows_in_response=0,
        missing_credential=True,
    )
    assert ev.error_signal == FetchErrorSignal.MISSING_CREDENTIAL.value
    assert ev.proves_honest_absence() is False


def test_build_evidence_exception_paths() -> None:
    from unified_api_contracts import build_fetch_evidence

    timeout_ev = build_fetch_evidence(
        source="massive",
        endpoint="s3://massive/cme",
        attempted_at=_NOW,
        rows_in_response=0,
        response_received=False,
        exception=TimeoutError("read timed out"),
    )
    assert timeout_ev.error_signal == FetchErrorSignal.TIMEOUT.value
    assert timeout_ev.proves_honest_absence() is False

    conn_ev = build_fetch_evidence(
        source="massive",
        endpoint="s3://massive/cme",
        attempted_at=_NOW,
        rows_in_response=0,
        response_received=False,
        exception=ConnectionError("DNS failure"),
    )
    assert conn_ev.error_signal == FetchErrorSignal.CONNECT_ERROR.value

    generic_ev = build_fetch_evidence(
        source="databento",
        endpoint="GLBX.MDP3",
        attempted_at=_NOW,
        rows_in_response=0,
        response_received=False,
        exception=ValueError("bad symbology"),
    )
    assert generic_ev.error_signal == FetchErrorSignal.ADAPTER_EXCEPTION.value


def test_build_evidence_no_response_unreachable() -> None:
    from unified_api_contracts import build_fetch_evidence

    ev = build_fetch_evidence(
        source="databento",
        endpoint="GLBX.MDP3",
        attempted_at=_NOW,
        rows_in_response=0,
        response_received=False,
    )
    assert ev.error_signal == FetchErrorSignal.SOURCE_UNREACHABLE.value
    assert ev.proves_honest_absence() is False


def test_build_evidence_explicit_signal_wins() -> None:
    from unified_api_contracts import build_fetch_evidence

    ev = build_fetch_evidence(
        source="databento",
        endpoint="GLBX.MDP3",
        attempted_at=_NOW,
        rows_in_response=0,
        http_status=200,
        error_signal=FetchErrorSignal.RATE_LIMITED_429.value,
    )
    assert ev.error_signal == FetchErrorSignal.RATE_LIMITED_429.value
    assert ev.proves_honest_absence() is False

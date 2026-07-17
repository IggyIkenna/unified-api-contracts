"""Tests for the evidence-gated bounded coverage-exclusion registry + its falsifier.

These tests encode the operator's hard constraint (2026-07-17): it must be IMPOSSIBLE to
declare a range out-of-bounds without evidence, and every declaration must be auditable
and falsifiable. ``SOURCE_COVERAGE_START`` was this same pattern WITHOUT these tests, and
it was wrong for months — hiding ~22,327 real objects behind floors nobody re-checked.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from scripts.check_coverage_exclusions import _data_findings, _structural_findings
from unified_api_contracts.canonical.coverage_exclusions import (
    COVERAGE_EXCLUSIONS,
    CoverageExclusion,
    CoverageExclusionError,
    ExclusionReason,
    all_coverage_exclusions,
    coverage_exclusions_for,
    find_coverage_exclusion,
    is_out_of_bounds,
)
from unified_api_contracts.canonical.crosscutting.honest_coverage import (
    OUT_OF_COVERAGE_WINDOW_REASONS,
    EmptyConfirmedReason,
    is_out_of_coverage_window,
)
from unified_api_contracts.registry.expected_coverage import (
    ExpectedState,
    expected_coverage,
    is_bounded_excluded,
)

_TODAY = date(2026, 7, 17)


def _valid(**overrides: object) -> CoverageExclusion:
    """A fully-evidenced exclusion; tests override single fields to prove the gate bites."""
    kwargs: dict[str, object] = {
        "asset_group": "cefi",
        "source": "EXAMPLE-VENUE",
        "data_type": "TRADES",
        "start": date(2024, 1, 1),
        "end": date(2024, 1, 31),
        "reason": ExclusionReason.UPSTREAM_OUTAGE,
        "evidence_uri": "https://status.example.com/incidents/2024-01-outage",
        "evidence_probe": "curl https://api.example.com/trades?day=2024-01-15 → 200 with empty payload",
        "verified_at": date(2026, 7, 1),
        "verified_by": "test-operator",
    }
    kwargs.update(overrides)
    return CoverageExclusion(**kwargs)  # pyright: ignore[reportArgumentType]


# ---------------------------------------------------------------------------
# THE REGISTRY SHIPS EMPTY — the honest default
# ---------------------------------------------------------------------------


def test_registry_ships_empty_no_range_declared_without_proof() -> None:
    """Nothing is declared out-of-bounds until it is PROVEN.

    Mirrors PROTOCOL_PAUSE_WINDOWS' stance: "don't encode pauses we can't prove from
    data". If this test fails, someone declared a range — that range must carry evidence
    that survives ``scripts/check_coverage_exclusions.py``.
    """
    assert COVERAGE_EXCLUSIONS == ()


def test_every_declaration_survives_structural_falsification() -> None:
    """THE STANDING GUARD — this is how the falsifier reaches CI.

    ``quality-gates.sh`` runs pytest, so every declaration is re-falsified on every gate
    run in every repo that imports UAC: evidence current (not stale), not redundant with a
    floor, no overlaps. The floors had no equivalent, which is exactly why they stayed
    wrong for months.

    The DATA layer (probe real manifest rows inside declared windows) needs a materialised
    availability index and runs via
    ``scripts/check_coverage_exclusions.py --index <availability_index.parquet>``.
    """
    assert _structural_findings(list(all_coverage_exclusions())) == []


def test_empty_registry_means_every_cell_is_in_model() -> None:
    assert find_coverage_exclusion("cefi", "BINANCE", "TRADES", date(2022, 9, 15)) is None
    assert not is_out_of_bounds("cefi", "BINANCE", "TRADES", date(2022, 9, 15))


def test_mdt_window_is_not_declared_it_is_a_capture_gap_to_recover() -> None:
    """The 32-day MDT window (2022-09-07..2022-10-01) must NEVER be declared out-of-bounds.

    The legacy ``market-data-tick-sports`` bucket HOLDS those 550,062 keys
    (verified two independent ways). Data in hand = a capture gap to RECOVER, not a range
    to declare. This test is a tripwire against exactly the mistake the floors made.
    """
    for day in (date(2022, 9, 7), date(2022, 9, 20), date(2022, 10, 1)):
        for source in ("BINANCE", "DERIBIT", "OKX", "BYBIT"):
            assert find_coverage_exclusion("cefi", source, "TRADES", day) is None


# ---------------------------------------------------------------------------
# EVIDENCE IS MANDATORY — a range without it must not be constructible
# ---------------------------------------------------------------------------


def test_declaration_without_evidence_uri_fails() -> None:
    """The operator's hard requirement: a range with no evidence field must fail a test."""
    with pytest.raises(CoverageExclusionError, match="evidence_uri is MANDATORY"):
        _valid(evidence_uri="")


def test_declaration_with_whitespace_only_evidence_fails() -> None:
    with pytest.raises(CoverageExclusionError, match="evidence_uri is MANDATORY"):
        _valid(evidence_uri="   ")


def test_declaration_with_non_machine_checkable_evidence_fails() -> None:
    """Prose is not evidence — an auditor must be able to GO AND LOOK."""
    with pytest.raises(CoverageExclusionError, match="not machine-checkable"):
        _valid(evidence_uri="the vendor told us on a call")


@pytest.mark.parametrize(
    "uri",
    [
        "_audits/mdt_gap_probe_2026_07_17/result.json",
        "audit://coverage_probe_2026_07_17/example-venue",
        "https://status.example.com/incidents/123",
    ],
)
def test_machine_checkable_evidence_prefixes_accepted(uri: str) -> None:
    assert _valid(evidence_uri=uri).evidence_uri == uri


def test_declaration_without_rerunnable_probe_fails() -> None:
    """A probe must be a re-runnable instruction, not a mood."""
    with pytest.raises(CoverageExclusionError, match="evidence_probe must be a re-runnable"):
        _valid(evidence_probe="checked, nothing there")


def test_declaration_without_verified_by_fails() -> None:
    with pytest.raises(CoverageExclusionError, match="verified_by is MANDATORY"):
        _valid(verified_by="")


def test_declaration_with_future_verified_at_fails() -> None:
    with pytest.raises(CoverageExclusionError, match="in the future"):
        _valid(verified_at=date.today() + timedelta(days=2))


def test_evidence_may_not_predate_the_window_it_claims_to_have_checked() -> None:
    with pytest.raises(CoverageExclusionError, match="precedes the window end"):
        _valid(start=date(2024, 1, 1), end=date(2024, 1, 31), verified_at=date(2023, 12, 1))


def test_inverted_interval_fails() -> None:
    with pytest.raises(CoverageExclusionError, match="precedes start"):
        _valid(start=date(2024, 2, 1), end=date(2024, 1, 1))


def test_untyped_reason_fails() -> None:
    """The reason must be a closed-set member — free-text reasons are unauditable."""
    with pytest.raises(CoverageExclusionError, match="must be an ExclusionReason member"):
        _valid(reason="it was broken")


def test_unknown_asset_group_fails() -> None:
    with pytest.raises(CoverageExclusionError, match="not one of"):
        _valid(asset_group="equities")


def test_market_closed_is_not_an_exclusion_reason() -> None:
    """Recurring calendar closure is owned by venue_trading_calendar + EXPECTED_WEEKEND/HOLIDAY.

    Modelling it here would duplicate a live primitive and let a recurring schedule
    masquerade as a one-off bounded outage.
    """
    assert not hasattr(ExclusionReason, "MARKET_CLOSED")


# ---------------------------------------------------------------------------
# LOOKUP semantics
# ---------------------------------------------------------------------------


def test_interval_is_closed_on_both_ends() -> None:
    exclusion = _valid(start=date(2024, 1, 10), end=date(2024, 1, 20))
    assert exclusion.covers(date(2024, 1, 10))
    assert exclusion.covers(date(2024, 1, 20))
    assert not exclusion.covers(date(2024, 1, 9))
    assert not exclusion.covers(date(2024, 1, 21))


def test_wildcard_data_type_covers_every_data_type(monkeypatch: pytest.MonkeyPatch) -> None:
    wildcard = _valid(data_type="*")
    monkeypatch.setattr(
        "unified_api_contracts.canonical.coverage_exclusions._INDEX",
        {wildcard.key: (wildcard,)},
    )
    assert find_coverage_exclusion("cefi", "EXAMPLE-VENUE", "TRADES", date(2024, 1, 15)) is wildcard
    assert find_coverage_exclusion("cefi", "EXAMPLE-VENUE", "BOOK_SNAPSHOT", date(2024, 1, 15)) is wildcard
    assert find_coverage_exclusion("cefi", "EXAMPLE-VENUE", "TRADES", date(2024, 3, 1)) is None


def test_lookup_is_asset_group_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    exclusion = _valid()
    monkeypatch.setattr(
        "unified_api_contracts.canonical.coverage_exclusions._INDEX",
        {exclusion.key: (exclusion,)},
    )
    assert find_coverage_exclusion("CeFi", "EXAMPLE-VENUE", "TRADES", date(2024, 1, 15)) is exclusion


def test_coverage_exclusions_for_returns_exact_and_wildcard(monkeypatch: pytest.MonkeyPatch) -> None:
    exact = _valid(data_type="TRADES")
    wildcard = _valid(data_type="*", start=date(2024, 5, 1), end=date(2024, 5, 3))
    monkeypatch.setattr(
        "unified_api_contracts.canonical.coverage_exclusions._INDEX",
        {exact.key: (exact,), wildcard.key: (wildcard,)},
    )
    found = coverage_exclusions_for("cefi", "EXAMPLE-VENUE", "TRADES")
    assert set(found) == {exact, wildcard}


def test_describe_carries_provenance_not_just_dates() -> None:
    """An out-of-model cell must always be explainable — never an unattributed hole."""
    described = _valid().describe()
    assert "UPSTREAM_OUTAGE" in described
    assert "https://status.example.com/incidents/2024-01-outage" in described
    assert "test-operator" in described


# ---------------------------------------------------------------------------
# CONSUMER (a) — the honest-coverage DENOMINATOR
# ---------------------------------------------------------------------------


def test_reason_is_out_of_model_clipped_from_denominator() -> None:
    """The operator's actual ask: an out-of-bounds range must leave the denominator."""
    reason = EmptyConfirmedReason.EXPECTED_UPSTREAM_OUT_OF_BOUNDS.value
    assert reason in OUT_OF_COVERAGE_WINDOW_REASONS
    assert is_out_of_coverage_window(reason)


def test_reason_is_distinct_from_known_source_gap_which_stays_in_denominator() -> None:
    """EXPECTED_KNOWN_SOURCE_GAP has live hand-stamped callsites (PYTH pre-archive, VIX 15m)
    and must KEEP its within-window semantics — reusing it would have silently moved live
    coverage numbers.
    """
    assert EmptyConfirmedReason.EXPECTED_KNOWN_SOURCE_GAP.value not in OUT_OF_COVERAGE_WINDOW_REASONS


# ---------------------------------------------------------------------------
# CONSUMER (b)/(c) — the ORACLE gate (enumerator seeding + adapter pre-fetch skip)
# ---------------------------------------------------------------------------


def test_oracle_gate_fires_out_of_bounds_with_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    """A declared range makes the oracle report EXPECTED_EMPTY + the typed reason.

    Adapters that consult the oracle pre-fetch (the lending_indices / risk_params pattern)
    inherit the skip, and the enumerator inherits the no-seed, from this one gate.
    """
    exclusion = _valid(asset_group="defi", source="AAVE_V3-ETHEREUM", data_type="lending_indices")
    monkeypatch.setattr(
        "unified_api_contracts.canonical.coverage_exclusions._INDEX",
        {exclusion.key: (exclusion,)},
    )
    result = expected_coverage("defi", "AAVE_V3-ETHEREUM", "lending_indices", date(2024, 1, 15))
    assert result.state is ExpectedState.EXPECTED_EMPTY
    assert result.reason == "EXPECTED_UPSTREAM_OUT_OF_BOUNDS"
    assert result.diagnostic is not None
    # The diagnostic must carry the evidence so the skip is auditable at the point of use.
    assert "https://status.example.com/incidents/2024-01-outage" in result.diagnostic


def test_oracle_leaves_cells_outside_the_window_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    exclusion = _valid(asset_group="defi", source="AAVE_V3-ETHEREUM", data_type="lending_indices")
    monkeypatch.setattr(
        "unified_api_contracts.canonical.coverage_exclusions._INDEX",
        {exclusion.key: (exclusion,)},
    )
    result = expected_coverage("defi", "AAVE_V3-ETHEREUM", "lending_indices", date(2025, 6, 2))
    assert result.reason != "EXPECTED_UPSTREAM_OUT_OF_BOUNDS"


# ---------------------------------------------------------------------------
# CONSUMER (d) — the VENUE-LEVEL pre-fetch skip (``is_bounded_excluded``)
#
# The MTDS orchestrator's ``_build_active_venues_for_date`` pre-skip gates a whole
# venue BEFORE any data_type is selected — unlike (b)/(c) above, it cannot consult
# the exact-data_type oracle. ``is_bounded_excluded`` is the wildcard-only sibling:
# it must fire for a venue-wide (``data_type="*"``) exclusion and must NOT fire for
# a data_type-scoped one (skipping the whole venue on a partial exclusion would drop
# data_types the exclusion never covered).
# ---------------------------------------------------------------------------


def test_is_bounded_excluded_fires_for_wildcard_exclusion(monkeypatch: pytest.MonkeyPatch) -> None:
    wildcard = _valid(asset_group="cefi", source="EXAMPLE-VENUE", data_type="*")
    monkeypatch.setattr(
        "unified_api_contracts.canonical.coverage_exclusions._INDEX",
        {wildcard.key: (wildcard,)},
    )
    assert is_bounded_excluded("cefi", "EXAMPLE-VENUE", date(2024, 1, 15)) is True
    assert is_bounded_excluded("cefi", "EXAMPLE-VENUE", date(2024, 3, 1)) is False


def test_is_bounded_excluded_ignores_data_type_scoped_exclusion(monkeypatch: pytest.MonkeyPatch) -> None:
    """A data_type-scoped exclusion must NOT skip the whole venue — only a wildcard can."""
    exact = _valid(asset_group="cefi", source="EXAMPLE-VENUE", data_type="TRADES")
    monkeypatch.setattr(
        "unified_api_contracts.canonical.coverage_exclusions._INDEX",
        {exact.key: (exact,)},
    )
    assert is_bounded_excluded("cefi", "EXAMPLE-VENUE", date(2024, 1, 15)) is False


def test_is_bounded_excluded_empty_registry_never_fires() -> None:
    assert is_bounded_excluded("cefi", "BINANCE", date(2024, 1, 15)) is False


# ---------------------------------------------------------------------------
# THE FALSIFIER — a wrong declaration must get CAUGHT
# ---------------------------------------------------------------------------


def _index_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_falsifier_fails_a_declaration_contradicted_by_real_captured_rows(tmp_path: object) -> None:
    """THE POINT OF THE WHOLE EXERCISE.

    A range declared impossible, with a real ``captured`` manifest row inside it, is WRONG.
    This is the check ``SOURCE_COVERAGE_START`` never had — and why it stayed wrong for
    months while we held 20/30/98-row parquets at day=2018-01-01.
    """
    exclusion = _valid()
    index_path = tmp_path / "availability_index.parquet"  # pyright: ignore[reportOperatorIssue]
    _index_frame(
        [
            {
                "date": "2024-01-15",
                "asset_group": "cefi",
                "source": "EXAMPLE-VENUE",
                "data_type": "TRADES",
                "capture_status": "captured",
                "row_count": 4_211,
            }
        ]
    ).to_parquet(index_path)

    findings = _data_findings([exclusion], index_path)  # pyright: ignore[reportArgumentType]
    assert len(findings) == 1
    assert "DECLARATION IS WRONG" in findings[0].message
    assert "RECOVER" in findings[0].message


def test_falsifier_low_bar_any_positive_row_count_falsifies(tmp_path: object) -> None:
    """Sensitivity is deliberate: a row that isn't marked ``captured`` but reports rows>0
    still falsifies. A false alarm is safe; a false pass hides a corpus.
    """
    exclusion = _valid()
    index_path = tmp_path / "availability_index.parquet"  # pyright: ignore[reportOperatorIssue]
    _index_frame(
        [
            {
                "date": "2024-01-20",
                "asset_group": "cefi",
                "source": "EXAMPLE-VENUE",
                "data_type": "TRADES",
                "capture_status": "attempted_failed",
                "row_count": 12,
            }
        ]
    ).to_parquet(index_path)

    assert len(_data_findings([exclusion], index_path)) == 1  # pyright: ignore[reportArgumentType]


def test_falsifier_passes_when_the_window_is_genuinely_empty(tmp_path: object) -> None:
    """A true declaration survives — the falsifier is not a blanket ban on exclusions."""
    exclusion = _valid()
    index_path = tmp_path / "availability_index.parquet"  # pyright: ignore[reportOperatorIssue]
    _index_frame(
        [
            # Real data OUTSIDE the window — must not falsify.
            {
                "date": "2024-03-01",
                "asset_group": "cefi",
                "source": "EXAMPLE-VENUE",
                "data_type": "TRADES",
                "capture_status": "captured",
                "row_count": 900,
            },
            # An honest empty INSIDE the window — consistent with the declaration.
            {
                "date": "2024-01-15",
                "asset_group": "cefi",
                "source": "EXAMPLE-VENUE",
                "data_type": "TRADES",
                "capture_status": "empty_confirmed",
                "row_count": 0,
            },
        ]
    ).to_parquet(index_path)

    assert _data_findings([exclusion], index_path) == []  # pyright: ignore[reportArgumentType]


def test_falsifier_does_not_cross_contaminate_other_sources(tmp_path: object) -> None:
    exclusion = _valid()
    index_path = tmp_path / "availability_index.parquet"  # pyright: ignore[reportOperatorIssue]
    _index_frame(
        [
            {
                "date": "2024-01-15",
                "asset_group": "cefi",
                "source": "OTHER-VENUE",
                "data_type": "TRADES",
                "capture_status": "captured",
                "row_count": 500,
            }
        ]
    ).to_parquet(index_path)

    assert _data_findings([exclusion], index_path) == []  # pyright: ignore[reportArgumentType]


def test_falsifier_refuses_to_pass_on_an_unreadable_surface(tmp_path: object) -> None:
    """Silence is not evidence — a probe that cannot read must FAIL, not report a pass."""
    index_path = tmp_path / "not_an_index.parquet"  # pyright: ignore[reportOperatorIssue]
    _index_frame([{"unrelated": 1}]).to_parquet(index_path)
    with pytest.raises(ValueError, match="not an availability index"):
        _data_findings([_valid()], index_path)  # pyright: ignore[reportArgumentType]


def test_falsifier_flags_stale_evidence() -> None:
    """ "It was true once" is not a licence to stay excluded — upstreams backfill history."""
    stale = _valid(verified_at=_TODAY - timedelta(days=400))
    findings = _structural_findings([stale])
    assert any("STALE EVIDENCE" in f.message for f in findings)


def test_falsifier_flags_a_range_the_floor_already_covers() -> None:
    """The deleted PREDICTION_KNOWN_COVERAGE_GAPS shape: a bounded range wholly below the
    floor does nothing but add risk.
    """
    redundant = _valid(
        asset_group="prediction",
        source="POLYMARKET",
        start=date(2020, 6, 12),
        end=date(2022, 11, 20),
        verified_at=_TODAY,
    )
    findings = _structural_findings([redundant])
    assert any("REDUNDANT" in f.message for f in findings)


def test_falsifier_flags_overlapping_declarations() -> None:
    first = _valid(start=date(2024, 1, 1), end=date(2024, 1, 31), verified_at=_TODAY)
    second = _valid(start=date(2024, 1, 15), end=date(2024, 2, 15), verified_at=_TODAY)
    findings = _structural_findings([first, second])
    assert any("OVERLAP" in f.message for f in findings)


def test_falsifier_is_quiet_on_a_clean_declaration() -> None:
    assert _structural_findings([_valid(verified_at=_TODAY)]) == []

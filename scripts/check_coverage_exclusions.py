#!/usr/bin/env python
"""FALSIFIER for declared bounded coverage exclusions — prove every declaration WRONG.

# Epic: data-pipeline-correctness
# Lifecycle: PERMANENT — this is a standing guard, not a one-off migration script.
# Delete-when: never (delete only if COVERAGE_EXCLUSIONS itself is retired).

WHY THIS EXISTS
===============

``SOURCE_COVERAGE_START`` — the floor registry this module's subject is the bounded
sibling of — was WRONG for months. Its sports floors declared 2018-2020 uncapturable
while we held ~22,327 real objects for exactly those dates. Nothing ever re-checked the
claim, so nothing ever caught it; it was amended only when a human happened to probe the
buckets by hand (UAC@c280e1ff, 2026-07-16).

The lesson is not "be more careful when declaring". It is that **a declaration must be
CONTINUOUSLY FALSIFIABLE, not a one-time assertion**. This script is that falsifier: for
every declared interval it asks the only question that matters —

    *does any real data exist inside a range we declared impossible?*

— and FAILS if the answer is yes. A declaration here is a standing, testable claim about
the world. If reality disagrees, reality wins and the declaration is deleted.

TWO LAYERS
==========

1. **Structural falsification** (always, offline, runs in QG): the evidence contract is
   real and current — mandatory machine-checkable ``evidence_uri``, a re-runnable
   ``evidence_probe``, ``verified_by``, and evidence that has not gone STALE
   (``EVIDENCE_MAX_AGE_DAYS``). Also catches ranges that are secretly floors, ranges
   that overlap each other, and ranges that duplicate a ``SOURCE_COVERAGE_START`` clip
   (a bounded interval must earn its keep — if the floor already covers it, it is
   redundant, exactly like the deleted ``PREDICTION_KNOWN_COVERAGE_GAPS``).

2. **Data falsification** (``--index <availability_index.parquet>``): probe the real
   manifest for rows inside each declared interval. Any real row FAILS the check.

Layer 2 takes an explicit index path rather than reaching into GCS itself because UAC is
a T0 contract package: it may not depend on UTL / unified-cloud-interface (tier + import
architecture), and bucket paths are resolved via ``resolve_bucket_name(...)``, never
inlined. The auditor materialises the index (audits already do) and points this at it.

THE SENSITIVITY ASYMMETRY (deliberate — do not "fix" it)
=======================================================

This falsifier uses a LOW bar for what counts as data: any manifest row marked
``captured``, or any row reporting >0 rows, inside a declared window is enough to FAIL.
That is intentionally more sensitive than the HIGH bar the floors' amendment used when
*declaring* a floor (parquet that PARSES + >=1 row + HISTORICALLY COHERENT with its
partition — object existence alone was explicitly rejected as evidence there, because
the corpus replicates present-day reference data under historical partitions).

The bars differ because the failure directions differ:

* A false FAIL here refuses an exclusion → the range stays IN the denominator → coverage
  reads honestly LOW. Safe.
* A false PASS lets a wrong exclusion stand → real data becomes invisible by declaration
  → the exact ``SOURCE_COVERAGE_START`` catastrophe. Unsafe.

So: when in doubt, FAIL. A noisy falsifier costs an investigation; a permissive one costs
a silently truncated corpus.

USAGE
=====

    # structural only (what QG runs — passes trivially while the registry is empty)
    python scripts/check_coverage_exclusions.py

    # + data falsification against a materialised availability index
    python scripts/check_coverage_exclusions.py --index /path/to/availability_index.parquet
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from unified_api_contracts.canonical.coverage_exclusions import (
    CoverageExclusion,
    all_coverage_exclusions,
)
from unified_api_contracts.canonical.coverage_starts import coverage_start

# Manifest columns the data probe understands. The availability index is the canonical
# surface; these are its stable column names.
_COL_DATE = "date"
_COL_ASSET_GROUP = "asset_group"
_COL_DATA_TYPE = "data_type"
_COL_CAPTURE_STATUS = "capture_status"
_COL_ROW_COUNT = "row_count"
# The source/venue axis is named differently per asset group; probe all of them.
_SOURCE_COLUMNS = ("source", "venue", "data_source")

_CAPTURED = "captured"


class _Finding:
    """One reason a declaration failed falsification."""

    def __init__(self, exclusion: CoverageExclusion, message: str) -> None:
        self.exclusion = exclusion
        self.message = message

    def render(self) -> str:
        return f"  ✗ {self.exclusion._key_repr()} {self.exclusion.start} → {self.exclusion.end}\n      {self.message}"


def _structural_findings(exclusions: Sequence[CoverageExclusion]) -> list[_Finding]:
    """Falsify the evidence contract itself — staleness, redundancy, overlap.

    The mandatory-evidence fields are already enforced at construction
    (``CoverageExclusion.__post_init__``), so an unevidenced range cannot reach this
    function. What remains falsifiable statically is whether the evidence is still
    CURRENT and whether the range is doing any work at all.
    """
    findings: list[_Finding] = []
    today = datetime.now(UTC).date()

    for exclusion in exclusions:
        # STALE evidence — "it was true once" is not a licence to stay excluded. Upstreams
        # backfill their own history; an exclusion nobody has re-checked in a year is an
        # assertion, not a fact.
        if exclusion.is_stale(as_of=today):
            age = (today - exclusion.verified_at).days
            findings.append(
                _Finding(
                    exclusion,
                    f"STALE EVIDENCE: last verified {exclusion.verified_at.isoformat()} ({age}d ago). "
                    f"Re-run the probe and refresh verified_at, or DELETE the declaration. "
                    f"Probe: {exclusion.evidence_probe}",
                )
            )

        # REDUNDANT vs the floor — if SOURCE_COVERAGE_START already clips the whole window,
        # the bounded range adds nothing and only adds risk. This is precisely the shape of
        # the deleted PREDICTION_KNOWN_COVERAGE_GAPS entry.
        floor = coverage_start(exclusion.asset_group, exclusion.source)
        if floor is not None and exclusion.end < floor:
            findings.append(
                _Finding(
                    exclusion,
                    f"REDUNDANT: entirely below SOURCE_COVERAGE_START {floor.isoformat()} — the floor "
                    "already clips this window. Delete the declaration (a bounded exclusion must "
                    "cover days the floor does not).",
                )
            )

    # OVERLAPPING declarations for the same key — two intervals claiming the same days means
    # at least one is unowned/duplicated, and their evidence cannot both be the reason.
    by_key: dict[tuple[str, str, str], list[CoverageExclusion]] = {}
    for exclusion in exclusions:
        by_key.setdefault(exclusion.key, []).append(exclusion)
    for key_exclusions in by_key.values():
        ordered = sorted(key_exclusions, key=lambda e: e.start)
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            if later.start <= earlier.end:
                findings.append(
                    _Finding(
                        later,
                        f"OVERLAP: this window overlaps {earlier.start.isoformat()} → "
                        f"{earlier.end.isoformat()} for the same key. Merge them, or narrow one — "
                        "overlapping declarations have ambiguous provenance.",
                    )
                )
    return findings


def _load_index(index_path: Path) -> pd.DataFrame:
    """Read the availability index. Fails loudly — a probe that cannot read is not a pass."""
    frame = pd.read_parquet(index_path)
    missing = {_COL_DATE, _COL_ASSET_GROUP, _COL_DATA_TYPE} - set(frame.columns)
    if missing:
        raise ValueError(
            f"{index_path} is not an availability index — missing columns {sorted(missing)}. "
            "Refusing to report a PASS from a surface I cannot read (silence is not evidence)."
        )
    return frame


def _real_data_mask(frame: pd.DataFrame) -> pd.Series:
    """Rows that represent REAL data, at the deliberately LOW sensitivity bar.

    ``captured`` status OR a positive row_count. Anything that looks like data counts —
    see the module docstring on why this errs toward failing.
    """
    mask = pd.Series(False, index=frame.index)
    if _COL_CAPTURE_STATUS in frame.columns:
        mask = mask | (frame[_COL_CAPTURE_STATUS].astype("string") == _CAPTURED)
    if _COL_ROW_COUNT in frame.columns:
        mask = mask | (pd.to_numeric(frame[_COL_ROW_COUNT], errors="coerce").fillna(0) > 0)
    return mask


def _data_findings(exclusions: Sequence[CoverageExclusion], index_path: Path) -> list[_Finding]:
    """THE FALSIFIER: does real data exist inside a range we declared impossible?"""
    findings: list[_Finding] = []
    frame = _load_index(index_path)
    dates = pd.to_datetime(frame[_COL_DATE], errors="coerce").dt.date
    real = _real_data_mask(frame)

    for exclusion in exclusions:
        in_window = (
            (dates >= exclusion.start)
            & (dates <= exclusion.end)
            & (frame[_COL_ASSET_GROUP].astype("string").str.lower() == exclusion.asset_group)
            & real
        )
        if exclusion.data_type != "*":
            in_window = in_window & (frame[_COL_DATA_TYPE].astype("string") == exclusion.data_type)

        # Match the source on whichever axis this index carries.
        source_matched = pd.Series(False, index=frame.index)
        source_axis_found = False
        for column in _SOURCE_COLUMNS:
            if column in frame.columns:
                source_axis_found = True
                source_matched = source_matched | (
                    frame[column].astype("string").str.upper() == exclusion.source.upper()
                )
        if source_axis_found:
            in_window = in_window & source_matched

        hits = int(in_window.sum())
        if hits > 0:
            sample = frame.loc[in_window, _COL_DATE].astype("string").head(5).tolist()
            findings.append(
                _Finding(
                    exclusion,
                    f"DECLARATION IS WRONG — falsified by {hits} real manifest row(s) inside the "
                    f"declared-impossible window (sample dates: {sample}). We HOLD data here. "
                    "This is not an out-of-bounds range; it is a capture gap with the data in hand, "
                    "or the window is simply wrong. DELETE the declaration and RECOVER the data. "
                    f"Evidence that claimed otherwise: {exclusion.evidence_uri} (verified "
                    f"{exclusion.verified_at.isoformat()} by {exclusion.verified_by}).",
                )
            )
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Falsify every declared bounded coverage exclusion.",
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=None,
        help=(
            "Path to a materialised availability_index.parquet. When given, runs DATA "
            "falsification (probe the manifest for real rows inside declared windows). "
            "Without it, only the structural/evidence-currency layer runs."
        ),
    )
    args = parser.parse_args(argv)
    index_path: Path | None = args.index

    exclusions = all_coverage_exclusions()
    if not exclusions:
        # The honest default. An empty registry is not a gap to fill — it means nothing has
        # been PROVEN uncapturable, which is exactly where a registry like this should sit
        # until evidence says otherwise.
        print("✓ COVERAGE_EXCLUSIONS is empty — no declarations to falsify (honest default).")
        return 0

    findings = _structural_findings(exclusions)
    if index_path is not None:
        findings.extend(_data_findings(exclusions, index_path))
    else:
        print(
            "! No --index given: DATA falsification skipped. Structural/evidence-currency "
            "checks only. Run with --index <availability_index.parquet> to falsify declarations "
            "against real manifest rows."
        )

    print(f"Falsifying {len(exclusions)} declared exclusion(s)...")
    if findings:
        print(f"\n✗ FAILED — {len(findings)} finding(s):\n")
        for finding in findings:
            print(finding.render())
        print(
            "\nA declaration that reality contradicts is not a declaration — it is a bug that "
            "hides data. Fix the registry, do not silence this check."
        )
        return 1

    print("✓ All declarations survived falsification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

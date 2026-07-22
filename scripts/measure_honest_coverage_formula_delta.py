# Epic: infrastructure_master
# Lifecycle: reusable — re-run before actually shipping the compute_honest_coverage()
#   formula change (plans/active/issues/sports_shard_enumeration_cartesian_blowup_2026_07_20.md
#   Part 4.1); prod manifests move daily, so the measured deltas below have a date on them
#   and must be re-verified immediately before the formula ships, not trusted from a stale run.
# Delete-when: the Part 4.1 formula change ships AND its final go/no-go re-measurement is done —
#   at that point this script has served its purpose and can be deleted (or kept as a permanent
#   coverage-formula-drift monitor if the operator wants standing visibility into this delta).
"""INVESTIGATION-ONLY. Read-only. Writes nothing to GCS/manifests.

Measures the real production before/after honest-coverage delta for the proposed
UAC formula change (drop empty_confirmed from both num+denom, matching
instruments-service/scripts/measure_honest_coverage.py's _count_statuses), across
every asset group, against real prod manifests in central-element-323112.

Design (why it's built this way):
  * The PROPOSED-formula data path is the REAL production module
    instruments-service/scripts/measure_honest_coverage.py, loaded via
    importlib (never edited on disk) and driven through its own
    `_read_manifest()` (pinned-primary bucket selection + secondary-bucket
    expected_unattempted-skeleton merge) and its own `_count_statuses()` --
    so the "proposed" number is guaranteed to match what running that script
    for real would print, not a re-derivation. For cefi (the one AG with the
    MVP read-time gate, `_MVP_READ_TIME_GATE_AGS`), we also apply the real
    `filter_manifest_to_expected()` gate before counting, mirroring
    `_compute_coverage()`'s own per-AG loop exactly.
  * That module's column list omits `error_reason`, which the CURRENT UAC
    formula needs (out_of_window / known_empty vs pending_fetch
    classification). We monkeypatch the *in-process* module's column-list
    globals to add "error_reason" (no file on disk is touched) so the SAME
    merged + MVP-gated dataframe backs BOTH formulas -- apples to apples.
  * The CURRENT-formula number is computed by building a real
    unified_api_contracts.CaptureStatusCounts from that dataframe (using the
    exact classification rules in UTL's read_capture_status_counts /
    UAC's _honest_coverage_logic.py docstring) and calling the REAL
    unified_api_contracts.compute_honest_coverage() against it -- the formula
    itself is never reimplemented, only the row->CaptureStatusCounts folding
    (which mirrors UTL's read_capture_status_counts verbatim).

MEASURED RESULT (2026-07-22, prod central-element-323112 — see the plan doc's
Part 4.1 section for the full table and discussion):

    asset_group | total_rows | current_pct | proposed_pct | delta_pp
    CEFI        | 8,980,261  | 60.88%      | 49.38%       | -11.50
    DEFI        | 52,293,294 | 68.49%      | 68.44%       | -0.05
    TRADFI      | 6,262,988  | 80.75%      | 71.79%       | -8.96
    SPORTS      | 1,977,165  | 94.32%      | 84.13%       | -10.19
    PREDICTION  | 745,358    | 99.55%      | 94.36%       | -5.19

Every asset group moves DOWN under the proposed formula (DEFI's move is
negligible because its out_of_window clipping already absorbs almost all of
its empty_confirmed rows — the other four have much smaller out_of_window
carve-outs relative to their empty_confirmed count, so excluding
empty_confirmed entirely hits them harder). This is real, current-methodology
production data, not an estimate — re-run this script for a fresh number
before treating the table above as authoritative for a ship decision.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("measure_delta")

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / "unified-trading-library"))
sys.path.insert(0, str(WORKSPACE / "unified-api-contracts"))

from unified_api_contracts import (  # noqa: E402
    CaptureStatusCounts,
    OUT_OF_COVERAGE_WINDOW_REASONS,
    SCHEDULE_DEFINING_DATA_TYPES,
    compute_honest_coverage,
)

# --- load the REAL production script as a module, unmodified on disk ---
MHC_PATH = WORKSPACE / "instruments-service" / "scripts" / "measure_honest_coverage.py"
spec = importlib.util.spec_from_file_location("mhc_real", MHC_PATH)
assert spec is not None and spec.loader is not None
mhc = importlib.util.module_from_spec(spec)
sys.modules["mhc_real"] = mhc
spec.loader.exec_module(mhc)


# In-process only: extend the column lists this module's readers pull so
# error_reason rides along for the CURRENT-formula classification. This does
# NOT touch the file on disk -- it mutates the already-imported module object
# in this Python process only (verify with `git status`/`git diff` post-run).
def _plus_reason(cols: list[str]) -> list[str]:
    return list(cols) if "error_reason" in cols else [*cols, "error_reason"]


mhc._READ_COLUMNS_WITH_CHAIN = _plus_reason(mhc._READ_COLUMNS_WITH_CHAIN)
mhc._READ_COLUMNS = _plus_reason(mhc._READ_COLUMNS)
mhc._READ_COLUMNS_FALLBACK = _plus_reason(mhc._READ_COLUMNS_FALLBACK)
mhc._READ_COLUMNS_LEGACY = _plus_reason(mhc._READ_COLUMNS_LEGACY)
mhc._READ_COLUMNS_MIN = _plus_reason(mhc._READ_COLUMNS_MIN)

logger.info("Patched (in-process only) column lists; WITH_CHAIN=%s", mhc._READ_COLUMNS_WITH_CHAIN)

_EXPECTED_PREFIX = "EXPECTED_"


def build_capture_status_counts(df: pd.DataFrame) -> CaptureStatusCounts:
    """Fold raw manifest rows into a CaptureStatusCounts.

    Mirrors unified_trading_library.manifest_writer._queries.read_capture_status_counts
    classification rules verbatim (verified against that function's source
    2026-07-22): EXPECTED_* prefix splits expected_unattempted into
    known_empty/pending_fetch; OUT_OF_COVERAGE_WINDOW_REASONS + the
    schedule-defining-FIXTURES SOURCE_RETURNED_ZERO carve-out identify
    out_of_window (a subset of empty_confirmed).
    """
    if "capture_status" not in df.columns:
        return CaptureStatusCounts(captured=len(df))

    status = df["capture_status"].astype(str)
    reason = df["error_reason"].astype(str) if "error_reason" in df.columns else pd.Series("", index=df.index)

    captured = int((status == "captured").sum())
    empty_mask = status == "empty_confirmed"
    empty_confirmed = int(empty_mask.sum())
    attempted_failed = int((status == "attempted_failed").sum())

    eu_mask = status == "expected_unattempted"
    known_empty = 0
    pending_fetch = 0
    if eu_mask.any():
        eu_reasons = reason[eu_mask]
        known_empty = int(eu_reasons.str.startswith(_EXPECTED_PREFIX).sum())
        pending_fetch = int((~eu_reasons.str.startswith(_EXPECTED_PREFIX)).sum())

    out_of_window = 0
    if empty_mask.any():
        empty_reasons = reason[empty_mask]
        oow_mask = empty_reasons.isin(OUT_OF_COVERAGE_WINDOW_REASONS)
        if "data_type" in df.columns:
            empty_dt = df.loc[empty_mask, "data_type"].astype(str)
            sched_mask = empty_dt.isin(SCHEDULE_DEFINING_DATA_TYPES) & (empty_reasons == "SOURCE_RETURNED_ZERO")
            oow_mask = oow_mask | sched_mask
        out_of_window = int(oow_mask.sum())

    return CaptureStatusCounts(
        captured=captured,
        empty_confirmed=empty_confirmed,
        attempted_failed=attempted_failed,
        expected_unattempted_known_empty=known_empty,
        expected_unattempted_pending_fetch=pending_fetch,
        out_of_window=out_of_window,
    )


def main() -> None:
    results: list[dict[str, object]] = []

    for ag in mhc._KNOWN_ASSET_GROUPS:
        t0 = time.monotonic()
        print(f"\n{'=' * 70}\n{ag.upper()} -- start {time.strftime('%H:%M:%S')}\n{'=' * 70}", flush=True)
        try:
            df = mhc._read_manifest(ag, merge=True)
        except Exception as exc:  # noqa: BLE001 -- investigation script, report don't crash
            logger.error("  [%s] manifest read raised: %s", ag, exc)
            results.append({"asset_group": ag.upper(), "status": f"NOT MEASURED - blocked: {exc!r}"})
            continue

        if df is None or df.empty:
            logger.warning("  [%s] no manifest accessible from any candidate bucket", ag)
            results.append({"asset_group": ag.upper(), "status": "NOT MEASURED - no candidate bucket accessible"})
            continue

        print(f"  [{ag}] manifest read done in {time.monotonic() - t0:.1f}s, {len(df):,} rows", flush=True)

        # Mirror _compute_coverage's per-AG MVP read-time gate exactly (cefi only,
        # today) so the "proposed" number matches what the nightly coverage.json
        # would actually show, and both formulas see the identical row population.
        df_l2 = df
        mvp_gated = False
        if ag in mhc._MVP_READ_TIME_GATE_AGS:
            try:
                checker = mhc._get_completeness_module()
                t_gate = time.monotonic()
                df_l2 = checker.filter_manifest_to_expected(ag, df)
                mvp_gated = True
                print(
                    f"  [{ag}] MVP read-time gate applied in {time.monotonic() - t_gate:.1f}s: "
                    f"{len(df):,} -> {len(df_l2):,} rows",
                    flush=True,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("  [%s] MVP gate failed (%s) -- using unfiltered df", ag, exc)
                df_l2 = df

        total_rows = len(df_l2)

        # PROPOSED formula: the REAL production _count_statuses (unmodified logic).
        proposed_raw = mhc._count_statuses(df_l2)

        # CURRENT formula: real CaptureStatusCounts -> real compute_honest_coverage.
        counts = build_capture_status_counts(df_l2)
        current_ratio = compute_honest_coverage(counts)
        current_pct = round(current_ratio * 100, 4)

        proposed_pct = round(float(proposed_raw["coverage_pct"]), 4)

        empty_confirmed_count = counts.empty_confirmed
        empty_pct_of_total = round(100.0 * empty_confirmed_count / total_rows, 4) if total_rows else 0.0

        delta_pp = round(proposed_pct - current_pct, 4)

        row = {
            "asset_group": ag.upper(),
            "mvp_gate_applied": mvp_gated,
            "total_rows": total_rows,
            "captured": counts.captured,
            "empty_confirmed": empty_confirmed_count,
            "empty_confirmed_pct_of_total": empty_pct_of_total,
            "attempted_failed": counts.attempted_failed,
            "expected_unattempted_known_empty": counts.expected_unattempted_known_empty,
            "expected_unattempted_pending_fetch": counts.expected_unattempted_pending_fetch,
            "expected_unattempted_total": counts.expected_unattempted_known_empty
            + counts.expected_unattempted_pending_fetch,
            "out_of_window": counts.out_of_window,
            "current_coverage_pct": current_pct,
            "proposed_coverage_pct": proposed_pct,
            "delta_pp": delta_pp,
            "direction": "UP" if delta_pp > 0 else ("DOWN" if delta_pp < 0 else "FLAT"),
        }
        results.append(row)
        print(f"  [{ag}] TOTAL elapsed {time.monotonic() - t0:.1f}s", flush=True)
        print(json.dumps(row, indent=2), flush=True)

        # Free memory before the next (possibly huge) asset_group.
        del df, df_l2

    print("\n\n" + "#" * 70)
    print("# FINAL SUMMARY")
    print("#" * 70)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

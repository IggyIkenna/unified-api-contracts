"""Sports "right days" SSOT — pinned smoke dates + the golden verification window.

Single source of truth for the specific calendar dates the sports pipeline's
smoke tests and verification/backfill tooling assert against. Before this
module, each consumer hardcoded its own copy of these dates (drift risk: a
date pinned for one reason — e.g. re-measured league-shard counts — silently
went stale in every OTHER copy). SSOT: `sports_consolidated_closeout_2026_07_19.md`
Track K ("SMOKE + SPEED + right-days").

Provides:
- ``SPORTS_SMOKE_DATES``: single dates pinned for specific smoke-test properties
  (a genuinely busy match day, a legitimately thin day, two known-buggy repro
  dates).
- ``SPORTS_GOLDEN_WINDOW_START`` / ``SPORTS_GOLDEN_WINDOW_END``: the EPL 2025
  91-day verification window used by backfill/verification tooling — long
  enough to satisfy every rolling/CLV lookback in the sports feature set.
"""

from __future__ import annotations

from typing import Final

# Pinned smoke dates. `resolve_latest_captured_date()` picks whatever is freshest,
# which for sports can legitimately be a near-empty holiday slate — so an
# unguided run can land on a thin day and PASS while the pipeline is broken.
# Measured 2026-07-19 (league-shard counts): Sat 2025-12-20 = 26 shards (busy)
# vs 2025-12-24 = 2 and 2025-12-25/31 = 1.
SPORTS_SMOKE_DATES: Final[dict[str, str]] = {
    # a genuinely busy match day — real volume MUST come back; empty here is a FAILURE
    "busy": "2025-12-20",
    # legitimately near-empty (Christmas Eve) — the ONLY date where empty_confirmed passes
    "thin": "2025-12-24",
    # sports_gw_enrichment §B2 repro: raw exists but the adapter emitted nothing
    # (615-min horizon dead-zone)
    "known_buggy_odds": "2025-12-18",
    # §V repro: pre-cutover date where a stale legacy entity=fixtures object still
    # exists, so a split-first read regression shows up as round/coach going sparse
    # again
    "known_buggy_fixtures": "2024-03-09",
}

# EPL 2025 golden 91-day verification window — long enough to satisfy every
# rolling/CLV lookback in the sports feature set (per the coverage table in
# `plans/active/honest_coverage_smoke_harness_2026_06_28.md`).
SPORTS_GOLDEN_WINDOW_START: Final[str] = "2025-09-01"
SPORTS_GOLDEN_WINDOW_END: Final[str] = "2025-11-30"

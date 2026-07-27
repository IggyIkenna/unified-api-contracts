"""P95 data-availability lag per sports data source.

These constants express how long after match-end each source typically takes to
publish complete post-match data.  Used by instruments-service to derive
``CanonicalFixture.report_time = match_end_time + <source_lag>``.

Values are empirically calibrated p95 latencies (seconds); callers that need
stricter SLAs should use their own percentile.

Re-pin review (2026-07-27, ~13-day live accrual,
``instruments-service/scripts/aggregate_source_latency_observations.py --emit-constants``
against ``instruments-store-sports-prd``'s ``_index/latency_observations``): only
API_FOOTBALL accrued samples (n=2504, all first-ATTEMPT/ceiling observations — the
live scheduler's genuine first-success poller has not yet confirmed a single
``first_success=True`` row, see the source doc). Observed p95=673s is below the
1800s floor, so per the aggregator's fail-safe (never lower from a ceiling-only
sample without ``--allow-lower``) the constant is UNCHANGED — this is a CONFIRM,
not a re-pin. SFI/UNDERSTAT/FOOTYSTATS/OPEN_METEO all read n=0 — UNDER-SAMPLED,
each for a distinct structural reason (no live trigger wiring / a confirmed
scheduler bug / never-instrumented). Full per-source verdict + sample counts +
root causes:
``unified-trading-pm/plans/active/sports_live_availability_and_source_latency_2026_07_24.md``
§ "Source-latency validation" Step 2; the discovered scheduler bug is tracked in
``unified-trading-pm/plans/active/issues/sports_post_match_trigger_24h_lookback_bug_2026_07_27.md``.
None of the 5 constants change value this cycle.
"""

from typing import Final

SFI_DATA_LAG_P95_SECONDS: Final[int] = 300
"""SoccerFootballInfo progressive-stats feed: data stabilises ~5 min post-match.

UNDER-SAMPLED (n=0, 2026-07-27 re-pin review) — SFI_PROGRESSIVE_STATS has no
corresponding trigger in ``deployment-service/configs/sports-trigger-tiers.yaml``'s
``post_match`` tier, so the live scheduler never dispatches it and no observation
can ever accrue until a trigger is added. Assumed value retained unchanged.
"""

UNDERSTAT_DATA_LAG_P95_SECONDS: Final[int] = 7200
"""Understat xG + advanced stats: typically available 2 h after full-time.

UNDER-SAMPLED (n=0, 2026-07-27 re-pin review) — the live ``stats_delayed`` trigger
(offset_hours=24) that targets XG/understat can structurally never fire: see
``sports_post_match_trigger_24h_lookback_bug_2026_07_27.md`` (the fixture-calendar
lookback window closes ~2h post-kickoff, long before a 24h-offset trigger becomes
due). Assumed value retained unchanged pending that fix.
"""

FOOTYSTATS_DATA_LAG_P95_SECONDS: Final[int] = 3600
"""FootyStats match stats: typically available 1 h after full-time.

UNDER-SAMPLED (n=0, 2026-07-27 re-pin review) — FootyStats is not mapped in
``ENTITY_TO_OBSERVATION_TARGET`` (``deployment-service/deployment_service/
sports_latency_observation.py``), so this source has never been instrumented by
the live-lag recorder at all. Assumed value retained unchanged.
"""

API_FOOTBALL_RESULT_LAG_P95_SECONDS: Final[int] = 1800
"""API-Football result + stats endpoint: typically available 30 min after full-time.

CONFIRMED, not re-pinned (n=2504, 2026-07-27 re-pin review, ~13-day live accrual):
observed p50=361s / p95=673s / max=898s, all first-ATTEMPT ceiling observations
(``first_success`` is 0/2504 — the genuine first-success confirmation has never
landed live). Per the aggregator's floor-at-assumed fail-safe, a ceiling-only
sample below the current constant does not lower it. Assumed value retained.
"""

OPEN_METEO_HISTORICAL_LAG_SECONDS: Final[int] = 3600
"""Open-Meteo historical weather: hourly archive typically available 1 h after the hour.

UNDER-SAMPLED (n=0, 2026-07-27 re-pin review) — Open-Meteo is not mapped in
``ENTITY_TO_OBSERVATION_TARGET`` (``deployment-service/deployment_service/
sports_latency_observation.py``), so this source has never been instrumented by
the live-lag recorder at all. Assumed value retained unchanged.
"""

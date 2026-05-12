"""P95 data-availability lag per sports data source.

These constants express how long after match-end each source typically takes to
publish complete post-match data.  Used by instruments-service to derive
``CanonicalFixture.report_time = match_end_time + <source_lag>``.

Values are empirically calibrated p95 latencies (seconds); callers that need
stricter SLAs should use their own percentile.
"""

from typing import Final

SFI_DATA_LAG_P95_SECONDS: Final[int] = 300
"""SoccerFootballInfo progressive-stats feed: data stabilises ~5 min post-match."""

UNDERSTAT_DATA_LAG_P95_SECONDS: Final[int] = 7200
"""Understat xG + advanced stats: typically available 2 h after full-time."""

FOOTYSTATS_DATA_LAG_P95_SECONDS: Final[int] = 3600
"""FootyStats match stats: typically available 1 h after full-time."""

API_FOOTBALL_RESULT_LAG_P95_SECONDS: Final[int] = 1800
"""API-Football result + stats endpoint: typically available 30 min after full-time."""

OPEN_METEO_HISTORICAL_LAG_SECONDS: Final[int] = 3600
"""Open-Meteo historical weather: hourly archive typically available 1 h after the hour."""

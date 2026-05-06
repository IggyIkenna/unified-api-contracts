"""Per-(asset_group, data_type) write-time `available_at` stamping rules.

SSOT for the semantic that determines a row's ``available_at`` column at
write-time. Per the workspace CLAUDE.md ``available_at`` rule:

> ``available_at`` is per-row, write-time, equal to live-pipeline-arrival
> (workspace-wide) — every shard's parquet contains an ``available_at``
> column. Each row's value = when the live pipeline would have actually
> had that row's information. NEVER derived at read-time.

Each :class:`AvailabilitySemantic` corresponds to a stamping helper in
``unified_trading_library.availability_stamping``; this module is the
[UAC] half of the layer split — it declares WHAT semantic applies for
each ``(asset_group, data_type)``, and UTL's stamping helpers implement
HOW to derive the timestamp from the source row.

Reference: writegate-honest-coverage plan Phase 1B + the historical-source-vs-live-pipeline
section of the workspace CLAUDE.md.
"""

from __future__ import annotations

from typing import Final, Literal

AvailabilitySemantic = Literal[
    "fetch_completed_at",
    "kickoff_minus_60min",
    "match_end_time",
    "event_time",
    "report_time",
    "announced_at",
    "forecast_issue_time",
    "publication_time",
    "tick_timestamp",
    "market_created_at",
]
"""The closed set of stamping semantics.

* ``fetch_completed_at`` — reference tables, instrument metadata, league rosters.
* ``kickoff_minus_60min`` — sports lineups (conservative; clip earlier leaks).
* ``match_end_time`` — post-match fixture stats, player stats, results, xG.
* ``event_time`` — fixture_events (per-row event timestamp).
* ``report_time`` — injuries (per-row report / occurrence timestamp).
* ``announced_at`` — fixtures (when the fixture itself was announced).
* ``forecast_issue_time`` — weather forecasts (issue time, NOT target time).
* ``publication_time`` — pre-match odds snapshots (per snapshot publication).
* ``tick_timestamp`` — CeFi / DeFi / TradFi market data; tick-time +
  source-priority scrape latency.
* ``market_created_at`` — prediction markets cannot have ticks before
  their listing time (lifecycle bound).
"""


# ---------------------------------------------------------------------------
# Per-(asset_group, data_type) registry.
# ---------------------------------------------------------------------------


AVAILABILITY_AT_SEMANTICS: Final[dict[tuple[str, str], AvailabilitySemantic]] = {
    # ---- Sports ----------------------------------------------------------
    ("sports", "FIXTURES"): "announced_at",
    ("sports", "FIXTURE_LINEUPS"): "kickoff_minus_60min",
    ("sports", "FIXTURE_EVENTS"): "event_time",
    ("sports", "INJURIES"): "report_time",
    ("sports", "FIXTURE_STATS"): "match_end_time",
    ("sports", "FIXTURE_PLAYER_STATS"): "match_end_time",
    ("sports", "RESULTS"): "match_end_time",
    ("sports", "UNDERSTAT_XG"): "match_end_time",
    ("sports", "SFI_PROGRESSIVE_STATS"): "match_end_time",
    ("sports", "ODDS_SNAPSHOT"): "publication_time",
    ("sports", "ODDS_MOVEMENT"): "publication_time",
    ("sports", "ARBITRAGE"): "publication_time",
    ("sports", "WEATHER_FORECAST"): "forecast_issue_time",
    # Sports reference tables.
    ("sports", "TEAMS"): "fetch_completed_at",
    ("sports", "PLAYERS"): "fetch_completed_at",
    ("sports", "VENUES"): "fetch_completed_at",
    ("sports", "LEAGUES"): "fetch_completed_at",
    ("sports", "PLAYER_VALUES"): "fetch_completed_at",
    # ---- CeFi -----------------------------------------------------------
    ("cefi", "trades"): "tick_timestamp",
    ("cefi", "ohlcv_1m"): "tick_timestamp",
    ("cefi", "ohlcv_15m"): "tick_timestamp",
    ("cefi", "book_snapshot"): "tick_timestamp",
    ("cefi", "liquidations"): "tick_timestamp",
    ("cefi", "options_chain"): "tick_timestamp",
    ("cefi", "futures_chain"): "tick_timestamp",
    ("cefi", "perpetual"): "tick_timestamp",
    ("cefi", "funding_rate"): "tick_timestamp",
    # ---- DeFi -----------------------------------------------------------
    ("defi", "swap"): "tick_timestamp",
    ("defi", "fx_rate"): "tick_timestamp",
    ("defi", "liquidity"): "tick_timestamp",
    ("defi", "market_state"): "tick_timestamp",
    ("defi", "gas_fees"): "tick_timestamp",
    ("defi", "lst_yields"): "tick_timestamp",
    ("defi", "vault_state"): "tick_timestamp",
    # ---- TradFi ---------------------------------------------------------
    ("tradfi", "trades"): "tick_timestamp",
    ("tradfi", "tbbo"): "tick_timestamp",
    ("tradfi", "ohlcv_1m"): "tick_timestamp",
    ("tradfi", "ohlcv_15m"): "tick_timestamp",
    ("tradfi", "options_chain"): "tick_timestamp",
    ("tradfi", "futures_chain"): "tick_timestamp",
    # ---- Prediction -----------------------------------------------------
    # Prediction CLOB ticks: tick_timestamp at write, but the orchestrator
    # ALSO clips by market_created_at upstream (no ticks before market
    # listing). The semantic here is the per-row stamp; lifecycle clipping
    # lives in instruments-service + MTDS pre-flight.
    ("prediction", "trades"): "tick_timestamp",
    ("prediction", "book_snapshot"): "tick_timestamp",
    ("prediction", "prediction_canonical_question_group"): "tick_timestamp",
    # MARKET_LIFECYCLE rows are written by instruments-service per
    # market_id (Polymarket conditionId / Kalshi ticker) and stamp the
    # available_at as ``market_created_at`` — we couldn't have known
    # about the market before it was listed. Predictions plan
    # ``predictions_canonical_question_group_polymarket_migration_2026_05_06.plan.md``
    # Phase 1A.
    ("prediction", "MARKET_LIFECYCLE"): "market_created_at",
    # ---- Reference data (asset-group-agnostic) --------------------------
    ("reference", "instruments"): "fetch_completed_at",
    ("reference", "venue_trading_calendar"): "fetch_completed_at",
}


def get_availability_semantic(asset_group: str, data_type: str) -> AvailabilitySemantic:
    """Return the ``available_at`` stamping semantic for a shard.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / ``prediction``
            / ``sports`` / ``reference``.
        data_type: Canonical data_type string.

    Returns:
        The ``AvailabilitySemantic`` literal for the pair.

    Raises:
        KeyError: If the pair is not registered. Failing loud is intentional
            — silent fallback to a default like ``fetch_completed_at`` would
            mask schema-drift bugs (a new data_type that callers forgot to
            register here gets wrong stamping). Adding a new data_type
            requires registering it here in the same change.
    """
    key = (asset_group, data_type)
    if key not in AVAILABILITY_AT_SEMANTICS:
        msg = (
            f"No availability_at semantic registered for "
            f"asset_group={asset_group!r}, data_type={data_type!r}. "
            "Register the pair in AVAILABILITY_AT_SEMANTICS before use."
        )
        raise KeyError(msg)
    return AVAILABILITY_AT_SEMANTICS[key]


def has_availability_semantic(asset_group: str, data_type: str) -> bool:
    """Check whether the pair is registered (non-raising membership test)."""
    return (asset_group, data_type) in AVAILABILITY_AT_SEMANTICS


__all__ = [
    "AVAILABILITY_AT_SEMANTICS",
    "AvailabilitySemantic",
    "get_availability_semantic",
    "has_availability_semantic",
]

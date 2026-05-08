"""Per-(asset_group, data_type) source priority registry.

SSOT for the ordered list of source keys that may serve a given
``(asset_group, data_type)``. The top entry is the primary — the source
whose emission time defines ``available_at`` for live and batch (per the
workspace ``Live = batch`` rule).

Per the workspace CLAUDE.md ``Live = batch — same data, same fields,
same timing semantics, different sources OK`` rule:

> Historical writes MUST be timestamped with the ``available_at`` we'd
> actually have in live mode (the ``SOURCE_PRIORITY`` top entry's
> emission time, NOT the canonical historical source's slower archive
> time).

Phase 1B seed: this module ships with **single-source seeds**
(top-of-list only). Multi-source merge logic and per-tier-tier-tier
priority tie-breakers are deferred to a follow-up plan
(``multi_source_priority_merge_2026_*<TBD>.md``) — flagged as a
documented temporary state per the workspace
``Temporary state must have a named successor plan`` rule.

Tie-breaker rules (when multiple sources are listed):

1. **Timestamp-availability** — sources that emit at live-time win over
   archive-only sources.
2. **Coverage** — sources with broader date / instrument coverage win.
3. **Information richness** — sources with more fields per row win.
4. **Merge-different-fields** — when two sources cover non-overlapping
   field sets, both stay in the list and consumers union.

The :data:`SOURCE_PRIORITY` registry below records the *single
authoritative source* for each pair today. When a second source becomes
available for the same pair, the writer-side merge logic must land
before the dict gets a multi-entry list (otherwise live=batch breaks).
"""

from __future__ import annotations

from typing import Final

SOURCE_PRIORITY: Final[dict[tuple[str, str], list[str]]] = {
    # ---- Sports ---------------------------------------------------------
    # Fixture lifecycle data — api_football is primary, footystats is the
    # multi-source merge candidate (deferred). Soccer-football-info handles
    # the SFI_PROGRESSIVE_STATS slice.
    ("sports", "FIXTURES"): ["api_football"],
    ("sports", "FIXTURE_LINEUPS"): ["api_football"],
    ("sports", "FIXTURE_EVENTS"): ["api_football"],
    ("sports", "FIXTURE_STATS"): ["api_football"],
    ("sports", "FIXTURE_PLAYER_STATS"): ["api_football"],
    ("sports", "INJURIES"): ["api_football"],
    ("sports", "RESULTS"): ["api_football"],
    ("sports", "UNDERSTAT_XG"): ["understat"],
    ("sports", "SFI_PROGRESSIVE_STATS"): ["soccer_football_info"],
    ("sports", "ODDS_SNAPSHOT"): ["odds_api"],
    ("sports", "ODDS_MOVEMENT"): ["odds_api"],
    ("sports", "ARBITRAGE"): ["odds_api"],
    ("sports", "WEATHER_FORECAST"): ["open_meteo"],
    # Sports reference tables.
    ("sports", "TEAMS"): ["api_football"],
    ("sports", "PLAYERS"): ["api_football"],
    ("sports", "VENUES"): ["api_football"],
    ("sports", "LEAGUES"): ["api_football"],
    ("sports", "PLAYER_VALUES"): ["transfermarkt"],
    # ---- CeFi -----------------------------------------------------------
    # Tardis is the canonical CeFi tick source (multi-venue archive).
    # Per-venue REST/WS adapters serve live-time updates; archive falls
    # back to Tardis.
    ("cefi", "trades"): ["tardis"],
    ("cefi", "ohlcv_1m"): ["tardis"],
    ("cefi", "ohlcv_15m"): ["tardis"],
    ("cefi", "book_snapshot"): ["tardis"],
    ("cefi", "liquidations"): ["tardis"],
    ("cefi", "options_chain"): ["tardis"],
    ("cefi", "futures_chain"): ["tardis"],
    ("cefi", "perpetual"): ["tardis"],
    ("cefi", "funding_rate"): ["tardis"],
    # ---- DeFi -----------------------------------------------------------
    # DeFi has per-protocol on-chain readers; no single canonical source.
    ("defi", "swap"): ["onchain_subgraph"],
    ("defi", "fx_rate"): ["onchain_subgraph"],
    ("defi", "liquidity"): ["onchain_subgraph"],
    ("defi", "market_state"): ["onchain_subgraph"],
    ("defi", "gas_fees"): ["onchain_rpc"],
    ("defi", "lst_yields"): ["onchain_subgraph"],
    ("defi", "vault_state"): ["onchain_subgraph"],
    # Phase 1A feature_dag seed gap closeout (2026-05-07): 5 on-chain DeFi
    # data_types declared in AVAILABILITY_AT_SEMANTICS but missing from
    # SOURCE_PRIORITY. Top-entry-only seeds per the Phase 1B convention
    # documented in this module's docstring; multi-source merge (e.g. The
    # Graph for AaveV3 + morpho_blue_api for Morpho on lending_indices)
    # is deferred to ``multi_source_priority_merge_2026_*<TBD>.md``.
    # `risk_params` reads protocol configurator state at the contract level
    # (Aave LendingPoolConfigurator, Morpho IRM params) → ``onchain_rpc``;
    # the other four are event-stream / index reads → ``onchain_subgraph``.
    ("defi", "lending_indices"): ["onchain_subgraph"],
    ("defi", "risk_params"): ["onchain_rpc"],
    ("defi", "rewards"): ["onchain_subgraph"],
    ("defi", "flash_loan_events"): ["onchain_subgraph"],
    ("defi", "eigenlayer_rewards"): ["onchain_subgraph"],
    # ---- TradFi ---------------------------------------------------------
    # Databento for CME/NQ/options/futures; Yahoo for VIX 15m rolling
    # window; Barchart for VIX 15m historical preload (handled at the
    # MTDS routing layer, not here — both are listed for the same shard
    # but the orchestrator picks by date).
    ("tradfi", "trades"): ["databento"],
    ("tradfi", "tbbo"): ["databento"],
    ("tradfi", "ohlcv_1m"): ["databento"],
    ("tradfi", "ohlcv_15m"): ["databento"],  # VIX uses Yahoo; orchestrator routes by date
    ("tradfi", "options_chain"): ["databento"],
    ("tradfi", "futures_chain"): ["databento"],
    # ---- Prediction -----------------------------------------------------
    ("prediction", "trades"): ["polymarket_clob"],
    ("prediction", "book_snapshot"): ["polymarket_clob"],
    ("prediction", "prediction_canonical_question_group"): ["polymarket_clob"],
    # MARKET_LIFECYCLE source — instruments-service reads from Polymarket
    # gamma API ``/markets/{conditionId}`` for created/resolution/settlement
    # timestamps. Phase 1B writes top entry only; Kalshi metadata source is
    # a deferred follow-up plan slot. Predictions plan
    # ``predictions_canonical_question_group_polymarket_migration_2026_05_06.md``
    # Phase 1A.
    ("prediction", "MARKET_LIFECYCLE"): ["polymarket_gamma_api"],
    # ---- Reference (asset-group-agnostic) -------------------------------
    ("reference", "instruments"): ["instruments_service"],
    ("reference", "venue_trading_calendar"): ["instruments_service"],
}


def get_source_priority(asset_group: str, data_type: str) -> list[str]:
    """Return the ordered source list for a ``(asset_group, data_type)`` pair.

    Returns a copy so callers cannot mutate the registry.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / ``prediction``
            / ``sports`` / ``reference``.
        data_type: Canonical data_type string.

    Returns:
        Ordered list of source keys. Top entry is primary (the
        live-time-winning source).

    Raises:
        KeyError: If the pair is not registered. Failing loud is intentional
            — silent fallback would mask schema-drift bugs.
    """
    key = (asset_group, data_type)
    if key not in SOURCE_PRIORITY:
        msg = (
            f"No source priority registered for "
            f"asset_group={asset_group!r}, data_type={data_type!r}. "
            "Register the pair in SOURCE_PRIORITY before use."
        )
        raise KeyError(msg)
    return list(SOURCE_PRIORITY[key])


def get_primary_source(asset_group: str, data_type: str) -> str:
    """Return the primary (top-of-list) source key for a pair.

    Convenience for callers that don't need the full list — most stamping
    helpers just need the live-time source name to compute available_at.
    """
    return get_source_priority(asset_group, data_type)[0]


def has_source_priority(asset_group: str, data_type: str) -> bool:
    """Check whether the pair is registered (non-raising membership test)."""
    return (asset_group, data_type) in SOURCE_PRIORITY


__all__ = [
    "SOURCE_PRIORITY",
    "get_primary_source",
    "get_source_priority",
    "has_source_priority",
]

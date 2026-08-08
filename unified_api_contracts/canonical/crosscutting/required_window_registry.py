"""Required-window registry per (asset_group, data_type) for the smoke harness.

Companion contract to
:mod:`unified_api_contracts.canonical.crosscutting.shard_coverage_classification`.
That module classifies a shard against a `RequiredWindow`; THIS module
provides the **declarative SSOT** for "what `RequiredWindow` does each
`(asset_group, data_type)` need?" so the harness can resolve a window per
shard atom at smoke time without magic numbers in the harness code.

Three product-shaped kinds (mirror of :data:`RequiredWindowKind`):

* ``seasonal_continuous`` — sports / per-(``league_id``, ``season_year``).
  Boundaries come from the live UAC sports league registry via
  :func:`unified_api_contracts.canonical.domain.sports.season_dates.get_season_boundary`
  — NEVER from hand-rolled date arithmetic in the harness.

* ``max_daily_aggregation`` — data_types whose downstream consumer only
  aggregates WITHIN a day (e.g. ``ohlcv_24h`` derived from intraday ticks).
  One calendar day is sufficient to exercise the path end-to-end.

* ``lookback_n`` — everything else: an integer ``lookback_calendar_days``
  conservatively bounded by the longest feature lookback that consumes the
  shard. Provenance (``driver_feature_family``,
  ``driver_lookback_periods``, ``driver_coarsest_timeframe``) is recorded
  alongside the integer so the registry stays auditable — when the
  feature config evolves the integer is updated in lock-step with the
  driver fields, never in isolation. The integer answers
  ``calendar_days = lookback_periods * coarsest_timeframe_in_days``
  rounded up to the next trading-day-equivalent (e.g. a 200-period 24h
  feature on a venue with weekend trading → 200 cal days; on a venue with
  M-F trading only → ~290 cal days for the same 200 trading-day lookback).

Plan: ``plans/active/honest_coverage_smoke_harness_2026_06_28.md`` —
DESIGN P1 todo #2 (this registry).
Codex SSOT: ``codex/02-data/shard-coverage-classification.md`` §
"Required-window is product-shaped".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Final, Literal

from unified_api_contracts.canonical.crosscutting.shard_coverage_classification import (
    RequiredWindow,
    RequiredWindowKind,
)
from unified_api_contracts.canonical.domain.sports.season_dates import (
    SeasonBoundary,
    get_season_boundary,
)

# ---------------------------------------------------------------------------
# RequiredWindowSpec — declarative per-(AG, data_type) entry.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RequiredWindowSpec:
    """Declarative spec for the required window of one (AG, data_type).

    The registry is the SSOT — :func:`resolve_required_window` reads it +
    the harness call-site context (``today`` / ``league_id`` /
    ``season_year``) to materialise the concrete :class:`RequiredWindow`.
    Adding a new MVP data_type = adding an entry here AND covering it in
    :data:`MVP_REQUIRED_WINDOW_REGISTRY`'s unit test.
    """

    kind: RequiredWindowKind
    """Which of the three product-shaped families this (AG, data_type) belongs to."""

    lookback_calendar_days: int = 0
    """For ``lookback_n``: inclusive calendar-day window (``today - N + 1
    .. today``). Zero for the other two kinds. The integer is conservatively
    chosen to satisfy the longest feature lookback that consumes the shard —
    see ``driver_*`` fields for the provenance trail."""

    driver_feature_family: str = ""
    """Provenance: the feature family whose lookback DRIVES this window
    (``volatility_rolling_24h_200p``, ``carry_funding_30d``, …). Empty for
    seasonal / max-daily entries where the driver is the path topology, not a
    feature lookback."""

    driver_lookback_periods: int = 0
    """Provenance: ``lookback_periods`` of the driver feature
    (e.g. 200 for a 200-period rolling feature). Zero for seasonal / max-daily."""

    driver_coarsest_timeframe: str = ""
    """Provenance: the coarsest timeframe the driver feature samples at
    (``24h`` / ``1h`` / ``15m`` / ``1m`` / ``15s`` / ``tick``). Empty for
    seasonal / max-daily."""

    notes: str = ""
    """Human-readable context for the entry — e.g. ``"DERIBIT options_chain
    bundle: derivative_ticker IV consumers use a 90d 1h base"``. Always
    relates the (AG, data_type) to the harness's expectations."""

    def __post_init__(self) -> None:
        if self.kind == "lookback_n":
            if self.lookback_calendar_days < 1:
                raise ValueError(
                    f"RequiredWindowSpec(kind=lookback_n) requires "
                    f"lookback_calendar_days >= 1 (got {self.lookback_calendar_days}); "
                    "driver provenance must yield a positive integer.",
                )
        else:
            if self.lookback_calendar_days != 0:
                raise ValueError(
                    f"RequiredWindowSpec(kind={self.kind}) must NOT carry "
                    f"lookback_calendar_days (got {self.lookback_calendar_days}) "
                    "— the integer is only meaningful for lookback_n.",
                )


# ---------------------------------------------------------------------------
# The registry — per-(asset_group, data_type) → RequiredWindowSpec.
#
# Each entry is the conservative window the smoke harness should exercise.
# The numbers are sourced from the audit-derived table in
# ``plans/active/honest_coverage_smoke_harness_2026_06_28.md`` § Representative
# smoke matrix (the per-AG min-window column, 2026-06-28 audit), which
# itself derived them from the features-service feature configs that
# consume each shard. The IMPLEMENT P1 todo wires the registry into the
# smoke runner; future feature-config additions update the driver_* fields
# + lookback_calendar_days in lock-step (review-blocking if one moves
# without the other).
# ---------------------------------------------------------------------------


_CEFI_LONG_LOOKBACK_NOTE: Final[str] = (
    "Carry / vol-regime / cross-instrument features rolling at 24h x 200p "
    "consume this shard; ~200 cal days satisfies on 24/7 venues."
)
_CEFI_SHORT_LOOKBACK_NOTE: Final[str] = (
    "Intraday execution / microstructure feature families (1m x 60p, "
    "15s x 100p) — 30d window is the conservative bound for the longest."
)


MVP_REQUIRED_WINDOW_REGISTRY: Final[dict[tuple[str, str], RequiredWindowSpec]] = {
    # -----------------------------------------------------------------
    # CeFi MVP data_types — per the plan's CeFi representative table.
    # All CeFi venues are 24/7 → lookback in calendar days == lookback in
    # trading days. driver_* fields name the feature family that pins the
    # 200-period 24h lookback (the longest in features-service today).
    # -----------------------------------------------------------------
    ("cefi", "trades"): RequiredWindowSpec(
        kind="lookback_n",
        lookback_calendar_days=200,
        driver_feature_family="cefi_vol_regime_24h_200p",
        driver_lookback_periods=200,
        driver_coarsest_timeframe="24h",
        notes=_CEFI_LONG_LOOKBACK_NOTE,
    ),
    ("cefi", "book_snapshot_5"): RequiredWindowSpec(
        kind="lookback_n",
        lookback_calendar_days=30,
        driver_feature_family="cefi_microstructure_1m_60p",
        driver_lookback_periods=60,
        driver_coarsest_timeframe="1m",
        notes=_CEFI_SHORT_LOOKBACK_NOTE,
    ),
    ("cefi", "derivative_ticker"): RequiredWindowSpec(
        kind="lookback_n",
        lookback_calendar_days=200,
        driver_feature_family="cefi_carry_funding_24h_200p",
        driver_lookback_periods=200,
        driver_coarsest_timeframe="24h",
        notes="Funding-rate carry features need ~200d to span the regimes.",
    ),
    ("cefi", "options_chain"): RequiredWindowSpec(
        kind="lookback_n",
        lookback_calendar_days=90,
        driver_feature_family="cefi_options_iv_term_1h_2160p",
        driver_lookback_periods=2160,  # 90 days x 24 hours
        driver_coarsest_timeframe="1h",
        notes="DERIBIT options_chain bundle: IV term-structure / skew features at 1h grain x 90d.",
    ),
    ("cefi", "futures_chain"): RequiredWindowSpec(
        kind="lookback_n",
        lookback_calendar_days=90,
        driver_feature_family="cefi_futures_basis_1h_2160p",
        driver_lookback_periods=2160,
        driver_coarsest_timeframe="1h",
        notes="DERIBIT/OKX futures_chain bundle: basis / term-structure features at 1h x 90d.",
    ),
    # -----------------------------------------------------------------
    # DeFi MVP data_types — short windows (snapshots are state-at-instant;
    # swaps fan out to feature aggregations at intraday and daily grain).
    # All chains are 24/7.
    # -----------------------------------------------------------------
    ("defi", "dex_pool_swaps"): RequiredWindowSpec(
        kind="lookback_n",
        lookback_calendar_days=90,
        driver_feature_family="defi_pool_volume_1h_2160p",
        driver_lookback_periods=2160,
        driver_coarsest_timeframe="1h",
        notes="Uniswap V3 pool swap features at 1h x 90d (the audit's conservative window).",
    ),
    ("defi", "dex_pool_state"): RequiredWindowSpec(
        kind="max_daily_aggregation",
        notes="Pool state snapshot — TVL / fee tier / liquidity at the date. Path consumes 1 day.",
    ),
    ("defi", "lending_indices"): RequiredWindowSpec(
        kind="lookback_n",
        lookback_calendar_days=30,
        driver_feature_family="defi_lending_apy_24h_30p",
        driver_lookback_periods=30,
        driver_coarsest_timeframe="24h",
        notes="Aave V3 lending APY features at 24h x 30d.",
    ),
    ("defi", "lst_rates"): RequiredWindowSpec(
        kind="lookback_n",
        lookback_calendar_days=30,
        driver_feature_family="defi_lst_yield_24h_30p",
        driver_lookback_periods=30,
        driver_coarsest_timeframe="24h",
        notes="Lido stETH/wstETH rate features at 24h x 30d.",
    ),
    ("defi", "oracle_prices"): RequiredWindowSpec(
        kind="lookback_n",
        lookback_calendar_days=30,
        driver_feature_family="defi_oracle_basis_1h_720p",
        driver_lookback_periods=720,
        driver_coarsest_timeframe="1h",
        notes="Pyth / Chainlink oracle-basis features at 1h x 30d.",
    ),
    ("defi", "perp_funding"): RequiredWindowSpec(
        kind="lookback_n",
        lookback_calendar_days=90,
        driver_feature_family="defi_perp_funding_carry_24h_90p",
        driver_lookback_periods=90,
        driver_coarsest_timeframe="24h",
        notes="On-chain DeFi perp funding rate carry features at 24h x 90d.",
    ),
    # -----------------------------------------------------------------
    # TradFi MVP data_types — Databento ohlcv_1m base. M-F trading +
    # holidays mean 200 trading days ≈ 290 calendar days (per the audit
    # table). EXPECTED_HOLIDAY / EXPECTED_WEEKEND cells inside the window
    # are within-window empties (legitimate) per the classifier's
    # decision table.
    # -----------------------------------------------------------------
    ("tradfi", "ohlcv_1m"): RequiredWindowSpec(
        kind="lookback_n",
        lookback_calendar_days=290,
        driver_feature_family="tradfi_vol_regime_24h_200p",
        driver_lookback_periods=200,
        driver_coarsest_timeframe="24h",
        notes="~290 calendar days envelops 200 trading days on M-F venues (CME / NYSE / NASDAQ / CBOE).",
    ),
    ("tradfi", "ohlcv_24h"): RequiredWindowSpec(
        kind="max_daily_aggregation",
        notes="Daily bar — the path aggregates within a single trading day from intraday source.",
    ),
    # -----------------------------------------------------------------
    # Sports MVP data_types — per-(league_id, season_year) seasonal
    # continuous. resolve_required_window pulls real boundaries from the
    # league registry via get_season_boundary. Magic numbers FORBIDDEN —
    # the registry call IS the SSOT (no per-league date literals here).
    # -----------------------------------------------------------------
    ("sports", "fixtures"): RequiredWindowSpec(
        kind="seasonal_continuous",
        notes="API-Football fixtures by (league, season) — schedule data spans the season window.",
    ),
    ("sports", "xg"): RequiredWindowSpec(
        kind="seasonal_continuous",
        notes="Understat xG by (league, season) — match-level xG joined to fixtures.",
    ),
    ("sports", "odds"): RequiredWindowSpec(
        kind="seasonal_continuous",
        notes="Odds-API match-odds by (league, season) — fixture-pinned, full-season coverage.",
    ),
    ("sports", "MATCH_STATS"): RequiredWindowSpec(
        kind="seasonal_continuous",
        notes="footystats per-match stats by (league, season).",
    ),
    # -----------------------------------------------------------------
    # Prediction MVP data_types — per-instrument lifecycle windows
    # (created → resolved → settled). The plan calls out "one full market
    # lifecycle" which spans hours-to-months depending on the contract.
    # We treat the lifecycle as a lookback_n window bounded by 30d at the
    # ceiling (longest live market in the MVP audit set); per-instrument
    # callers can pass a tighter window via the wrapper at smoke time.
    # -----------------------------------------------------------------
    ("prediction", "trades"): RequiredWindowSpec(
        kind="lookback_n",
        lookback_calendar_days=30,
        driver_feature_family="prediction_trade_flow_15m_2880p",
        driver_lookback_periods=2880,
        driver_coarsest_timeframe="15m",
        notes="Polymarket / Kalshi trades. 30d ceiling envelops the MVP audit set's longest market lifecycle.",
    ),
    ("prediction", "book_snapshot_5"): RequiredWindowSpec(
        kind="lookback_n",
        lookback_calendar_days=30,
        driver_feature_family="prediction_orderbook_1m_43200p",
        driver_lookback_periods=43200,
        driver_coarsest_timeframe="1m",
        notes="Polymarket / Kalshi book_snapshot_5. Lifecycle window sister of trades.",
    ),
    ("prediction", "market_lifecycle"): RequiredWindowSpec(
        kind="max_daily_aggregation",
        notes="market_lifecycle is a per-day state row (open / resolved / settled). 1 day exercises the path.",
    ),
    ("prediction", "canonical_question_group"): RequiredWindowSpec(
        kind="max_daily_aggregation",
        notes="CQG bundled refdata per day — 1 day exercises the bundle-cluster validator.",
    ),
}
"""Per-(asset_group, data_type) required-window specs for the smoke harness.

Covers all 5 asset groups' MVP data_types per the audit-derived table in
``plans/active/honest_coverage_smoke_harness_2026_06_28.md``. Adding a new
MVP data_type = adding an entry here AND extending
``tests/unit/test_required_window_registry.py``'s
``test_registry_covers_all_mvp_data_types`` assertion (kept additive — the
test enumerates the registry).
"""


# ---------------------------------------------------------------------------
# Resolver — registry + call-site context → concrete RequiredWindow.
# ---------------------------------------------------------------------------


class UnknownRequiredWindowError(KeyError):
    """Raised when ``(asset_group, data_type)`` has no registry entry.

    The smoke harness MUST fail-loudly on an un-classified shard: the
    plan's IMPLEMENT P1 gate is ``no combo silently skipped (un-classified
    = hard error)``. This exception is that hard error.
    """


def resolve_required_window(
    *,
    asset_group: str,
    data_type: str,
    today: date,
    league_id: str | None = None,
    season_year: int | None = None,
) -> RequiredWindow:
    """Materialise the concrete :class:`RequiredWindow` for a smoke shard.

    Reads :data:`MVP_REQUIRED_WINDOW_REGISTRY` for the (AG, data_type)
    spec and composes it with the call-site context:

    * ``seasonal_continuous`` → REQUIRES ``league_id`` + ``season_year``.
      Boundaries come from
      :func:`unified_api_contracts.canonical.domain.sports.season_dates.get_season_boundary`
      — the harness MUST NOT compute season dates inline.
    * ``max_daily_aggregation`` → window is ``[today, today]``.
    * ``lookback_n`` → window is
      ``[today - (lookback_calendar_days - 1), today]`` inclusive.

    Args:
        asset_group:  One of ``cefi`` / ``defi`` / ``tradfi`` / ``sports`` /
                      ``prediction``.
        data_type:    Writer-grain data_type (must match a registry key).
        today:        Anchor date (UTC) — the right edge of the window for
                      non-seasonal kinds.
        league_id:    Sports league id (required for ``seasonal_continuous``).
        season_year:  Sports season year — the year the season STARTS, per
                      :func:`get_season_boundary`'s convention (e.g. 2025 for
                      the 2025-26 EPL season). Required for
                      ``seasonal_continuous``.

    Raises:
        UnknownRequiredWindowError: ``(asset_group, data_type)`` not in
            the registry.
        ValueError: ``seasonal_continuous`` requested without
            ``league_id`` + ``season_year``.
    """
    key = (asset_group, data_type)
    spec = MVP_REQUIRED_WINDOW_REGISTRY.get(key)
    if spec is None:
        raise UnknownRequiredWindowError(
            f"No required-window spec registered for {key!r}; add a "
            f"RequiredWindowSpec entry to MVP_REQUIRED_WINDOW_REGISTRY "
            "(every MVP data_type must be classified — un-classified = hard error "
            "per plans/active/honest_coverage_smoke_harness_2026_06_28.md "
            "IMPLEMENT P1 gate).",
        )
    if spec.kind == "seasonal_continuous":
        if league_id is None or season_year is None:
            raise ValueError(
                f"resolve_required_window({key!r}) is seasonal_continuous; "
                "league_id + season_year are required arguments "
                "(seasonal boundaries come from the sports league registry, never "
                "magic numbers in the caller).",
            )
        boundary: SeasonBoundary = get_season_boundary(league_id, season_year)
        # Clip to today during an active season: future dates have no manifest
        # rows and would count as M(missing) → INSUFFICIENT_HISTORY. Post-season
        # behaviour is unchanged (min returns season_end when today ≥ season_end).
        return RequiredWindow(
            start=boundary.start_date,
            end=min(boundary.end_date, today),
            kind="seasonal_continuous",
        )
    if spec.kind == "max_daily_aggregation":
        return RequiredWindow(start=today, end=today, kind="max_daily_aggregation")
    # spec.kind == "lookback_n" — validated by RequiredWindowSpec.__post_init__.
    span = spec.lookback_calendar_days
    return RequiredWindow(
        start=today - timedelta(days=span - 1),
        end=today,
        kind="lookback_n",
    )


# ---------------------------------------------------------------------------
# MVP coverage exhaustiveness — drives the unit-test assertion that every
# MVP (AG, data_type) of the harness universe has a registry entry.
# ---------------------------------------------------------------------------


MVP_ASSET_GROUPS: Final[tuple[Literal["cefi", "defi", "tradfi", "sports", "prediction"], ...]] = (
    "cefi",
    "defi",
    "tradfi",
    "sports",
    "prediction",
)
"""The five asset groups the smoke harness iterates."""


def registered_data_types_for_asset_group(asset_group: str) -> frozenset[str]:
    """Set of registered ``data_type`` strings for one ``asset_group``.

    Used by the harness's "no combo silently skipped" gate — the harness
    iterates this set per AG and routes each through
    :func:`resolve_required_window` (so a missing entry raises
    :class:`UnknownRequiredWindowError` instead of silently dropping a
    data_type).
    """
    return frozenset(dt for (ag, dt) in MVP_REQUIRED_WINDOW_REGISTRY if ag == asset_group)


__all__ = [
    "MVP_ASSET_GROUPS",
    "MVP_REQUIRED_WINDOW_REGISTRY",
    "RequiredWindowSpec",
    "UnknownRequiredWindowError",
    "registered_data_types_for_asset_group",
    "resolve_required_window",
]

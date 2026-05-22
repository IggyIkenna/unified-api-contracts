"""Operator-expected coverage policy + deterministic availability oracle (SSOT).

This module holds two related-but-distinct contracts:

1. **Scope policy** (`EXPECTED_COVERAGE_BY_ASSET_GROUP`, `is_expected`,
   `get_expected_*`, `get_source_coverage_start_for_data_type`,
   `is_before_source_coverage_start`): declares which
   (asset_group, venue, data_type) tuples we *intend* to keep filled +
   per-(venue, data_type) coverage-start lookups. Powers the four-state
   data-status view in deployment-ui.

2. **Availability oracle** (`expected_coverage`, `ExpectedCoverageResult`,
   `ExpectedState`): deterministic per-(asset_group, source, data_type,
   date) answer to "should this cell have data?". Composes the scope
   policy with venue/chain launch dates, SourceCapability.coverage_start
   per data_type, and trading-calendar gap data already encoded in UAC
   (`venue_launch_dates`, `chain_env`, `venue_trading_calendar`,
   `half_day_sessions`). Output mirrors the `EmptyConfirmedReason`
   taxonomy so divergence between expected + actual manifest state can
   be classified deterministically. Mega-audit Phase A2 deliverable
   (`plans/active/issues/mega_audit_and_plan_beefup_progression_2026_05_20.md`).

Both contracts live here per operator directive 2026-05-20 — single SSOT,
single module to consult for "is this cell expected to have data".

## Scope-policy section

Phase 1 of the unified-data-status work — declares the subset of
(asset_group, venue, data_type) tuples we *intend* to keep filled.
Sister registry to :mod:`processed_data_dependencies`; together they
power the four-state data-status view in deployment-ui:

    captured       — manifest row has ``capture_status='captured'``.
    missing        — in-policy, raw shard captured (or this IS raw),
                     but the expected shard is absent. Actionable.
    blocked_on_raw — processed shard absent because the underlying raw
                     shard is absent. Fix raw first; this is derived.
    out_of_scope   — venue x data_type not in EXPECTED_COVERAGE for the
                     active asset_group. Excluded from the denominator;
                     rendered gray (or hidden) in the UI.

Distinction from :data:`VENUE_DATA_TYPE_CAPABILITIES`:

    capability — what a venue *could* emit (declared in
                 ``market_data_categories.py``). Used by adapters to
                 know what calls are valid.
    expected   — what we *plan* to fill (this file). Used by the data-
                 status denominator and by gap-fill launchers to know
                 what to chase.

Operator overrides via UI filter chips overlay on top of this policy
at request time — narrowing the denominator further but never
expanding it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as _date
from enum import StrEnum

from unified_api_contracts.registry.capability import (
    CapabilityResolutionError,
    SourceCapability,
    resolve_capability,
)

# ---------------------------------------------------------------------------
# CeFi — full Tardis sharded backfill coverage (9 venues x 6 data types).
# All venues capable of every data_type are expected to fill it. Deribit gets
# the full options/futures chain bulk; HYPERLIQUID/ASTER are perp-only.
# ---------------------------------------------------------------------------
_CEFI: dict[str, list[str]] = {
    "BINANCE-SPOT": ["trades", "book_snapshot_5"],
    "BINANCE-FUTURES": [
        "trades",
        "book_snapshot_5",
        "derivative_ticker",
        "liquidations",
        "futures_chain",
    ],
    "BYBIT": [
        "trades",
        "book_snapshot_5",
        "derivative_ticker",
        "liquidations",
        "futures_chain",
    ],
    "OKX": ["trades", "book_snapshot_5", "derivative_ticker", "liquidations"],
    "DERIBIT": [
        "trades",
        "book_snapshot_5",
        "derivative_ticker",
        "liquidations",
        "options_chain",
        "futures_chain",
    ],
    "UPBIT": ["trades", "book_snapshot_5"],
    "COINBASE": ["trades", "book_snapshot_5"],
    "HYPERLIQUID": [
        "trades",
        "book_snapshot_5",
        "derivative_ticker",
        "liquidations",
    ],
    "ASTER": [
        "trades",
        "book_snapshot_5",
        "derivative_ticker",
        "liquidations",
    ],
}

# ---------------------------------------------------------------------------
# TradFi — operator-confirmed scope (2026-04-28). CME / ICE futures get
# trades + ohlcv_1m + tbbo via Databento. CBOE provides VIX 15m. FX +
# YAHOO_FINANCE for daily rates / VIX rolling.
#
# DELIBERATELY OMITTED: NASDAQ, NYSE, BARCHART. They are declared in
# ``VENUE_DATA_TYPE_CAPABILITIES`` (capable of trades/ohlcv_1m/tbbo) but
# are NOT in scope today — the operator confirmed "what we have is
# enough for now"; OPRA / per-symbol US-equity tick is cost-prohibitive.
# An operator can opt them back in via the UI filter chips at any time
# without editing this policy.
# ---------------------------------------------------------------------------
_TRADFI: dict[str, list[str]] = {
    "CME": ["trades", "ohlcv_1m", "tbbo"],
    "ICE": ["trades", "ohlcv_1m", "tbbo"],
    "CBOE": ["ohlcv_15m"],
    # NASDAQ + NYSE equity venues added 2026-05-17 per OHLCV-only MVP scope
    # (operator direction 2026-05-15 — see
    # plans/active/tradfi_ohlcv_only_mvp_backfill_2026_05_15.md). Phase 7
    # backfill captured 33,672 NASDAQ + 122,494 NYSE ohlcv_1m rows from
    # 2023-04-15+ via Databento XNAS.ITCH + XNYS.PILLAR. Before this entry
    # the venues were silently out_of_scope in the data-status denominator.
    "NASDAQ": ["ohlcv_1m"],
    "NYSE": ["ohlcv_1m"],
    "FX": ["ohlcv_24h"],
    "YAHOO_FINANCE": ["ohlcv_15m", "ohlcv_24h"],
}

# ---------------------------------------------------------------------------
# DeFi — Phase 1 expansion (2026-04-24). Scope set declares the data types
# each protocol-chain composite is expected to fill. Pass-through types
# (lending_indices, perp_funding, oracle_prices, gas_fees, rewards, …) live
# alongside candle-built types (dex_swaps, dex_pools).
#
# Per protocol family:
#   DEXes   → dex_pools, dex_swaps
#   Lending → lending_indices, liquidation_events, position_data
#             (+ flash_loan_events on Aave V3 only)
#   LST     → lst_rates, staking_yields
#   Cross-chain   → bridge_events, token_transfers (selective)
#   Oracle / gas  → oracle_prices, gas_fees (chain-level)
# ---------------------------------------------------------------------------
_DEFI_DEX_PAIRS: list[str] = ["dex_pools", "dex_swaps"]
_DEFI_LENDING_PAIRS: list[str] = [
    "lending_indices",
    "liquidation_events",
    "position_data",
    "risk_params",
]
_DEFI_LENDING_AAVE_PAIRS: list[str] = [*_DEFI_LENDING_PAIRS, "flash_loan_events"]
_DEFI_LST_PAIRS: list[str] = ["lst_rates", "staking_yields"]

_DEFI: dict[str, list[str]] = {
    # --- DEX protocols ---
    "UNISWAPV2-ETHEREUM": list(_DEFI_DEX_PAIRS),
    "UNISWAPV3-ETHEREUM": list(_DEFI_DEX_PAIRS),
    "UNISWAPV3-ARBITRUM": list(_DEFI_DEX_PAIRS),
    "UNISWAPV3-BASE": list(_DEFI_DEX_PAIRS),
    "UNISWAPV3-OPTIMISM": list(_DEFI_DEX_PAIRS),
    "UNISWAPV3-POLYGON": list(_DEFI_DEX_PAIRS),
    "UNISWAPV4-ETHEREUM": list(_DEFI_DEX_PAIRS),
    "CURVE-ETHEREUM": list(_DEFI_DEX_PAIRS),
    "CURVE-AVALANCHE": list(_DEFI_DEX_PAIRS),
    "CURVE-OPTIMISM": list(_DEFI_DEX_PAIRS),
    "BALANCER-ETHEREUM": list(_DEFI_DEX_PAIRS),
    "BALANCER-ARBITRUM": list(_DEFI_DEX_PAIRS),
    "BALANCER-AVALANCHE": list(_DEFI_DEX_PAIRS),
    "BALANCER-BASE": list(_DEFI_DEX_PAIRS),
    "BALANCER-OPTIMISM": list(_DEFI_DEX_PAIRS),
    "BALANCER-POLYGON": list(_DEFI_DEX_PAIRS),
    # --- Lending protocols ---
    "AAVEV3-ETHEREUM": list(_DEFI_LENDING_AAVE_PAIRS),
    "AAVEV3-ARBITRUM": list(_DEFI_LENDING_AAVE_PAIRS),
    "AAVEV3-AVALANCHE": list(_DEFI_LENDING_AAVE_PAIRS),
    "AAVEV3-BASE": list(_DEFI_LENDING_AAVE_PAIRS),
    "AAVEV3-BSC": list(_DEFI_LENDING_AAVE_PAIRS),
    "AAVEV3-LINEA": list(_DEFI_LENDING_AAVE_PAIRS),
    "AAVEV3-OPTIMISM": list(_DEFI_LENDING_AAVE_PAIRS),
    "AAVEV3-POLYGON": list(_DEFI_LENDING_AAVE_PAIRS),
    "COMPOUNDV3-ETHEREUM": list(_DEFI_LENDING_PAIRS),
    "COMPOUNDV3-ARBITRUM": list(_DEFI_LENDING_PAIRS),
    "COMPOUNDV3-BASE": list(_DEFI_LENDING_PAIRS),
    "COMPOUNDV3-OPTIMISM": list(_DEFI_LENDING_PAIRS),
    "COMPOUNDV3-POLYGON": list(_DEFI_LENDING_PAIRS),
    "MORPHO-ETHEREUM": list(_DEFI_LENDING_PAIRS),
    "MORPHO-ARBITRUM": list(_DEFI_LENDING_PAIRS),
    "MORPHO-BASE": list(_DEFI_LENDING_PAIRS),
    "MORPHO-OPTIMISM": list(_DEFI_LENDING_PAIRS),
    "MORPHO-POLYGON": list(_DEFI_LENDING_PAIRS),
    "FLUID-ETHEREUM": list(_DEFI_LENDING_PAIRS),
    # --- LST / yield ---
    "LIDO-ETHEREUM": list(_DEFI_LST_PAIRS),
    "ETHERFI-ETHEREUM": [*_DEFI_LST_PAIRS, "eigenlayer_rewards"],
    "ETHENA-ETHEREUM": list(_DEFI_LST_PAIRS),
    "JITO-SOLANA": list(_DEFI_LST_PAIRS),
    # --- Oracle / gas / token infra (provider-level, chain is a separate shard dim) ---
    # "venue" here means data-source provider, not exchange. These are RPC
    # providers / oracle protocols — conceptually data_source_type=ORACLE|RPC_PROVIDER.
    # All were missing from initial registration; manifest rows exist but were
    # invisible to data-status denominator. Batch-added 2026-05-22.
    "ALCHEMY": ["gas_fees", "token_transfers"],
    "CHAINLINK": ["oracle_prices"],
    "PYTH": ["oracle_prices"],
    # --- Perp funding (DeFi perpetual protocols) ---
    # perp_funding_handler DEFAULT_PROTOCOLS; venue is protocol-only (chain in shard dim).
    "HYPERLIQUID": ["perp_funding"],
    "ASTER": ["perp_funding"],
    "GMX": ["perp_funding"],
    "PACIFICA-SOLANA": ["perp_funding"],
    "LIGHTER-ZKSYNC": ["perp_funding"],
    # --- Bridge protocols ---
    # bridge_events_handler _BRIDGE_PROTOCOLS = ["ACROSS", "STARGATE"]
    "ACROSS": ["bridge_events"],
    "STARGATE": ["bridge_events"],
    # --- MEV / block-builder data ---
    # mev_events_handler _VENUE = "FLASHBOTS"
    "FLASHBOTS": ["mev_events"],
    # --- Governance (on-chain votes, protocol-level, EVM) ---
    # governance_events_handler _GOVERNANCE_PROTOCOLS = ["COMPOUND", "AAVE", "UNISWAP"]
    # Note: governance_proposals uses same protocols but data_type "governance_proposals"
    # is not yet in the defi capability set — deferred to handler/capability alignment plan.
    "COMPOUND": ["governance_events"],
    "AAVE": ["governance_events"],
    "UNISWAP": ["governance_events"],
    # --- EigenLayer restaking rewards (separate from ETHERFI LST restaking) ---
    # eigenlayer_rewards_handler venue="EIGENLAYER"
    "EIGENLAYER": ["eigenlayer_rewards"],
    # --- Deferred (handler→capability venue naming inconsistency) ---
    # native_staking_rates (SOLANA-NATIVE-SOLANA) + vault_share_price (YEARNV3/MAKER/
    # FRAX/MORPHOVAULTS/ETHENA) + governance_proposals (COMPOUND/AAVE/UNISWAP) have
    # capabilities dict entries using VENUE-CHAIN format while handlers emit bare VENUE.
    # These 3 data_type families are NOT yet in DATA_TYPES_BY_ASSET_GROUP["defi"].
    # Tracked: plans/active/issues/defi_coverage_capability_alignment_2026_05_22.md
}

# ---------------------------------------------------------------------------
# Sports — ODDS_API is the raw odds source; per-bookmaker venues emit
# point-in-time odds_snapshot + odds_movement for cross-feed validation.
#
# DELIBERATELY OMITTED on capability rows: arbitrage_opportunity. It is a
# purely-derived MDPS output (cross-bookmaker disparity) — not emitted by
# any venue. Lives in :mod:`processed_data_dependencies` instead.
# ---------------------------------------------------------------------------
_SPORTS: dict[str, list[str]] = {
    "ODDS_API": ["odds"],
    "PINNACLE": ["odds_snapshot", "odds_movement"],
    "BETFAIR": ["odds_snapshot", "odds_movement"],
    "DRAFTKINGS": ["odds_snapshot", "odds_movement"],
    "FANDUEL": ["odds_snapshot", "odds_movement"],
    "BET365": ["odds_snapshot", "odds_movement"],
}

# ---------------------------------------------------------------------------
# Prediction — Polymarket + Kalshi CLOB trades. book_snapshot_5 was retired
# 2026-04-19 (neither adapter captures order book snapshots). Polymarket
# "other" categorisation already lives in instruments-service Polymarket
# adapter — surfaces in the UI via the instrument_type breakdown, no
# separate data_type needed here.
# ---------------------------------------------------------------------------
_PREDICTION: dict[str, list[str]] = {
    "POLYMARKET": ["trades"],
    "KALSHI": ["trades"],
}


EXPECTED_COVERAGE_BY_ASSET_GROUP: dict[str, dict[str, list[str]]] = {
    "cefi": _CEFI,
    "tradfi": _TRADFI,
    "defi": _DEFI,
    "sports": _SPORTS,
    "prediction": _PREDICTION,
}


def is_expected(asset_group: str, venue: str, data_type: str) -> bool:
    """Return ``True`` iff ``(asset_group, venue, data_type)`` is in scope.

    Used by deployment-api to decide whether a missing manifest shard
    counts against the denominator (in-scope) or is excluded as
    out-of-scope. UI filter chips narrow this further at request time.
    """
    ag_scope = EXPECTED_COVERAGE_BY_ASSET_GROUP.get(asset_group.lower(), {})
    return data_type in ag_scope.get(venue, [])


def get_expected_data_types_for_venue_in_scope(asset_group: str, venue: str) -> list[str]:
    """Return the in-scope data_types for ``(asset_group, venue)``.

    Empty list means the venue is entirely out-of-scope for the asset
    group's expected-coverage policy. Callers branch on truthiness:
    truthy → include venue in denominator; falsy → render as
    ``out_of_scope``.
    """
    ag_scope = EXPECTED_COVERAGE_BY_ASSET_GROUP.get(asset_group.lower(), {})
    return list(ag_scope.get(venue, []))


def get_expected_venues_in_scope(asset_group: str) -> list[str]:
    """Return the venues with at least one expected data_type in this asset group."""
    ag_scope = EXPECTED_COVERAGE_BY_ASSET_GROUP.get(asset_group.lower(), {})
    return [venue for venue, dts in ag_scope.items() if dts]


def get_expected_pairs(asset_group: str) -> list[tuple[str, str]]:
    """Flatten to ``(venue, data_type)`` tuples for the asset group."""
    ag_scope = EXPECTED_COVERAGE_BY_ASSET_GROUP.get(asset_group.lower(), {})
    return [(venue, dt) for venue, dts in ag_scope.items() for dt in dts]


def _resolve_capability_for_venue(venue: str) -> SourceCapability | None:
    """Resolve a SourceCapability from an expected_coverage venue token.

    Venue tokens in EXPECTED_COVERAGE_BY_ASSET_GROUP are uppercase
    (e.g. "HYPERLIQUID", "BINANCE-SPOT"). SourceCapability.source is
    lowercase (e.g. "hyperliquid", "binance"). Strategy: try the exact
    lowercase match first; if not found, try the base name before the
    first "-" (e.g. "binance-spot" → "binance"). Returns None if neither
    matches a registered declaration.
    """
    lowered = venue.lower()
    try:
        return resolve_capability(lowered)
    except CapabilityResolutionError:
        pass
    base = lowered.split("-")[0]
    if base != lowered:
        try:
            return resolve_capability(base)
        except CapabilityResolutionError:
            pass
    return None


def get_source_coverage_start_for_data_type(venue: str, data_type: str) -> _date | None:
    """Return the earliest date a venue has data for a specific data_type.

    Reads from SourceCapability.coverage_start[data_type]. Returns None if
    the venue has no capability record, no coverage_start dict, or no entry
    for this data_type. Callers treat None as "no clip".
    """
    cap = _resolve_capability_for_venue(venue)
    if cap is None or cap.coverage_start is None:
        return None
    return cap.coverage_start.get(data_type)


def is_before_source_coverage_start(venue: str, data_type: str, check_date: _date) -> bool:
    """Return True if check_date is before the venue's coverage start for data_type.

    Callers use this to emit EXPECTED_PRE_SOURCE_COVERAGE_START in
    record_empty() calls. Returns False when no coverage start is known
    (no clip — do not exclude the date from the expected denominator).

    Example:
        if is_before_source_coverage_start(venue, data_type, day):
            record_empty(reason=EmptyConfirmedReason.EXPECTED_PRE_SOURCE_COVERAGE_START)
    """
    start = get_source_coverage_start_for_data_type(venue, data_type)
    if start is None:
        return False
    return check_date < start


__all__ = [
    "EXPECTED_COVERAGE_BY_ASSET_GROUP",
    "ExpectedCoverageResult",
    "ExpectedState",
    "expected_coverage",
    "get_expected_data_types_for_venue_in_scope",
    "get_expected_pairs",
    "get_expected_venues_in_scope",
    "get_source_coverage_start_for_data_type",
    "is_before_source_coverage_start",
    "is_expected",
]


# ────────────────────────────────────────────────────────────────────────────
# Availability oracle — `expected_coverage()` and supporting types.
#
# Mega-audit Phase A2 deliverable (2026-05-20).
#
# Given (asset_group, source, data_type, date), returns a deterministic answer
# to "should this cell have data?". Consumed by:
#
#   1. Manifest divergence reporting (Phase A3) — classify
#      ``actual=empty_confirmed`` rows: if oracle says ``SHOULD_HAVE_DATA`` it
#      is a ``DIVERGENT_EMPTY`` (likely adapter bug); if oracle says
#      ``EXPECTED_EMPTY:<reason>`` it is an honest empty.
#   2. Pre-flight gates in MTDS/features-service handlers — skip-with-typed-
#      reason rather than record_empty(reason="") at write-time.
#   3. Coverage denominator in deployment-ui — combine with scope policy
#      (this same module's ``is_expected``) to render the four-state view.
#
# Data inputs (all already in UAC — no new SSOT):
#   - scope policy (this module's ``EXPECTED_COVERAGE_BY_ASSET_GROUP``)
#   - SourceCapability.coverage_start via ``is_before_source_coverage_start``
#     (Phase 4 of `uac_source_capability_metadata_promotion_2026_05_20.md`)
#   - venue launch dates (`venue_launch_dates`)
#   - DeFi chain genesis dates (`chain_env.CHAIN_GENESIS_DATES`)
#   - US trading calendar (`venue_trading_calendar.US_MARKET_HOLIDAYS`)
#   - half-day sessions (`half_day_sessions.HALF_DAY_SESSIONS`)
# ────────────────────────────────────────────────────────────────────────────


class ExpectedState(StrEnum):
    """Deterministic outcome of the availability oracle.

    Closed set of four states. Pair with ``EmptyConfirmedReason`` to get the
    full per-cell expectation:

    - ``SHOULD_HAVE_DATA``: cell should be ``captured`` in the manifest. If
      ``empty_confirmed`` instead → ``DIVERGENT_EMPTY`` (review-blocking).
    - ``EXPECTED_EMPTY``: cell should be ``empty_confirmed`` with a specific
      ``EmptyConfirmedReason``. Caller composes the typed reason from the
      ``reason`` attribute of :class:`ExpectedCoverageResult`.
    - ``NOT_YET_LIVE``: target_date precedes the venue's / chain's public
      launch date. Distinct from ``EXPECTED_EMPTY`` so launchers can entirely
      skip the fetch rather than write an ``empty_confirmed`` row.
    - ``NOT_IN_SCOPE``: (asset_group, source, data_type) tuple is excluded
      from the scope policy; the cell is out_of_scope for the denominator.
    """

    SHOULD_HAVE_DATA = "SHOULD_HAVE_DATA"
    EXPECTED_EMPTY = "EXPECTED_EMPTY"
    NOT_YET_LIVE = "NOT_YET_LIVE"
    NOT_IN_SCOPE = "NOT_IN_SCOPE"


@dataclass(frozen=True, slots=True)
class ExpectedCoverageResult:
    """Per-cell outcome of :func:`expected_coverage`.

    Attributes:
        state: closed-set classification (see :class:`ExpectedState`).
        reason: when ``state in {EXPECTED_EMPTY, NOT_YET_LIVE}``, the
            ``EmptyConfirmedReason`` taxonomy member as a string-typed enum
            value (`"EXPECTED_HOLIDAY"`, `"EXPECTED_PRE_VENUE_LAUNCH"`,
            etc.); ``None`` otherwise. Always a string-typed enum member,
            never a free-form string — this is the same reason taxonomy
            ``record_empty()`` uses.
        diagnostic: human-readable one-liner explaining the result.
            For SHOULD_HAVE_DATA this is a short positive note; for
            EXPECTED_EMPTY / NOT_YET_LIVE it cites the gate that fired
            (e.g. "venue_launch_dates: BINANCE-SPOT launched 2017-07-14").
    """

    state: ExpectedState
    reason: str | None
    diagnostic: str


# Asset groups whose calendars follow US-equity trading days. Crypto markets
# (CeFi spot/perp, DeFi) are 24/7; sports + prediction are per-event /
# per-league (handled separately when calendars land).
_US_TRADFI_ASSET_GROUPS: frozenset[str] = frozenset({"tradfi"})


def _parse_iso_date(value: str | None) -> _date | None:
    if value is None:
        return None
    parts = value.split("-")
    if len(parts) != 3:
        return None
    try:
        return _date(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None


def _is_deprecated_defi_venue(data_source: str) -> bool:
    """True if the DeFi venue is in the workspace-canonical deprecated/empty set.

    SSOT: ``capability_declarations._defi_coverage.EMPTY_OR_DEPRECATED_DEFI_VENUES``
    (e.g. ``TRADER_JOEV2-AVALANCHE``, ``UNISWAPV3-POLYGON``, ``GMX-AVALANCHE``).
    These venues either have empty/retired subgraphs or no historical parquets;
    flagging them as ``EXPECTED_DEPRECATED_DATA_TYPE`` keeps the divergence
    report honest.
    """
    from .capability_declarations import EMPTY_OR_DEPRECATED_DEFI_VENUES

    return data_source in EMPTY_OR_DEPRECATED_DEFI_VENUES


def _is_defi_not_yet_collected(data_source: str) -> bool:
    """True if the DeFi venue has a subgraph but instruments-service hasn't
    backfilled it yet.

    SSOT: ``capability_declarations._defi_coverage.DEFI_INSTRUMENTS_NOT_YET_COLLECTED``
    (e.g. ``VELODROMEV2-OPTIMISM``, ``SPARK-ETHEREUM``, ``SANCTUM-SOLANA``,
    ``SOLBLAZE-SOLANA``). Until first parquet writes land, historical days for
    these venues should NOT count as ``MISSING_EXPECTED``.
    """
    from .capability_declarations import DEFI_INSTRUMENTS_NOT_YET_COLLECTED

    return data_source in DEFI_INSTRUMENTS_NOT_YET_COLLECTED


def _is_sports_in_known_source_gap(data_source: str, data_type: str, target_date: _date) -> bool:
    """True if (source, data_type, date) is inside a registered sports
    known-gap window.

    SSOT: ``unified_api_contracts.canonical.domain.sports.is_in_known_gap``
    which reads ``KNOWN_COVERAGE_GAPS[(source, data_type)]``. Sister to the
    pre-source-coverage-start gate but operates on per-source-published gaps
    (e.g. API-Football historical-stats outage windows) rather than the source
    archive's start date.
    """
    from unified_api_contracts.canonical.domain.sports import is_in_known_gap

    return is_in_known_gap(data_source, data_type, target_date.isoformat())


def _is_us_trading_day(target_date: _date) -> tuple[bool, str | None]:
    """Return (is_trading_day, reason_if_not).

    Imports are local to avoid module-load cycles when expected_coverage.py
    is imported by handlers that themselves live below the registry layer.
    """
    if target_date.weekday() >= 5:
        return False, "EXPECTED_WEEKEND"
    from .venue_trading_calendar import US_MARKET_HOLIDAYS

    if target_date.isoformat() in US_MARKET_HOLIDAYS:
        return False, "EXPECTED_HOLIDAY"
    return True, None


def _is_us_half_day(venue: str, target_date: _date) -> bool:
    """True if ``venue``'s US session is shortened (not closed) on target_date."""
    from .half_day_sessions import is_half_day_session

    return is_half_day_session(venue, target_date)


def _defi_protocol_chain_split(source: str) -> tuple[str, str] | None:
    """Split a DeFi source like 'AAVEV3-ETHEREUM' into ('AAVEV3', 'ETHEREUM')."""
    if "-" not in source:
        return None
    protocol, _, chain = source.rpartition("-")
    if not protocol or not chain:
        return None
    return protocol.upper(), chain.upper()


def _venue_launch_date_for(asset_group: str, source: str) -> _date | None:
    """Lookup the public-launch date for ``source`` in the given ``asset_group``."""
    from .venue_launch_dates import (
        CEFI_VENUE_LAUNCH_DATES,
        DEFI_VENUE_LAUNCH_DATES,
        PREDICTION_VENUE_LAUNCH_DATES,
    )

    table_by_group: dict[str, dict[str, str]] = {
        "cefi": CEFI_VENUE_LAUNCH_DATES,
        "defi": DEFI_VENUE_LAUNCH_DATES,
        "prediction": PREDICTION_VENUE_LAUNCH_DATES,
    }
    table = table_by_group.get(asset_group.lower())
    if table is None:
        return None
    return _parse_iso_date(table.get(source))


def _chain_genesis_date_for(chain: str) -> _date | None:
    """Lookup the chain's genesis date (DeFi only)."""
    from .chain_env import CHAIN_GENESIS_DATES

    return _parse_iso_date(CHAIN_GENESIS_DATES.get(chain.upper()))


def expected_coverage(
    asset_group: str,
    data_source: str,
    data_type: str,
    target_date: _date,
) -> ExpectedCoverageResult:
    """Return the deterministic expected-coverage state for one cell.

    Composes the scope policy with launch/genesis dates and trading-calendar
    data already encoded in UAC. No I/O — same inputs return the same result.

    Order of checks (first matching gate fires):

    1. **Scope policy** — ``NOT_IN_SCOPE`` if tuple not in
       ``EXPECTED_COVERAGE_BY_ASSET_GROUP``.
    2. **Pre-venue-launch** — ``NOT_YET_LIVE`` +
       ``EXPECTED_PRE_VENUE_LAUNCH`` if before venue_launch_dates entry.
    3. **Pre-chain-genesis (DeFi only)** — ``NOT_YET_LIVE`` +
       ``EXPECTED_PRE_GENESIS_CHAIN`` if before chain genesis.
    4. **Pre-source-coverage-start** — ``EXPECTED_EMPTY`` +
       ``EXPECTED_PRE_SOURCE_COVERAGE_START`` if before
       ``SourceCapability.coverage_start[data_type]``. Composes with the
       Phase 4 helper :func:`is_before_source_coverage_start`.
    5. **TradFi calendar** — weekend / holiday / half-day.
    6. **Default** → ``SHOULD_HAVE_DATA``.

    Args:
        asset_group: workspace-canonical lowercase (``cefi`` / ``defi`` /
            ``tradfi`` / ``sports`` / ``prediction``).
        data_source: venue token as used in
            ``EXPECTED_COVERAGE_BY_ASSET_GROUP`` (e.g. ``BINANCE-SPOT``,
            ``AAVEV3-ETHEREUM``, ``CME``).
        data_type: data_type as used in the scope policy.
        target_date: the date being queried.

    Returns:
        :class:`ExpectedCoverageResult` with state + typed reason + diagnostic.

    Known gaps (Phase A2 v2 — 2026-05-20 round 2 update):

    * Per-symbol granularity (``EXPECTED_INSTRUMENT_NOT_LISTED`` /
      ``EXPECTED_INSTRUMENT_DELISTED``) requires IS catalogue access; out of
      scope here. Pair this oracle with IS at the call site (R9 in mega-audit
      delegation SSOT).
    * Sports league off-season (per-league fixture calendar) requires league_id
      axis on the oracle signature; current gate only covers source-level
      known-gap windows via `is_in_known_gap`. Per-league off-season check
      lives in `unified_api_contracts.canonical.domain.sports.get_league_fixture_calendar`
      and should be called by callers that know the league_id.
    * DeFi protocol pause windows (time-windowed, e.g. Aave V2 deprecation)
      not yet encoded. Venue-level deprecation IS handled via
      `EMPTY_OR_DEPRECATED_DEFI_VENUES` (gate added 2026-05-20 round 2).
    """
    ag = asset_group.lower()
    ag_scope = EXPECTED_COVERAGE_BY_ASSET_GROUP.get(ag, {})
    in_scope_types = ag_scope.get(data_source, [])
    if data_type not in in_scope_types:
        return ExpectedCoverageResult(
            state=ExpectedState.NOT_IN_SCOPE,
            reason=None,
            diagnostic=f"({ag}, {data_source}, {data_type}) not in EXPECTED_COVERAGE_BY_ASSET_GROUP",
        )

    # DeFi venue-level deprecation (added 2026-05-20 round 2 — operator Q1 fix).
    # Even when the venue is in scope policy, the workspace-canonical
    # `EMPTY_OR_DEPRECATED_DEFI_VENUES` overrides — these venues have empty
    # or retired subgraphs.
    if ag == "defi" and _is_deprecated_defi_venue(data_source):
        return ExpectedCoverageResult(
            state=ExpectedState.EXPECTED_EMPTY,
            reason="EXPECTED_DEPRECATED_DATA_TYPE",
            diagnostic=(
                f"DeFi venue {data_source} in EMPTY_OR_DEPRECATED_DEFI_VENUES — "
                "retired subgraph / no historical parquets"
            ),
        )

    # DeFi venues with subgraph but no instruments-service backfill yet
    # (added 2026-05-20 round 2 — sister of EMPTY_OR_DEPRECATED check).
    if ag == "defi" and _is_defi_not_yet_collected(data_source):
        return ExpectedCoverageResult(
            state=ExpectedState.EXPECTED_EMPTY,
            reason="EXPECTED_INSTRUMENT_NOT_LISTED",
            diagnostic=(
                f"DeFi venue {data_source} in DEFI_INSTRUMENTS_NOT_YET_COLLECTED — instruments-service backfill pending"
            ),
        )

    launch = _venue_launch_date_for(ag, data_source)
    if launch is not None and target_date < launch:
        return ExpectedCoverageResult(
            state=ExpectedState.NOT_YET_LIVE,
            reason="EXPECTED_PRE_VENUE_LAUNCH",
            diagnostic=f"venue {data_source} public launch {launch.isoformat()} > target {target_date.isoformat()}",
        )

    if ag == "defi":
        split = _defi_protocol_chain_split(data_source)
        if split is not None:
            protocol, chain = split
            genesis = _chain_genesis_date_for(chain)
            if genesis is not None and target_date < genesis:
                return ExpectedCoverageResult(
                    state=ExpectedState.NOT_YET_LIVE,
                    reason="EXPECTED_PRE_GENESIS_CHAIN",
                    diagnostic=f"chain {chain} genesis {genesis.isoformat()} > target {target_date.isoformat()}",
                )
            # Protocol pause window check (added 2026-05-20 round 3 — R8 full closure).
            from .protocol_pause_windows import is_protocol_paused

            paused, pause_desc = is_protocol_paused(protocol, chain, target_date)
            if paused:
                return ExpectedCoverageResult(
                    state=ExpectedState.EXPECTED_EMPTY,
                    reason="EXPECTED_PROTOCOL_PAUSED",
                    diagnostic=pause_desc or f"{protocol}-{chain} in pause window covering {target_date.isoformat()}",
                )

    # Sports source-level known gaps (added 2026-05-20 round 2 — operator Q1 fix).
    # Composes with sports.league_data.is_in_known_gap which reads the canonical
    # KNOWN_COVERAGE_GAPS registry per (source, data_type).
    if ag == "sports" and _is_sports_in_known_source_gap(data_source, data_type, target_date):
        return ExpectedCoverageResult(
            state=ExpectedState.EXPECTED_EMPTY,
            reason="EXPECTED_KNOWN_SOURCE_GAP",
            diagnostic=(
                f"sports source {data_source} data_type {data_type} in known-gap window "
                f"covering {target_date.isoformat()} (see sports.league_data.KNOWN_COVERAGE_GAPS)"
            ),
        )

    # Phase 4 helper: per-data_type source coverage start.
    if is_before_source_coverage_start(data_source, data_type, target_date):
        start = get_source_coverage_start_for_data_type(data_source, data_type)
        return ExpectedCoverageResult(
            state=ExpectedState.EXPECTED_EMPTY,
            reason="EXPECTED_PRE_SOURCE_COVERAGE_START",
            diagnostic=(
                f"source {data_source} coverage_start[{data_type}] = "
                f"{start.isoformat() if start else '?'} > target {target_date.isoformat()}"
            ),
        )

    if ag in _US_TRADFI_ASSET_GROUPS:
        is_trading_day, calendar_reason = _is_us_trading_day(target_date)
        if not is_trading_day:
            assert calendar_reason is not None
            return ExpectedCoverageResult(
                state=ExpectedState.EXPECTED_EMPTY,
                reason=calendar_reason,
                diagnostic=f"US calendar: {calendar_reason} on {target_date.isoformat()}",
            )
        if _is_us_half_day(data_source, target_date):
            return ExpectedCoverageResult(
                state=ExpectedState.SHOULD_HAVE_DATA,
                reason="EXPECTED_PARTIAL_HALF_DAY",
                diagnostic=f"US half-day session on {target_date.isoformat()} (shortened, not closed)",
            )

    return ExpectedCoverageResult(
        state=ExpectedState.SHOULD_HAVE_DATA,
        reason=None,
        diagnostic=f"({ag}, {data_source}, {data_type}) in scope on {target_date.isoformat()}",
    )

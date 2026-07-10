"""Provider data availability registry — lag, timing, and freshness metadata.

Centralises knowledge about when data from each provider becomes available
after the target date (UTC).  Services use this to decide whether it is
reasonable to request data for a given (venue, date) combination.

This is distinct from ``DataAvailability`` in ``_endpoint_registry_types.py``
which classifies endpoints as historical-only / live-only / both.  This module
describes *when* a provider's data for a specific UTC date is expected to land.

Import via the registry facade::

    from unified_api_contracts.registry import (
        VENUE_DATA_AVAILABILITY,
        ProviderDataAvailability,
        get_provider_availability,
    )

Or from the top-level UAC facade::

    from unified_api_contracts import (
        VENUE_DATA_AVAILABILITY,
        ProviderDataAvailability,
        get_provider_availability,
    )
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderDataAvailability:
    """Describes when a data provider makes data available for a target UTC date.

    Attributes:
        venue_name: Canonical venue / provider name (matches VENUE_TO_ASSET_GROUP keys where applicable).
        asset_group: Venue / data plane bucket — ``cefi``, ``tradfi``, ``defi``, ``sports``,
            ``prediction``, ``altdata``.
        availability_lag_hours: Minimum hours after UTC midnight before the
            *previous* day's data is expected.  ``0.0`` means real-time / no lag.
        available_after_utc_hour: If the provider publishes on a fixed daily
            schedule, the UTC hour (0-23) after which data appears.  ``None``
            when availability is continuous / real-time.
        is_t_plus_one: ``True`` when the provider only delivers data for a date
            *after* that date has ended (batch file providers like Tardis,
            Databento).  ``False`` for real-time / streaming providers.
        notes: Human-readable notes about availability quirks.
    """

    venue_name: str
    asset_group: str
    availability_lag_hours: float
    available_after_utc_hour: int | None = None
    is_t_plus_one: bool = False
    notes: str = ""


# ---------------------------------------------------------------------------
# VENUE_DATA_AVAILABILITY — SSOT for provider timing metadata
#
# Keyed by canonical venue/provider name.  Where a provider serves multiple
# venue strings (e.g. TARDIS serves BINANCE-SPOT, BINANCE-FUTURES, etc.)
# the entry is under the *provider* name and a lookup helper resolves it.
# ---------------------------------------------------------------------------

VENUE_DATA_AVAILABILITY: dict[str, ProviderDataAvailability] = {
    # ── CeFi tick data (via Tardis) ──────────────────────────────────
    "TARDIS": ProviderDataAvailability(
        venue_name="TARDIS",
        asset_group="cefi",
        availability_lag_hours=6.0,
        available_after_utc_hour=6,
        is_t_plus_one=True,
        notes="Full-day zstd files available ~06:00 UTC for the previous day",
    ),
    # ── TradFi tick data (via Databento) ─────────────────────────────
    "DATABENTO": ProviderDataAvailability(
        venue_name="DATABENTO",
        asset_group="tradfi",
        availability_lag_hours=0.0,
        available_after_utc_hour=0,
        is_t_plus_one=True,
        notes="T+1 batch files available shortly after midnight UTC",
    ),
    # "BARCHART" provider RETIRED 2026-06-24 — Barchart removed (VIX 15m now
    # aggregates from VX futures via Databento XCBF.PITCH). No shim.
    "YAHOO_FINANCE": ProviderDataAvailability(
        venue_name="YAHOO_FINANCE",
        asset_group="tradfi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Rolling 60-day window for VIX 15m; real-time for FX rates",
    ),
    # ── Sports reference data ────────────────────────────────────────
    "API_FOOTBALL": ProviderDataAvailability(
        venue_name="API_FOOTBALL",
        asset_group="sports",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Real-time API; fixtures, odds, predictions available immediately",
    ),
    "ODDS_API": ProviderDataAvailability(
        venue_name="ODDS_API",
        asset_group="sports",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Real-time odds aggregation; immediate availability",
    ),
    "FOOTYSTATS": ProviderDataAvailability(
        venue_name="FOOTYSTATS",
        asset_group="sports",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Real-time API for match stats and odds",
    ),
    "SOCCER_FOOTBALL_INFO": ProviderDataAvailability(
        venue_name="SOCCER_FOOTBALL_INFO",
        asset_group="sports",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Real-time API for fixtures, teams, referees",
    ),
    "TRANSFERMARKT": ProviderDataAvailability(
        venue_name="TRANSFERMARKT",
        asset_group="sports",
        availability_lag_hours=12.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Web scraper with variable lag; transfers/valuations update slowly",
    ),
    "UNDERSTAT": ProviderDataAvailability(
        venue_name="UNDERSTAT",
        asset_group="sports",
        availability_lag_hours=24.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="xG stats updated hours to days after match completion",
    ),
    "OPEN_METEO": ProviderDataAvailability(
        venue_name="OPEN_METEO",
        asset_group="sports",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Real-time weather API; immediate availability",
    ),
    "BETFAIR": ProviderDataAvailability(
        venue_name="BETFAIR",
        asset_group="sports",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Real-time Exchange Stream API; sub-second updates",
    ),
    # ── Prediction markets ───────────────────────────────────────────
    "POLYMARKET": ProviderDataAvailability(
        venue_name="POLYMARKET",
        asset_group="prediction",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Public CLOB; real-time prices and orderbook",
    ),
    "KALSHI": ProviderDataAvailability(
        venue_name="KALSHI",
        asset_group="prediction",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Regulated prediction market; real-time API",
    ),
    # ── DeFi protocols (all on-chain / The Graph — immediate) ────────
    "AAVE_V3": ProviderDataAvailability(
        venue_name="AAVE_V3",
        asset_group="defi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="On-chain + The Graph subgraph; real-time",
    ),
    "COMPOUND_V3": ProviderDataAvailability(
        venue_name="COMPOUND_V3",
        asset_group="defi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="On-chain + The Graph subgraph; real-time",
    ),
    "MORPHO": ProviderDataAvailability(
        venue_name="MORPHO",
        asset_group="defi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Blue API + on-chain; real-time",
    ),
    "UNISWAP_V2": ProviderDataAvailability(
        venue_name="UNISWAP_V2",
        asset_group="defi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="On-chain + The Graph subgraph; real-time",
    ),
    "UNISWAP_V3": ProviderDataAvailability(
        venue_name="UNISWAP_V3",
        asset_group="defi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="On-chain + The Graph subgraph; real-time",
    ),
    "UNISWAP_V4": ProviderDataAvailability(
        venue_name="UNISWAP_V4",
        asset_group="defi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="On-chain + The Graph subgraph; real-time",
    ),
    "CURVE": ProviderDataAvailability(
        venue_name="CURVE",
        asset_group="defi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="On-chain + The Graph subgraph; real-time",
    ),
    "BALANCER": ProviderDataAvailability(
        venue_name="BALANCER",
        asset_group="defi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="On-chain + The Graph subgraph; real-time",
    ),
    "LIDO": ProviderDataAvailability(
        venue_name="LIDO",
        asset_group="defi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="On-chain staking protocol; real-time",
    ),
    "ETHENA": ProviderDataAvailability(
        venue_name="ETHENA",
        asset_group="defi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="On-chain synthetic dollar protocol; real-time",
    ),
    "ETHERFI": ProviderDataAvailability(
        venue_name="ETHERFI",
        asset_group="defi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="On-chain restaking protocol; real-time",
    ),
    "FLUID_PLASMA": ProviderDataAvailability(
        venue_name="FLUID_PLASMA",
        asset_group="defi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="On-chain lending protocol; real-time",
    ),
    "AERODROME": ProviderDataAvailability(
        venue_name="AERODROME",
        asset_group="defi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="On-chain DEX on Base; real-time",
    ),
    # ── CeFi CLOBs (real-time) ───────────────────────────────────────
    "HYPERLIQUID": ProviderDataAvailability(
        venue_name="HYPERLIQUID",
        asset_group="cefi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="On-chain CLOB; real-time REST + WebSocket",
    ),
    "ASTER": ProviderDataAvailability(
        venue_name="ASTER",
        asset_group="cefi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="On-chain CLOB; real-time REST + WebSocket",
    ),
    # ── Alt data / on-chain analytics ────────────────────────────────
    "ALCHEMY": ProviderDataAvailability(
        venue_name="ALCHEMY",
        asset_group="altdata",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Real-time RPC + enhanced APIs",
    ),
    "THEGRAPH": ProviderDataAvailability(
        venue_name="THEGRAPH",
        asset_group="altdata",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Decentralised indexing; typically <1 min behind chain head",
    ),
    # ── TradFi reference data ────────────────────────────────────────
    "FRED": ProviderDataAvailability(
        venue_name="FRED",
        asset_group="tradfi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Federal Reserve Economic Data; updated on release schedule",
    ),
    "POLYGON": ProviderDataAvailability(
        venue_name="POLYGON",
        asset_group="tradfi",
        availability_lag_hours=0.0,
        available_after_utc_hour=None,
        is_t_plus_one=False,
        notes="Real-time + historical equities/options data",
    ),
}

# ---------------------------------------------------------------------------
# Mapping from composite venue names (e.g. "BINANCE-FUTURES") to provider
# ---------------------------------------------------------------------------

_TARDIS_VENUES: frozenset[str] = frozenset(
    {
        "BINANCE-SPOT",
        "BINANCE-FUTURES",
        "BYBIT",
        "OKX",
        "DERIBIT",
        "UPBIT",
        "COINBASE-SPOT",
    }
)

_DATABENTO_VENUES: frozenset[str] = frozenset(
    {
        "NASDAQ",
        "NYSE",
        "CME",
        "ICE",
        "CBOE",
    }
)

_DEFI_PROTOCOL_PREFIXES: tuple[tuple[str, str], ...] = (
    ("AAVE_V3-", "AAVE_V3"),
    ("COMPOUND_V3-", "COMPOUND_V3"),
    ("MORPHO-", "MORPHO"),
    ("UNISWAP_V2-", "UNISWAP_V2"),
    ("UNISWAP_V3-", "UNISWAP_V3"),
    ("UNISWAP_V4-", "UNISWAP_V4"),
    ("CURVE-", "CURVE"),
    ("BALANCER-", "BALANCER"),
    ("AERODROME-", "AERODROME"),
)


def get_provider_availability(venue: str) -> ProviderDataAvailability | None:
    """Resolve the data availability metadata for a venue.

    Handles composite venue names like ``BINANCE-FUTURES`` (→ TARDIS),
    ``AAVE_V3-ETHEREUM`` (→ AAVE_V3), etc.

    Returns ``None`` if the venue is not recognised.
    """
    # Direct lookup first
    entry = VENUE_DATA_AVAILABILITY.get(venue)
    if entry is not None:
        return entry

    # Tardis-served CeFi venues
    if venue in _TARDIS_VENUES:
        return VENUE_DATA_AVAILABILITY["TARDIS"]

    # Databento-served TradFi venues
    if venue in _DATABENTO_VENUES:
        return VENUE_DATA_AVAILABILITY["DATABENTO"]

    # DeFi composite venues (protocol-chain)
    for prefix, provider_key in _DEFI_PROTOCOL_PREFIXES:
        if venue.startswith(prefix):
            return VENUE_DATA_AVAILABILITY.get(provider_key)

    # Uppercase normalisation fallback
    normalised = venue.upper().replace("-", "_")
    return VENUE_DATA_AVAILABILITY.get(normalised)


__all__ = [
    "VENUE_DATA_AVAILABILITY",
    "ProviderDataAvailability",
    "get_provider_availability",
]

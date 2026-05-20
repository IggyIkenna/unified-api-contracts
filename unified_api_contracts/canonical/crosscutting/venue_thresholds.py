"""Venue-level connectivity + testnet SSOTs.

Two registries, both keyed by venue + (where applicable) data_type / mode:

1. ``VENUE_HEARTBEAT_THRESHOLDS`` — empirical inter-message gap thresholds per
   ``(venue, data_type)`` for ``LiveConnectivityWatchdog`` (MTDS market_interface).
   Values reflect 99th-percentile inter-message gaps in nominal operation; once
   exceeded the watchdog transitions HEALTHY → GAP and emits
   ``CONNECTIVITY_GAP_DETECTED``.

2. ``VENUE_TESTNET_URLS`` — testnet REST + WS endpoint URLs for CeFi venues
   (Binance / Bybit / OKX / Deribit / Coinbase). execution-service CCXT
   adapters route to these when the ``testnet=True`` constructor flag is set;
   CCXT's ``set_sandbox_mode(True)`` typically handles the routing internally,
   but the SSOT here keeps the URLs centrally documented + lets ad-hoc
   non-CCXT adapters reach the same endpoints.

Reference: master plan ``master_to_live_defi_2026_05_23.md`` Group F Item 20
("Live testnet replicates prod") + audit issue
``audit_2026_05_08_substantial_unfixed_items.md`` items #5 (MTDS adapter
heartbeat wire-in) + #11 (CeFi testnet wiring).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

# ----------------------------------------------------------------------------
# Heartbeat thresholds (live-mode connectivity watchdog)
# ----------------------------------------------------------------------------

# Default per-class thresholds. Per-(venue, data_type) overrides go in
# ``VENUE_HEARTBEAT_THRESHOLDS`` below; consumers should fall back to
# ``DEFAULT_HEARTBEAT_THRESHOLD_BY_CLASS[<class>]`` keyed by venue category.
DEFAULT_HEARTBEAT_THRESHOLD_BY_CLASS: dict[str, timedelta] = {
    # CeFi WS feeds (BTC/ETH majors): trade ticks land sub-second on busy
    # pairs, sparser pairs may go a few seconds idle. 5s captures the 99p
    # gap for top venues without false-tripping on illiquid altcoins.
    "cefi_ws": timedelta(seconds=5),
    # DeFi WS (Hyperliquid / Aster) — block-driven, slower cadence (~12s
    # ETH block time, faster on L2s). 10s is the empirical floor before
    # genuine network/peer issues become more likely than just slow blocks.
    "defi_ws": timedelta(seconds=10),
    # TradFi DBN replay / Databento live — depends on session activity;
    # 30s for the live tape during regular session is conservative.
    "tradfi_replay": timedelta(seconds=30),
    # Prediction REST polling — Polymarket / Kalshi are polled every 5-10s
    # in live mode; 60s threshold catches a missed poll cycle.
    "prediction_rest": timedelta(seconds=60),
    # Sports REST polling — odds_api polled every 30-60s during
    # active match windows; 120s catches a missed cycle without false-tripping.
    "sports_rest": timedelta(seconds=120),
}


# Per-(venue, data_type) overrides. Empty by default — populate with measured
# 99p inter-message gaps as live-mode telemetry accumulates. Until then,
# consumers should use ``DEFAULT_HEARTBEAT_THRESHOLD_BY_CLASS[<class>]``.
VENUE_HEARTBEAT_THRESHOLDS: dict[tuple[str, str], timedelta] = {}


def get_heartbeat_threshold(
    venue: str,
    data_type: str,
    venue_class: str = "cefi_ws",
) -> timedelta:
    """Return heartbeat threshold for a ``(venue, data_type)`` pair.

    Lookup order:
      1. Explicit ``VENUE_HEARTBEAT_THRESHOLDS[(venue, data_type)]`` override.
      2. ``DEFAULT_HEARTBEAT_THRESHOLD_BY_CLASS[venue_class]`` fallback.

    ``venue_class`` MUST be a key in
    ``DEFAULT_HEARTBEAT_THRESHOLD_BY_CLASS``. Unknown class raises ``KeyError``
    loud (per CLAUDE.md "fail loud — no fallback masking").
    """
    explicit = VENUE_HEARTBEAT_THRESHOLDS.get((venue.lower(), data_type.lower()))
    if explicit is not None:
        return explicit
    return DEFAULT_HEARTBEAT_THRESHOLD_BY_CLASS[venue_class]


# ----------------------------------------------------------------------------
# Testnet endpoint SSOT (CeFi CCXT adapters)
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class VenueTestnetEndpoints:
    """Testnet REST + WS endpoint set for a CeFi venue.

    ``rest`` and ``ws`` are the canonical testnet URLs; CCXT typically routes
    via ``set_sandbox_mode(True)`` so adapters do NOT need to thread these
    URLs explicitly. The SSOT exists for (a) non-CCXT direct REST/WS clients,
    (b) ops dashboards that surface the testnet endpoint per venue, and (c)
    smoke-test fixtures.
    """

    rest: str
    ws: str
    notes: str = ""


# Per CCXT documentation + venue testnet portals (verified 2026-05-08):
# - Binance Futures testnet:  https://testnet.binancefuture.com
# - Binance Spot testnet:     https://testnet.binance.vision
# - Bybit testnet:            https://api-testnet.bybit.com
# - OKX testnet (paper):      reached via header `x-simulated-trading: 1` on
#                             the production endpoint — CCXT handles via
#                             set_sandbox_mode. No separate base URL.
# - Deribit testnet:          https://test.deribit.com
# - Coinbase Advanced Trade:  no public testnet (CCXT set_sandbox_mode is
#                             a no-op for coinbase-advanced; sim-mode used
#                             for paper trading).
VENUE_TESTNET_URLS: dict[str, VenueTestnetEndpoints] = {
    "binance": VenueTestnetEndpoints(
        rest="https://testnet.binancefuture.com",
        ws="wss://stream.binancefuture.com",
        notes=(
            "Binance Futures testnet. Spot testnet is at "
            "https://testnet.binance.vision (separate portal). "
            "CCXT set_sandbox_mode(True) routes correctly when "
            "options.defaultType in ('future', 'spot')."
        ),
    ),
    "bybit": VenueTestnetEndpoints(
        rest="https://api-testnet.bybit.com",
        ws="wss://stream-testnet.bybit.com",
        notes="Bybit unified-account testnet. CCXT set_sandbox_mode routes correctly.",
    ),
    "okx": VenueTestnetEndpoints(
        rest="https://www.okx.com",
        ws="wss://wspap.okx.com:8443",
        notes=(
            "OKX 'demo trading' uses the production REST host with "
            "header x-simulated-trading: 1; CCXT set_sandbox_mode(True) "
            "injects the header automatically. WS uses wspap.okx.com:8443."
        ),
    ),
    "deribit": VenueTestnetEndpoints(
        rest="https://test.deribit.com",
        ws="wss://test.deribit.com/ws/api/v2",
        notes="Deribit testnet. CCXT set_sandbox_mode routes correctly.",
    ),
    "coinbase": VenueTestnetEndpoints(
        rest="https://api-public.sandbox.exchange.coinbase.com",
        ws="wss://ws-feed-public.sandbox.exchange.coinbase.com",
        notes=(
            "Coinbase Exchange (legacy) sandbox. The newer Coinbase "
            "Advanced Trade API does NOT have a public testnet — "
            "CCXT set_sandbox_mode(True) is a no-op for coinbase-advanced; "
            "use sim-mode for paper trading there."
        ),
    ),
    "hyperliquid": VenueTestnetEndpoints(
        rest="https://api.hyperliquid-testnet.xyz",
        ws="wss://api.hyperliquid-testnet.xyz/ws",
        notes="Hyperliquid testnet (separate chain). CCXT 'hyperliquid' set_sandbox_mode routes correctly.",
    ),
}


def get_testnet_endpoints(venue: str) -> VenueTestnetEndpoints | None:
    """Return testnet endpoint set for a venue, or None if not registered.

    Caller should treat ``None`` as "this venue has no testnet"; in that case
    the CCXT adapter's ``testnet=True`` flag will fail-loud at
    ``set_sandbox_mode`` if the venue doesn't support it (Coinbase Advanced
    Trade is the canonical example).
    """
    return VENUE_TESTNET_URLS.get(venue.lower())


__all__ = [
    "DEFAULT_HEARTBEAT_THRESHOLD_BY_CLASS",
    "VENUE_HEARTBEAT_THRESHOLDS",
    "VENUE_TESTNET_URLS",
    "VenueTestnetEndpoints",
    "get_heartbeat_threshold",
    "get_testnet_endpoints",
]

"""Venue launch dates — SSOT for CeFi + Prediction "venue did not exist yet" semantics.

Sister registry to ``chain_env.CHAIN_GENESIS_DATES`` (DeFi pre-genesis) and the sports
``SOURCE_COVERAGE_START`` dict (api_football / footystats / understat archive starts).
All three express the same idea ("no data possible because the venue/chain/source did
not exist yet on this date") for different asset_groups, but the SSOTs are deliberately
separate because the underlying data sources are different.

Used by:

- ``instruments-service/scripts/enumerate_expected_universe.py`` Phase 3.D.4 backward-fill —
  generates ``record_expected_empty(reason=EXPECTED_PRE_VENUE_LAUNCH)`` rows for every
  ``(asset_group, venue, data_type, day)`` tuple where ``day < launch_date``.
- ``deployment-api`` data-status panel: clip pre-venue-launch dates from the expected
  denominator so the panel doesn't render thousands of "missing" days for venues that
  only existed for the last few months (Hyperliquid, Aster, Lighter, Pacifica, Extended).

**Conservative principle**: when uncertain, prefer the LATER (more recent) date. A
later date means fewer ``EXPECTED_PRE_VENUE_LAUNCH`` rows are emitted; if our value is
later than the actual launch, the missing few days simply stay as ``capture_status=
captured`` (or ``empty_confirmed`` if the orchestrator already ran). The cost of a
slightly-stale date is "a few days of pre-launch dates rendered as missing in the
denominator." The cost of a too-early date would be "real data dates marked as
PRE_VENUE_LAUNCH" — a correctness bug. Better to undercount than overcount.

Add a venue here when:

1. The venue appears in ``VENUES_BY_ASSET_GROUP['cefi']`` or
   ``VENUES_BY_ASSET_GROUP['prediction']``, AND
2. Its public launch date is after 2018-01-01 (the workspace's default backfill start
   date) — otherwise the [2018-01-01, today] window has zero pre-launch days and the
   entry is no-op.

Sources for the dates below: official venue announcements + CoinGecko / DefiLlama
"founded" fields cross-checked. Documented per-venue inline so future audits can verify.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# CeFi venue launch dates — the date the venue began offering public trading
# of the data_type axis we'd actually backfill against (spot trades, perp
# futures, etc.). For venues with separate spot vs futures launches, the two
# are tracked as distinct VENUES_BY_ASSET_GROUP entries (e.g. KRAKEN-SPOT vs
# KRAKEN-FUTURES) and dated independently.
# ---------------------------------------------------------------------------

CEFI_VENUE_LAUNCH_DATES: dict[str, str] = {
    # Pre-2018-01-01 venues — entries are kept for completeness + downstream
    # data-status display, but the enumerator's pre-launch loop yields zero
    # rows for them within the default [2018-01-01, today] window.
    "BINANCE-SPOT": "2017-07-14",  # Binance launch
    "BINANCE-FUTURES": "2019-09-08",  # USDT-M futures launch
    "OKX": "2017-01-01",  # OKEx founded; rebranded OKX 2022
    "DERIBIT": "2016-06-29",  # mainnet
    "UPBIT": "2017-10-24",  # KRW market launch
    "COINBASE": "2014-12-08",  # GDAX launch (rebranded Coinbase Pro 2018)
    "BITFINEX-SPOT": "2012-12-27",  # founded
    "BITFINEX-FUTURES": "2019-08-01",  # perp launch
    "BITGET-SPOT": "2018-04-01",  # founded
    "BITGET-FUTURES": "2019-04-01",  # futures product launch
    "KRAKEN-SPOT": "2013-09-10",  # BTC trading launch (founded 2011)
    "KRAKEN-FUTURES": "2019-09-01",  # acquired CryptoFacilities, rebranded Kraken Futures
    # Post-2018 venues — these are the ones that actually generate
    # EXPECTED_PRE_VENUE_LAUNCH rows in the [2018-01-01, today] window.
    "BYBIT": "2018-12-01",  # founded Mar 2018, public trading Dec 2018
    "HYPERLIQUID": "2023-06-14",  # mainnet beta
    "ASTER": "2024-09-25",  # mainnet (post-rebrand from Astherus)
    "PACIFICA-SOLANA": "2024-04-01",  # Pacifica perp DEX on Solana
    "EXTENDED-STARKNET": "2024-09-01",  # Extended on Starknet
    "LIGHTER-ZKSYNC": "2024-09-01",  # Lighter on zkSync Era
    "GMX": "2021-09-01",  # GMX V1 on Arbitrum (V2 launched 2023-08)
    "DRIFT": "2021-11-08",  # Drift V1 mainnet on Solana
}
"""CeFi venue → public-launch date (ISO YYYY-MM-DD).

Date is the venue's earliest public-trading-available date for the data axis
we'd want to backfill (spot trades for spot venues, perp futures for futures
venues). For venues launched before the workspace's default 2018-01-01 backfill
start, the entry is informational — the enumerator yields zero pre-launch rows
within the default window.
"""


# ---------------------------------------------------------------------------
# Prediction venue launch dates — when the venue began offering public
# binary/multi-outcome markets that our pipeline could ingest.
# ---------------------------------------------------------------------------

PREDICTION_VENUE_LAUNCH_DATES: dict[str, str] = {
    "POLYMARKET": "2020-09-01",  # mainnet launch on Polygon
    "KALSHI": "2021-07-30",  # CFTC-approved exchange launch
}
"""Prediction venue → public-launch date (ISO YYYY-MM-DD).

Polymarket launched on Polygon mainnet 2020-09 (early markets used Matic
sidechain). Kalshi opened trading 2021-07 after CFTC approval. Both are
well after the workspace 2018-01-01 default — so both contribute
EXPECTED_PRE_VENUE_LAUNCH rows in the default window.
"""


# ---------------------------------------------------------------------------
# Combined lookup — keyed by ``(asset_group, venue)`` so a single helper
# call can resolve the launch date regardless of which asset_group's
# dict the venue lives in.
# ---------------------------------------------------------------------------

_ALL_VENUE_LAUNCH_DATES: Final[dict[tuple[str, str], str]] = {
    **{("cefi", venue): date for venue, date in CEFI_VENUE_LAUNCH_DATES.items()},
    **{("prediction", venue): date for venue, date in PREDICTION_VENUE_LAUNCH_DATES.items()},
}


def get_venue_launch_date(asset_group: str, venue: str) -> str | None:
    """Return the venue's public-launch date (ISO YYYY-MM-DD) or ``None``.

    Case-insensitive on ``asset_group`` (lowercase) and ``venue`` (uppercase).
    Returns ``None`` for unknown ``(asset_group, venue)`` pairs — caller can
    treat unknown as "unbounded" (date not constrained, fall through to other
    enumerator branches).
    """
    return _ALL_VENUE_LAUNCH_DATES.get((asset_group.lower(), venue.upper()))


__all__ = (
    "CEFI_VENUE_LAUNCH_DATES",
    "PREDICTION_VENUE_LAUNCH_DATES",
    "get_venue_launch_date",
)

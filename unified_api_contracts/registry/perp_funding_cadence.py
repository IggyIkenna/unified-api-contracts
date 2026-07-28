"""Per-venue perp funding-rate cadence + annualisation math.

``FUNDING_CADENCE_SECONDS[venue]`` is the **annualisation period** — the time
span that the venue's canonical/stored ``funding_rate`` figure represents — NOT
necessarily the venue's funding *charge* interval. For almost every venue the two
coincide (the venue publishes a per-charge-cycle rate), so the period is just the
funding interval:

* 8h period (3 figures/day): Binance, Bybit, OKX, Aster (perp-CCXT), Bitget, Bitfinex
* 4h period (6 figures/day): Kraken Pro derivatives
* 1h period (24 figures/day): Hyperliquid, Lighter, Coinbase (COINBASE-FUTURES /
  Coinbase International Exchange -- official docs confirm hourly settlement;
  empirically confirmed 2026-07-28 against real captured shards), EXTENDED-STARKNET
  (see below -- also 1h, confirmed both ways 2026-07-28)

**EXTENDED-STARKNET key form is the FULL compound venue string, not a bare
short name (codified 2026-07-28).** Every other entry here is either the bare
exchange name (``binance``, ``deribit``, ``aster``) or resolves to one after
``_canonical_venue`` strips a registered *instrument-type* suffix
(``-futures``/``-swap``/``-perpetual``/``-perp``, e.g. ``BINANCE-FUTURES`` ->
``binance``). EXTENDED-STARKNET's canonical ``venue`` value is ALWAYS the
compound ``"EXTENDED-STARKNET"`` (GCS venue-dir, ``instrument_id``, the
adapter's own ``venue`` field literal -- never a bare ``"EXTENDED"`` anywhere
in the codebase), and ``-STARKNET`` is a CHAIN suffix, not an instrument-type
one (parallel to LIGHTER-ZKSYNC / PACIFICA-SOLANA's ``<VENUE>-<CHAIN>``
naming) -- adding it to ``_VENUE_SUFFIXES`` would be semantically wrong (that
list documents instrument-shape markers, not chain identity). So the registry
key here is the full lowercased compound string ``"extended-starknet"``;
registering a bare ``"extended"`` instead would silently make
``is_supported_venue("EXTENDED-STARKNET")`` return ``False`` for every real
caller (``perp_funding_rates.py`` / ``perp_funding_rates_defi.py`` /
``canonical_derivative_ticker_funding_provider.py`` all pass the parsed GCS
venue-dir string straight through) -- confirmed live in-session
(``_canonical_venue("EXTENDED-STARKNET") == "extended-starknet"``, no suffix
stripped). Cadence + mechanism evidence:

* **Official docs** (fetched live 2026-07-28): ``docs.extended.exchange/
  extended-resources/trading/funding-payments`` -- "funding payments are
  charged every hour and are applied to all users with open positions at
  that time"; ``api.docs.extended.exchange`` ``GET /info/{market}/funding``
  -- "the funding rate is calculated every minute; it is only applied once
  per hour", and its ``T`` timestamp field is documented as "the timestamp
  (in epoch milliseconds) when the funding rate was calculated and applied"
  -- i.e. Extended's own raw ``T`` field IS the charge instant already (no
  forward-looking-vs-charge-instant offset exists for this venue the way it
  did for the Tardis bulk-CSV venues -- see
  ``plans/active/issues/perp_funding_data_semantics_and_cadence_2026_06_16.md``
  Finding 2 / the ``reprocess_bulk_tardis_derivative_ticker_funding_timestamp_
  2026_07_28.py`` script this venue was explicitly a no-op case for).
* **Empirical** (real captured ``derivative_ticker`` shards, both the
  ``batch_extended`` and the currently-mislabelled ``batch_tardis`` lane --
  see ``plans/active/issues/onchain_venues_mislabeled_batch_tardis_lane_
  2026_07_20.md``): every sampled shard carries exactly 24 rows/day; on
  2026-06-03 every one of AAVE-USD/BTC-USD/ETH-USD/SOL-USD/XRP-USD's 24
  ``timestamp`` values is IDENTICAL across instruments (a single system-wide
  settlement batch, not a per-market async job) and lands at ``minute=0`` of
  every UTC hour with sub-second jitter only (deltas between consecutive
  settlements cluster tightly around exactly 3600s: observed range
  [3599.09s, 3600.94s], i.e. <=0.95s jitter -- consistent with "calculated
  every minute, applied once per hour"). Cross-checked across 2025-07-18
  (venue funding genesis), 2025-07-20, 2025-08-01, 2026-01-15, 2026-02-15,
  2026-06-03 -- same 24-rows/day, minute=0 pattern throughout; 2025-07-17
  (one day pre-genesis) has ZERO objects (honest absence, not a flat/
  fabricated placeholder). See
  ``plans/active/issues/perp_funding_data_semantics_and_cadence_2026_06_16.md``.

**Deribit is the one figure-vs-charge exception (codified 2026-06-17).** Deribit
*charges* funding hourly, but the canonical ``derivative_ticker.funding_rate`` we
ingest (Tardis -> MTDS, and UAC ``external/deribit/normalize.py`` which maps the
``funding_8h`` field) stores the venue's published **8-hour figure**, NOT the
per-hour rate (empirically verified 2026-06-16/17: the stored value ~= Deribit API
``interest_8h`` ~ -1e-6, not ``interest_1h`` ~ -1e-8). Since the annualiser does
``rate x figures_per_year``, and the stored figure is the 8h figure, Deribit's
annualisation period is **8h** — using 1h over-states Deribit funding APY by 8x.
We keep the stored ``funding_rate`` equal to the venue's published figure (so it
matches the exchange API exactly) and annualise at the figure's period. If the
ingest is ever switched to persist Deribit's per-hour rate, change this entry back
to ``1 * 3600`` in the same commit. See
``plans/active/issues/perp_funding_data_semantics_and_cadence_2026_06_16.md``
Finding 1 + ``e2e-testing/scripts/defi/staked_basis_funding_scan.py``.

Reading raw funding_rate from MTDS adapters and feeding it directly into
strategy features as an annualised rate without venue-aware scaling produces
~8x errors for the venues whose figure-period differs from the 8h default. This
module is the **single source of truth** for the conversion — strategy +
features-service + execution + risk all consume from here. UTL's former
``return_metrics.FUNDING_PERIODS_PER_DAY`` was a divergent parallel registry
(Aster/Deribit inverted, 8x wrong) and was DELETED 2026-06-17 in favour of this.

Single-place rule (Bucket-name SSOT cousin): never inline a `* 3 * 365`
constant — call ``annualise_funding_rate_bps(rate, venue)`` (or
``fundings_per_day(venue)`` / ``fundings_per_year(venue)`` for the period).

Adding a new venue: pick the period in seconds = the span the venue's PUBLISHED
funding figure represents (Binance: 8h; Hyperliquid: 1h; Deribit: 8h figure even
though it charges hourly — see above). Then add a row + a unit test. **Key
form**: use the bare exchange name UNLESS the venue's canonical ``venue``
value is itself a compound ``<VENUE>-<CHAIN>`` string that ``_canonical_venue``
does not otherwise reduce (e.g. EXTENDED-STARKNET, see above) — in that case
the registry key is the full lowercased compound string, verified via
``_canonical_venue(<real venue value>)`` BEFORE assuming a short key resolves.

Refs:
* plans/active/phase5_features_streaming_carry_staked_basis_mvp_2026_05_19.md
  Phase A
* plans/active/issues/perp_funding_data_semantics_and_cadence_2026_06_16.md
* features-service/features_service/cefi/calculators/perp_funding_rates.py
* features-service/features_service/onchain/calculators/perp_funding_rates_defi.py
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

# ── Per-venue funding cadence in seconds ─────────────────────────────────────
# Single SSOT — update here, not in any consumer.
FUNDING_CADENCE_SECONDS: Final[dict[str, int]] = {
    # CeFi — 8h figure (3/day)
    "binance": 8 * 3600,
    "bybit": 8 * 3600,
    "okx": 8 * 3600,
    "aster": 8 * 3600,  # Astherus/Aster: 8h funding (fundingTime spacing = 28 800 s, verified 2026-06-16)
    "bitget": 8 * 3600,
    "bitfinex": 8 * 3600,
    # CeFi — 4h figure (6/day)
    "kraken": 4 * 3600,
    # CeFi — Deribit: CHARGES hourly, but the stored funding_rate is the 8h FIGURE
    # (verified 2026-06-16/17) -> annualise at 8h. Using 1h over-states 8x. See module docstring.
    "deribit": 8 * 3600,
    # CeFi — Coinbase (COINBASE-FUTURES / Coinbase International Exchange): 1h figure
    # (24/day). Confirmed BOTH via official docs (help.coinbase.com/en/derivatives/
    # perpetual-style-futures/funding-rate: "Settlements of Funding happens every hour")
    # AND empirically against real captured production data (2026-07-28): the
    # `derivative_ticker.funding_timestamp` column for venue=COINBASE-FUTURES,
    # day=2026-07-24 shows exactly 24 distinct funding_timestamp values per shard,
    # each spaced precisely 3600s apart (verified across 6 real shards incl. PENGU-USD,
    # RED-USD, XRP-USD, POPCAT-USD, SKHY-USD, QQQ-USD -- see
    # plans/active/issues/perp_funding_data_semantics_and_cadence_2026_06_16.md).
    "coinbase": 1 * 3600,
    # EXTENDED-STARKNET (StarkNet perp DEX): 1h figure (24/day). Key is the FULL
    # compound venue string (not "extended") -- see module docstring for why.
    # Confirmed via official docs (docs.extended.exchange/extended-resources/
    # trading/funding-payments: "charged every hour") AND empirically 2026-07-28
    # (24 distinct settlements/day, cross-instrument-identical, minute=0 UTC
    # anchor, <=0.95s jitter -- see module docstring for the full evidence).
    "extended-starknet": 1 * 3600,
    # DeFi — 1h figure (24/day)
    "hyperliquid": 1 * 3600,
    "lighter": 1 * 3600,
    # DRIFT / PACIFICA (Solana) removed 2026-07-16 (operator ruling: all Solana perp
    # DEXes dropped except Jupiter, which is a swap aggregator not a perp DEX).
    # GMX removed 2026-07-25 (unreliable historical funding data — see
    # unified-trading-pm/plans/active/defi_gmx_venue_removal_2026_07_25.md).
}

SECONDS_PER_YEAR: Final[int] = 365 * 24 * 3600

# Convenience: 10000 bps = 100% -> multiplier from rate-fraction to bps
_BPS_PER_RATE: Final[Decimal] = Decimal("10000")

# Perp instrument-type suffixes carried on GCS venue-dir keys
# (``BINANCE-FUTURES`` / ``OKX-SWAP`` / ``ETH-PERPETUAL``) that are NOT part of
# the venue identity for cadence lookup. Stripping them here is the SSOT for
# the venue-dir -> cadence-key mapping (callers must NOT keep their own dict —
# that was the bug class of the deleted UTL ``FUNDING_PERIODS_PER_DAY``).
_VENUE_SUFFIXES: Final[tuple[str, ...]] = ("-futures", "-swap", "-perpetual", "-perp")


def _canonical_venue(venue: str) -> str:
    """Normalise a venue string to a ``FUNDING_CADENCE_SECONDS`` key.

    Accepts both the bare venue name (``binance``) and the GCS venue-dir form
    (``BINANCE-FUTURES`` / ``OKX-SWAP``): lowercases then strips a single perp
    instrument-type suffix. So ``fundings_per_year("OKX-SWAP")`` resolves to
    the ``okx`` cadence.
    """
    key = venue.lower()
    for suffix in _VENUE_SUFFIXES:
        if key.endswith(suffix):
            return key[: -len(suffix)]
    return key


def fundings_per_year(venue: str) -> Decimal:
    """Number of funding accruals per year for ``venue``.

    Accepts the bare venue name or the GCS venue-dir form (``BINANCE-FUTURES``).
    Raises ``KeyError`` if the venue isn't in the registry — caller should
    have validated venue against ``is_supported_venue`` already.
    """
    cadence = FUNDING_CADENCE_SECONDS[_canonical_venue(venue)]
    # Decimal arithmetic to avoid float drift on the high cadences (a 5min
    # cadence = 105120 fundings/year would float-round otherwise).
    return Decimal(SECONDS_PER_YEAR) / Decimal(cadence)


def fundings_per_day(venue: str) -> Decimal:
    """Number of funding figures per day for ``venue`` (``fundings_per_year`` / 365).

    The SSOT replacement for any hard-coded ``periods_per_day`` (e.g. the old
    UTL ``FUNDING_PERIODS_PER_DAY`` dict, deleted 2026-06-17). Use with the
    generic ``funding_apr_per_day(rate, periods_per_day)`` math helper, or call
    :func:`annualise_funding_rate_bps` directly. Raises ``KeyError`` for an
    unregistered venue — validate against ``is_supported_venue`` first.
    """
    return Decimal(86400) / Decimal(FUNDING_CADENCE_SECONDS[_canonical_venue(venue)])


def annualise_funding_rate_bps(rate: Decimal, venue: str) -> Decimal:
    """Convert a raw per-funding-cycle rate fraction into annualised APY bps.

    ``rate`` is the raw funding_rate from the venue's API as a Decimal
    fraction (e.g. 0.0001 = 1bp per cycle = 0.01%). Output is the linearly
    annualised APY in basis points.

    Linear (not compounded) is used because (a) funding is rebated, not
    reinvested — there's no auto-compounding inside the venue; (b) strategy
    comparisons are easier in linear bps; (c) cycle rates are tiny so
    linear ~= compounded to 1bp anyway.

    Example: Binance 0.01% per 8h -> 0.0001 * 3 * 365 * 10000 = 109,500 bps =
    1095% APY (deliberately huge to highlight units in tests; real funding
    is typically 0.001% - 0.01% per cycle = ~11% - 110% APY).
    """
    return rate * fundings_per_year(venue) * _BPS_PER_RATE


def is_supported_venue(venue: str) -> bool:
    """``True`` if ``venue`` has a registered funding cadence.

    Accepts the bare venue name or the GCS venue-dir form (``OKX-SWAP``).
    """
    return _canonical_venue(venue) in FUNDING_CADENCE_SECONDS


def cadence_seconds(venue: str) -> int:
    """Whole-second funding cadence for ``venue`` — the single derivation point
    for "shift a raw timestamp by one cadence period" style corrections (e.g.
    deriving ``next_funding_timestamp = funding_timestamp + cadence_seconds``,
    or the Tardis-wire-forward-looking-value fix in
    ``market-tick-data-service/scripts/one_offs/
    reprocess_bulk_tardis_derivative_ticker_funding_timestamp_2026_07_28.py``).
    Every entry in ``FUNDING_CADENCE_SECONDS`` is already a whole number of
    seconds by construction, so this is just the dict lookup through
    ``_canonical_venue`` — call it instead of reaching into the dict directly
    so a future non-integer entry would be a type error at the boundary, not a
    silent float downstream. Raises ``KeyError`` for an unregistered venue —
    validate against :func:`is_supported_venue` first.
    """
    return FUNDING_CADENCE_SECONDS[_canonical_venue(venue)]


__all__ = [
    "FUNDING_CADENCE_SECONDS",
    "SECONDS_PER_YEAR",
    "annualise_funding_rate_bps",
    "cadence_seconds",
    "fundings_per_day",
    "fundings_per_year",
    "is_supported_venue",
]

"""Most-liquid representative selectors (volume-based) — items 002 + 003 in
``plans/active/mvp_for_mdps_and_features_universe_uac_2026_06_28.md``.

Two selectors share a single venue-volume basis (computed once by callers from
the manifest/candle volume we already have, and passed in here as observations):

- :func:`execution_spot_representative` — per ``(base, asset_group)``, the
  most-liquid SPOT ``(venue, instrument)`` for EXECUTION (consumed by
  Plan 9's execution-fidelity harness).
- ``feature_perp_representative`` (item 002, NOT yet implemented) — per
  ``(base, asset_group)``, the most-liquid PERPETUAL ``(venue, instrument)``
  for delta-one feature computation. Will live in this same module so the
  shared :class:`VenueVolumeObservation` contract + tie-break rules are
  declared once.

Both functions are pure: the caller supplies a sequence of measured
observations; the selector restricts to MVP-scope cells, picks the highest
volume, and applies a deterministic ``(venue ASC, instrument ASC)`` tie-break.
The volume basis (quote-currency aggregate over some window — typically the
last 7-30 days of candle volume) is the caller's responsibility — UAC owns
the selection contract, NOT the data layer that aggregates volume.

Why a pure function + caller-supplied observations:
  - UAC stays a types/contracts library with NO data-plane dependencies.
  - Trivially concurrent across bases (independent calls, no shared state).
  - Deterministic + testable without mocking a manifest reader.
  - Scales to the full ``CEFI_BASE_ASSET_UNIVERSE`` (~490 bases): the caller
    aggregates venue volume ONCE per window (the "computed once" basis), then
    invokes the selector per-base over that shared snapshot.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from unified_api_contracts.canonical.crosscutting.mvp_scope import (
    mdps_mvp_universe,
)

# ---------------------------------------------------------------------------
# Volume observation — the shared basis contract for both selectors
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VenueVolumeObservation:
    """One venue's measured trading volume for a ``(base, instrument)`` cell.

    The shared volume-basis contract consumed by both
    :func:`execution_spot_representative` (item 003) and
    ``feature_perp_representative`` (item 002). Callers aggregate per-venue
    volume from the MDPS manifest / candle volume over a chosen basis window
    (e.g. trailing 30 days, quote-currency notional), then pass observations
    to the relevant selector.

    Attributes:
        venue: Canonical venue identifier (e.g. ``"BINANCE-SPOT"``,
            ``"COINBASE-SPOT"``). Must match the venue spelling used in
            :data:`unified_api_contracts.MVP_SCOPE`.
        instrument: Canonical instrument identifier on the venue
            (e.g. ``"BTC-USDT"``, ``"BTC/USD"``). Opaque to the selector;
            returned verbatim as part of the chosen representative.
        instrument_type: Canonical instrument_type (e.g. ``"SPOT_PAIR"``,
            ``"PERPETUAL"``, ``"EQUITY"``). Used to gate selection by family
            (SPOT for the execution selector; PERPETUAL for the feature
            selector when wired).
        base: Base currency the instrument trades (e.g. ``"BTC"``,
            ``"ETH"``). Selectors filter observations by this field.
        volume: Aggregated trading volume over the basis window, in a
            consistent quote currency (USD/USDT-equivalent). Larger ==
            more liquid. Callers MUST use the same unit across all
            observations for a single selector invocation; mixing units is
            a caller bug the selector cannot detect.
    """

    venue: str
    instrument: str
    instrument_type: str
    base: str
    volume: float


# ---------------------------------------------------------------------------
# Per-asset_group SPOT instrument_types
# ---------------------------------------------------------------------------
# What counts as a "spot-execution representative" depends on the AG:
#   - cefi: literal SPOT_PAIR (BTC-USDT on BINANCE-SPOT, etc.).
#   - tradfi: the cash equity / ETF — the spot twin of CME futures and Binance
#     tradfi-perps (the equity-basis carve-out's basis leg in mvp_scope.py).
#   - defi: DEX pool quotes ARE the spot venue on-chain (POOL = EVM AMM pool
#     snapshots; DEX_POOL = Solana DEX orderbook/quote shards).
# sports / prediction have no spot-execution concept — the selector raises.

_SPOT_INSTRUMENT_TYPES_BY_ASSET_GROUP: Final[dict[str, frozenset[str]]] = {
    "cefi": frozenset({"SPOT_PAIR"}),
    "tradfi": frozenset({"EQUITY", "ETF"}),
    "defi": frozenset({"POOL", "DEX_POOL"}),
}


# ---------------------------------------------------------------------------
# Public selector — item 003
# ---------------------------------------------------------------------------


def execution_spot_representative(
    base: str,
    asset_group: str,
    venue_volumes: Iterable[VenueVolumeObservation],
) -> tuple[str, str] | None:
    """Return the most-liquid SPOT ``(venue, instrument)`` for *base* by volume.

    Filters *venue_volumes* down to observations that

    1. match ``base`` (instrument trades this base),
    2. carry a SPOT-class ``instrument_type`` for ``asset_group``
       (see :data:`_SPOT_INSTRUMENT_TYPES_BY_ASSET_GROUP`), AND
    3. whose ``(venue, instrument_type)`` cell is in the MVP scope for
       ``asset_group`` (per :func:`mdps_mvp_universe`).

    The highest-volume surviving observation wins; ties are broken
    deterministically by ``(venue ASC, instrument ASC)`` so the same input
    always selects the same representative across processes and re-runs.

    Args:
        base: Base currency (e.g. ``"BTC"``, ``"ETH"``).
        asset_group: One of ``"cefi"`` / ``"tradfi"`` / ``"defi"``. Other
            asset_groups have no spot-execution concept.
        venue_volumes: Iterable of measured per-venue volume observations
            over the caller's chosen basis window.

    Returns:
        ``(venue, instrument)`` of the most-liquid spot representative, or
        ``None`` when no observation passes the filter (no MVP-scope spot
        venue lists *base*, or the observation list is empty).

    Raises:
        ValueError: ``asset_group`` is not a market-data AG with a spot
            representative (sports / prediction / unknown / Phase-2 stub).

    Example::

        from unified_api_contracts import (
            VenueVolumeObservation,
            execution_spot_representative,
        )

        observations = [
            VenueVolumeObservation("BINANCE-SPOT", "BTCUSDT", "SPOT_PAIR", "BTC", 5_000_000_000.0),
            VenueVolumeObservation("COINBASE-SPOT", "BTC-USD", "SPOT_PAIR", "BTC", 800_000_000.0),
        ]
        venue, instrument = execution_spot_representative("BTC", "cefi", observations)
        assert (venue, instrument) == ("BINANCE-SPOT", "BTCUSDT")
    """
    spot_types = _SPOT_INSTRUMENT_TYPES_BY_ASSET_GROUP.get(asset_group)
    if spot_types is None:
        raise ValueError(
            f"execution_spot_representative: asset_group {asset_group!r} has no "
            "spot-execution representative (supported: cefi / tradfi / defi)."
        )
    mvp_cells = mdps_mvp_universe(asset_group)
    eligible = [
        obs
        for obs in venue_volumes
        if obs.base == base
        and obs.instrument_type in spot_types
        and (obs.venue, obs.instrument_type) in mvp_cells
    ]
    if not eligible:
        return None
    # Highest volume wins; deterministic tie-break by (venue ASC, instrument ASC).
    best = min(eligible, key=lambda o: (-o.volume, o.venue, o.instrument))
    return (best.venue, best.instrument)

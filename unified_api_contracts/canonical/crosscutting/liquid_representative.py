"""Most-liquid representative selectors (volume-based) — items 002 + 003 in
``plans/active/mvp_for_mdps_and_features_universe_uac_2026_06_28.md``, plus
the margin-side selector from
``plans/active/issues/cefi_universe_capture_rule_2026_06_23.md``.

Three selectors share a single venue-volume basis (computed once by callers
from the manifest/candle volume we already have, and passed in here as
observations):

- :func:`execution_spot_representative` — per ``(base, asset_group)``, the
  most-liquid SPOT ``(venue, instrument)`` for EXECUTION (consumed by
  Plan 9's execution-fidelity harness).
- :func:`feature_perp_representative` (item 002) — per ``(base, asset_group)``,
  the most-liquid PERPETUAL ``(venue, instrument)`` for delta-one feature
  computation. Shares :class:`VenueVolumeObservation` + the deterministic
  tie-break with the spot selector. TradFi has no perp → falls back to the
  most-liquid 1m FUTURE source (CME front-month is the typical winner).
- :func:`margin_type_representative` (cefi_universe_capture_rule) — per
  ``(venue, base)``, which :class:`~unified_api_contracts.MarginType`
  (linear vs inverse) to CAPTURE for a venue that lists BOTH margin types of
  the same base's perp (e.g. BYBIT, OKX-SWAP, KRAKEN-FUTURES all expose a
  linear USDT/USDC leg AND a coin-margined inverse leg for the same base
  under one canonical venue key — see ``_infer_margin_type`` in
  instruments-service's tardis ``parsing.py``). Generalizes the operator's
  "capture the more liquid margin type, default linear" rule via measured
  volume instead of a hand-list. Does NOT apply to DERIBIT (both legs
  captured unconditionally — not margin-gated, per the same issue doc) or to
  BINANCE-DELIVERY (removed from cefi MVP scope entirely, mvp_scope.py v10
  decision #3 — COIN-M delivery is not MVP, so there is no margin-side
  choice to make for it).

All three functions are pure: the caller supplies a sequence of measured
observations; the selector restricts to MVP-scope cells, picks the highest
volume, and applies a deterministic tie-break. The volume basis
(quote-currency aggregate over some window — typically the last 7-30 days of
candle volume) is the caller's responsibility — UAC owns the selection
contract, NOT the data layer that aggregates volume. This is deliberately
NOT a live external API call (e.g. hitting Tardis per-contract at request
time) — "live-data" means the volume WE ALREADY CAPTURE via MDPS/MTDS,
aggregated by the caller, same as the other two selectors.

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

from unified_api_contracts._instrument_enums import MarginType
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
    # Project the (venue, instrument_type, data_type) triples down to the
    # (venue, instrument_type) pairs this selector gates on — it picks a
    # representative per-instrument, not per-shard, so it has no data_type
    # axis of its own.
    mvp_cells = {(v, it) for v, it, _dt in mdps_mvp_universe(asset_group)}
    eligible = [
        obs
        for obs in venue_volumes
        if obs.base == base and obs.instrument_type in spot_types and (obs.venue, obs.instrument_type) in mvp_cells
    ]
    if not eligible:
        return None
    # Highest volume wins; deterministic tie-break by (venue ASC, instrument ASC).
    best = min(eligible, key=lambda o: (-o.volume, o.venue, o.instrument))
    return (best.venue, best.instrument)


# ---------------------------------------------------------------------------
# Per-asset_group PERP instrument_types
# ---------------------------------------------------------------------------
# Delta-one features are computed on the **most-liquid PERP per base**
# (plan: every MVP base has a perp via the perp-gate rule, and perps usually
# carry more open interest / volume than the matching spot leg). Per-AG:
#   - cefi: PERPETUAL covers BOTH the crypto-base perp AND the crypto-venue
#     single-stock equity perp (operator 2026-07-16 — equity perps are typed
#     PERPETUAL, no distinct EQUITY_PERP type; the equity identity rides the
#     catalogue is_equity_perp / tracks_equity tags). EQUITY_PERP is retained in
#     the set below only DEFENSIVELY (deprecated; no obs carries it anymore).
#   - tradfi: NO perpetual exists — the plan substitutes the most-liquid 1m
#     FUTURE source (CME front-month). OPTION is excluded (delta-one features
#     do not run on options).
#   - defi: on-chain perps (Hyperliquid / Aster / Drift) are classified ``cefi``
#     everywhere in this codebase, so defi has NO perp instrument_type of its
#     own here; defi-native delta-one features have their own pipeline
#     (``features_service.onchain``). The selector raises for ``defi`` /
#     ``sports`` / ``prediction``.

_PERP_INSTRUMENT_TYPES_BY_ASSET_GROUP: Final[dict[str, frozenset[str]]] = {
    # PERPETUAL covers crypto-venue equity perps too (operator 2026-07-16 — no
    # distinct EQUITY_PERP type). EQUITY_PERP kept defensively (deprecated; no obs
    # carries it, and the (venue, EQUITY_PERP) MVP cell no longer exists either).
    "cefi": frozenset({"PERPETUAL", "EQUITY_PERP"}),
    "tradfi": frozenset({"FUTURE"}),
}


# ---------------------------------------------------------------------------
# Public selector — item 002
# ---------------------------------------------------------------------------


def feature_perp_representative(
    base: str,
    asset_group: str,
    venue_volumes: Iterable[VenueVolumeObservation],
) -> tuple[str, str] | None:
    """Return the most-liquid PERP ``(venue, instrument)`` for *base* by volume.

    The contract the delta-one features pipeline reads to collapse a base from
    "every venue's perp in the manifest" down to ONE representative — so a
    delta-one feature family emits one row per ``(base, timestamp)`` instead
    of ``N_venues`` rows. Selection is BY MEASURED VOLUME from *venue_volumes*
    (the same per-venue aggregate the caller computed for
    :func:`execution_spot_representative` — the basis is computed once and
    reused across both selectors). Binance-Futures usually wins on crypto,
    but only because its measured volume is highest, not because the
    function hardcodes it.

    Filters *venue_volumes* down to observations that

    1. match ``base`` (instrument trades this base),
    2. carry a PERP-class ``instrument_type`` for ``asset_group``
       (see :data:`_PERP_INSTRUMENT_TYPES_BY_ASSET_GROUP`), AND
    3. whose ``(venue, instrument_type)`` cell is in the MVP scope for
       ``asset_group`` (per :func:`mdps_mvp_universe`).

    The highest-volume surviving observation wins; ties are broken
    deterministically by ``(venue ASC, instrument ASC)`` — the same rule as
    :func:`execution_spot_representative` — so the same input always selects
    the same representative across processes and re-runs.

    Per-asset-group dispatch:

    * **cefi** — filter to ``PERPETUAL``; the perp leg of a crypto base OR a
      crypto-venue single-stock equity perp (typed PERPETUAL, operator 2026-07-16).
    * **tradfi** — no perpetual exists; collapse to the most-liquid 1m
      ``FUTURE`` source instead (CME front-month is the typical winner; the
      tradfi MVP rule has CME as the only venue today).
    * **defi / sports / prediction** — raises :class:`ValueError`. DeFi
      perpetuals (Hyperliquid / Aster / Drift) are classified ``cefi``
      everywhere in this codebase (see ``MVP_SCOPE["cefi"].venues``); on-chain
      DeFi-native delta-one features have their own pipeline. Sports +
      prediction do not run delta-one features.

    Args:
        base: Base-asset symbol (``BTC`` / ``ETH`` / ``ES`` / ``NQ`` / …).
        asset_group: Lowercase asset_group key — ``cefi`` or ``tradfi``.
        venue_volumes: Iterable of measured per-venue volume observations
            over the caller's chosen basis window — typically the same
            iterable handed to :func:`execution_spot_representative`
            (records for OTHER bases / instrument_types are dropped by the
            per-call filter, so a single "all-cells" snapshot can be reused).

    Returns:
        ``(venue, instrument)`` of the most-liquid perp representative, or
        ``None`` when no observation passes the filter (fail-loud: ``None``
        means "no representative available", never a silent default).

    Raises:
        ValueError: ``asset_group`` is not ``cefi`` or ``tradfi`` (defi /
            sports / prediction do not run delta-one features via this
            selector — see the asset_group-dispatch section above).

    Example::

        from unified_api_contracts import (
            VenueVolumeObservation,
            feature_perp_representative,
        )

        observations = [
            VenueVolumeObservation("BINANCE-FUTURES", "BTC-USDT", "PERPETUAL", "BTC", 12_500_000_000.0),
            VenueVolumeObservation("BYBIT", "BTC-USDT", "PERPETUAL", "BTC", 4_200_000_000.0),
        ]
        assert feature_perp_representative("BTC", "cefi", observations) == (
            "BINANCE-FUTURES",
            "BTC-USDT",
        )
    """
    perp_types = _PERP_INSTRUMENT_TYPES_BY_ASSET_GROUP.get(asset_group)
    if perp_types is None:
        raise ValueError(
            f"feature_perp_representative: asset_group {asset_group!r} not supported — "
            "delta-one features via PERP/FUTURE representative apply to cefi or tradfi only "
            "(defi perps are classified cefi; defi-native, sports, prediction do not run "
            "delta-one features via this selector)."
        )
    # Project the (venue, instrument_type, data_type) triples down to the
    # (venue, instrument_type) pairs this selector gates on — same rationale
    # as execution_spot_representative above.
    mvp_cells = {(v, it) for v, it, _dt in mdps_mvp_universe(asset_group)}
    eligible = [
        obs
        for obs in venue_volumes
        if obs.base == base and obs.instrument_type in perp_types and (obs.venue, obs.instrument_type) in mvp_cells
    ]
    if not eligible:
        return None
    # Highest volume wins; deterministic tie-break by (venue ASC, instrument ASC).
    # Same tie-break shape as execution_spot_representative — both selectors
    # share the contract so callers see identical determinism semantics.
    best = min(eligible, key=lambda o: (-o.volume, o.venue, o.instrument))
    return (best.venue, best.instrument)


# ---------------------------------------------------------------------------
# Margin-type volume observation — the basis contract for the margin selector
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MarginVolumeObservation:
    """One margin-type leg's measured trading volume for a ``(venue, base)``
    PERP cell — the basis contract for :func:`margin_type_representative`.

    Attributes:
        venue: Canonical venue identifier (e.g. ``"BYBIT"``, ``"OKX-SWAP"``).
            Must match the venue spelling used in
            :data:`unified_api_contracts.MVP_SCOPE`.
        base: Base currency the perp trades (e.g. ``"BTC"``, ``"ETH"``).
        margin_type: :class:`~unified_api_contracts.MarginType` of this
            observation's leg (``LINEAR`` or ``INVERSE`` — ``QUANTO`` is
            never a candidate; the selector ignores it).
        volume: Aggregated trading volume over the basis window, in a
            consistent quote currency (USD/USDT-equivalent). Larger ==
            more liquid. Callers MUST use the same unit across all
            observations for a single selector invocation.
    """

    venue: str
    base: str
    margin_type: MarginType
    volume: float


# ---------------------------------------------------------------------------
# Public selector — cefi_universe_capture_rule margin-side selection
# ---------------------------------------------------------------------------


def margin_type_representative(
    venue: str,
    base: str,
    margin_volumes: Iterable[MarginVolumeObservation],
) -> MarginType:
    """Return the more-liquid margin type to CAPTURE for a ``(venue, base)`` perp.

    Generalizes the operator's rule (``cefi_universe_capture_rule_2026_06_23.md``
    § "COIN-MARGIN (inverse) perps"): "capture the MORE LIQUID margin type per
    (venue, base) — default linear (more liquid for ~all alts); capture inverse
    instead where inverse is more liquid (historically BTC/ETH inverse on some
    venues)." This function is the "live-data liquidity spot-check" that rule
    called for, generalized via measured volume rather than a hand-list.

    Filters *margin_volumes* down to observations matching ``(venue, base)``,
    sums volume PER :class:`~unified_api_contracts.MarginType` (a base can have
    more than one observation per margin type — e.g. a perp AND a dated future
    sharing the same settlement leg), and returns whichever of
    ``LINEAR``/``INVERSE`` has the higher aggregate. ``LINEAR`` wins both a tie
    AND the no-observations case — the documented safe default.

    NOT applicable to:

    * **DERIBIT** — both legs are captured unconditionally (not margin-gated;
      Deribit splits by settlement quote instead, see the issue doc). Calling
      this for Deribit is a caller error (Deribit isn't the venue this
      function exists for), though it will not raise — it simply reflects
      whatever volumes are passed.
    * **BINANCE-DELIVERY** — removed from the cefi MVP venues entirely
      (``mvp_scope.py`` v10 decision #3, 2026-06-27 — COIN-M delivery is not
      MVP), so there is no margin-side choice left to make for it; the venue
      is no longer capturable at all.

    Args:
        venue: Canonical venue identifier (e.g. ``"BYBIT"``, ``"OKX-SWAP"``,
            ``"KRAKEN-FUTURES"`` — any cefi venue that lists BOTH a linear and
            an inverse leg for the same base under one canonical venue key).
        base: Base currency (e.g. ``"BTC"``, ``"ETH"``).
        margin_volumes: Iterable of measured per-margin-type volume
            observations over the caller's chosen basis window.

    Returns:
        :attr:`MarginType.LINEAR` or :attr:`MarginType.INVERSE` — never
        ``None`` (unlike the other two selectors) because the capture layer
        always needs an answer; ``LINEAR`` is the documented fallback when no
        observation exists yet for this ``(venue, base)``.

    Example::

        from unified_api_contracts import (
            MarginType,
            MarginVolumeObservation,
            margin_type_representative,
        )

        observations = [
            MarginVolumeObservation("BYBIT", "BTC", MarginType.LINEAR, 4_200_000_000.0),
            MarginVolumeObservation("BYBIT", "BTC", MarginType.INVERSE, 180_000_000.0),
        ]
        assert margin_type_representative("BYBIT", "BTC", observations) == MarginType.LINEAR
    """
    matching = [ob for ob in margin_volumes if ob.venue == venue and ob.base == base]
    totals: dict[MarginType, float] = {}
    for ob in matching:
        totals[ob.margin_type] = totals.get(ob.margin_type, 0.0) + ob.volume
    inverse_volume = totals.get(MarginType.INVERSE, 0.0)
    linear_volume = totals.get(MarginType.LINEAR, 0.0)
    if inverse_volume > linear_volume:
        return MarginType.INVERSE
    return MarginType.LINEAR

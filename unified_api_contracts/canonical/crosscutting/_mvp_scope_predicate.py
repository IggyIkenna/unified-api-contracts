"""MVP scope public predicate — ``is_mvp()`` + venue/data_type matching helpers.

Split out of ``mvp_scope.py`` (900-line file-size QG, 2026-07-09) — pure
file-organization move, no behavior change. ``mvp_scope.py`` re-exports
everything here so the public import path
(``unified_api_contracts.canonical.crosscutting.mvp_scope``) is unchanged.

See ``mvp_scope.py`` for the full module-level doc (hierarchy, grain,
phase-1 scope). This module owns:
    * ``is_mvp()`` — the core cell-membership predicate.
    * ``get_mvp_data_types_for_cefi_venue()`` — the per-venue data_type
      convenience helper.
    * The CeFi venue/data_type matching helpers (``_cefi_venue_in_rule`` /
      ``_cefi_venue_data_type_set`` / ``_data_type_in_rule``).

SSOT: ``plans/active/mvp_scope_catalogue_tagging_2026_06_08.md``.
"""

from __future__ import annotations

from typing import Final

from unified_api_contracts.canonical.crosscutting._mvp_scope_rules import (
    MVP_SCOPE,
    CeFiMvpRule,
    DeFiMvpRule,
    FeaturesModelsMvpStub,
    PredictionMvpRule,
    SportsMvpRule,
    TradFiMvpRule,
)

# The TradFi equity/ETF MVP basis universe — the DBEQ.BASIC cash-equity twins of
# the Binance tradfi-perp underlyings (the basis-reference leg of the equity-basis
# arb archetype). Used by the tradfi MVP rule's equity carve-out below so those
# cash equities/ETFs are MVP-scoped alongside the CME futures complex.
from unified_api_contracts.registry.tradfi_ticker_universe import (
    TRADFI_EQUITY_PERP_BASIS_UNIVERSE,
)

# Venues whose canonical pipeline form is the bare base token but whose MVP rule
# declares SUB-VENUES (so an unsuffixed caller still resolves). OKX is the only
# one today: the catalogue + manifest carry ``OKX-SPOT`` / ``OKX-SWAP`` /
# ``OKX-FUTURES`` but legacy callers (+ some registries) pass the bare ``OKX``.
# A bare token that base-normalises to a key here matches ANY of that key's
# sub-venues for the (instrument_type) axis. (mvp_instrument_universe_gap_audit
# P2 #1, 2026-06-17.)
_CEFI_SUB_VENUE_BASES: Final[frozenset[str]] = frozenset({"OKX"})


def _cefi_venue_data_type_set(venue: str, rule: CeFiMvpRule) -> frozenset[str] | None:
    """Return the per-venue data_type override set for *venue*, or ``None``.

    Checks the ``venue_data_types`` map first with the exact venue string, then
    with the bare base token (``COINBASE-SPOT`` → ``COINBASE``).  Returns ``None``
    when the venue has no override (caller should use ``instrument_type_data_types``
    / flat ``data_types`` instead).

    Introduced in v11 (operator 2026-06-28) to support the COINBASE={trades}
    venue-wide override (COINBASE-SPOT / COINBASE-FUTURES drop book_snapshot_5).
    NOTE: Deribit has NO venue override — its OPTION->{options_chain} cut stays
    in ``instrument_type_data_types`` (v10), and Deribit perp/future keep
    trades + book_snapshot_5.
    """
    if not rule.venue_data_types:
        return None
    v = (venue or "").strip().upper()
    # Exact match first (COINBASE-SPOT, COINBASE-FUTURES, …).
    if v in rule.venue_data_types:
        return rule.venue_data_types[v]
    # Base-token fallback (COINBASE → matches COINBASE-SPOT / COINBASE-FUTURES
    # if the map carries the bare token; not used today but future-safe).
    base = v.split("-", 1)[0]
    if base in rule.venue_data_types:
        return rule.venue_data_types[base]
    return None


def _cefi_venue_in_rule(venue: str, rule_venues: frozenset[str]) -> bool:
    """Match a CeFi ``venue`` against the rule's venue set, OKX-aware.

    Direct membership first (``OKX-SPOT`` ∈ rule). Then, when the caller passes a
    BARE base token (``OKX``) whose base is in :data:`_CEFI_SUB_VENUE_BASES`, it
    matches iff the rule declares ANY sub-venue with that base (``OKX-SPOT`` /
    ``OKX-SWAP`` / ``OKX-FUTURES``) — so ``is_mvp("cefi", "OKX", …)`` resolves the
    instrument-grain question "is this OKX instrument in scope" without the caller
    knowing the exact sub-venue. (mvp_instrument_universe_gap_audit P2 #1.)
    """
    if venue in rule_venues:
        return True
    base = venue.strip().upper().split("-", 1)[0] if venue else ""
    if base not in _CEFI_SUB_VENUE_BASES:
        return False
    return any(rv.split("-", 1)[0] == base for rv in rule_venues)


def get_mvp_data_types_for_cefi_venue_itype(venue: str, instrument_type: str) -> frozenset[str]:
    """Return the MVP data_type set for a CeFi ``(venue, instrument_type)`` cell.

    The instrument_type-AWARE counterpart of
    :func:`get_mvp_data_types_for_cefi_venue`. It resolves the SAME effective
    data_type set that :func:`is_mvp` uses for a cefi cell (the two share this
    one resolver — see :func:`is_mvp`), so a consumer that knows the
    instrument_type gets the exact per-itype MVP set rather than the venue-wide
    flat default. This is what the instruments-service expected-universe
    enumerator uses so that a per-instrument_type override (``PERPETUAL`` →
    flat + ``liquidations``; ``OPTION`` → ``{options_chain}``) narrows the
    denominator correctly WITHOUT losing the per-venue ``venue_data_types``
    override (e.g. ``COINBASE-FUTURES`` → ``{trades}`` still wins for its
    PERPETUAL cells — no liquidations/book5 over-seed).

    Resolution order (the single SSOT for cefi effective-data_type resolution):
      1. PER-VENUE override (``venue_data_types``) — highest priority; final for
         ALL instrument_types at that venue.
      2. PER-INSTRUMENT_TYPE override (``instrument_type_data_types``) for this
         ``instrument_type`` — e.g. ``PERPETUAL`` / ``OPTION``.
      3. Flat ``data_types`` — default when neither override applies.

    Args:
        venue: Canonical CeFi venue identifier.
        instrument_type: Canonical instrument_type string (e.g. ``PERPETUAL``);
            blank / an itype with no override → the flat ``data_types`` set.

    Returns:
        Frozenset of MVP data_type strings for the cell. Empty frozenset only
        when the venue is not in the CeFi MVP rule (venue not MVP at all).
    """
    rule = MVP_SCOPE.get("cefi")
    if not isinstance(rule, CeFiMvpRule):
        return frozenset()
    # Venue must be in the rule at all.
    if not _cefi_venue_in_rule(venue, rule.venues):
        return frozenset()
    # Per-venue override is the highest-priority gate (final for all itypes).
    venue_override = _cefi_venue_data_type_set(venue, rule)
    if venue_override is not None:
        return venue_override
    # Per-instrument_type override, else the flat ``data_types`` default.
    it_norm = (instrument_type or "").strip().upper()
    return rule.instrument_type_data_types.get(it_norm, rule.data_types)


def get_mvp_data_types_for_cefi_venue(venue: str) -> frozenset[str]:
    """Return the venue-wide (instrument_type-agnostic) MVP data_type set.

    Convenience helper for capture-time enforcement (backfill launchers, the
    MTDS orchestrator, live-VM data_type selection): given a canonical CeFi
    venue string, return the data_types that are MVP for that venue.  Callers
    can then REJECT any ``(venue, data_type)`` shard where ``data_type`` is NOT
    in the returned set — this is the code-level block so no VM ever spins for
    a non-MVP (venue x data_type) combination.

    This is the instrument_type-AGNOSTIC default: it returns the per-venue
    override (if any) else the flat ``data_types`` set. It deliberately does NOT
    reflect the per-instrument_type overrides (``PERPETUAL`` → flat +
    ``liquidations``; ``OPTION`` → ``{options_chain}``) — a caller that knows
    the instrument_type MUST use :func:`get_mvp_data_types_for_cefi_venue_itype`
    (or :func:`is_mvp`) for an exact per-cell gate. Kept for back-compat with
    the venue-only callers that predate the per-itype axis.

    Args:
        venue: Canonical CeFi venue identifier (e.g. ``COINBASE-SPOT``,
            ``BINANCE-FUTURES``, ``DERIBIT``).

    Returns:
        Frozenset of MVP data_type strings for the venue.  An empty frozenset
        is returned only when the venue is not in the CeFi MVP rule (which
        means the venue is not MVP at all).

    Example::

        from unified_api_contracts import get_mvp_data_types_for_cefi_venue

        # COINBASE venues: trades only (no book5)
        assert "trades" in get_mvp_data_types_for_cefi_venue("COINBASE-SPOT")
        assert "book_snapshot_5" not in get_mvp_data_types_for_cefi_venue("COINBASE-SPOT")

        # Standard venue: trades + book5 + funding
        assert "book_snapshot_5" in get_mvp_data_types_for_cefi_venue("BINANCE-FUTURES")
    """
    # Delegates to the itype-aware resolver with an UNBOUND instrument_type:
    # the per-instrument_type override map has no ``""`` key, so this resolves to
    # the per-venue override (if any) else the flat ``data_types`` set —
    # byte-identical to the historical venue-wide behaviour.
    return get_mvp_data_types_for_cefi_venue_itype(venue, "")


# ---------------------------------------------------------------------------
# Public predicate
# ---------------------------------------------------------------------------


def _data_type_in_rule(data_type: str | None, rule_data_types: frozenset[str]) -> bool:
    """Match a ``data_type`` against a rule's declared data_types — UNBOUND-aware.

    Convention (mvp_instrument_universe_gap_audit P2 #2, 2026-06-17): a blank
    ``data_type`` (``""`` / ``None``) means **"any MVP data_type"** — an
    instrument-grain caller carries no data_type axis (the instrument exists
    across ALL the AG's data_types), so the membership question is "is this
    (venue, instrument_type, base) MVP for ANY of the rule's data_types". A blank
    data_type therefore matches iff the rule declares at least one data_type
    (always true today). A NON-blank data_type must be an explicit member. This
    lets every single-grain consumer call ``is_mvp`` cleanly without inventing a
    fake "representative" data_type locally.
    """
    if not data_type:
        return bool(rule_data_types)
    return data_type in rule_data_types


def _tradfi_underlier_gate(instrument_type: str, base_ccy: str | None, rule: TradFiMvpRule) -> bool:
    """Return True iff the TradFi underlier axis passes for the CME futures complex.

    OPTION cells use the narrower ``option_underliers`` carve-out (operator
    2026-07-14 ruling: tradfi MVP options = the S&P 500 / ES complex ONLY —
    see :data:`TradFiMvpRule.option_underliers`) when it is declared; FUTURE
    (and any other instrument_type) cells use the full ``underliers`` set
    unchanged. Mirrors the CeFi OPTION -> ``options_base_ccys`` narrowing
    pattern in :func:`is_mvp`. An empty ``underliers``/``option_underliers``
    set means "no underlier restriction" (passes unconditionally).
    """
    if instrument_type == "OPTION" and rule.option_underliers:
        return base_ccy in rule.option_underliers
    if rule.underliers:
        return base_ccy in rule.underliers
    return True


def is_mvp(
    asset_group: str,
    venue: str,
    instrument_type: str,
    data_type: str | None = None,
    *,
    base_ccy: str | None = None,
    league: str | None = None,
    market_group: str | None = None,
    source: str | None = None,
) -> bool:
    """Return ``True`` iff the catalogue cell is within the MVP scope.

    A cell is MVP iff ALL of the following hold:

    1. ``asset_group`` is declared in :data:`MVP_SCOPE`.
    2. ``(venue, instrument_type)`` is declared in the rule for that
       ``asset_group``. For CeFi, a BARE ``OKX`` caller resolves to the
       canonical ``OKX-SPOT`` / ``OKX-SWAP`` / ``OKX-FUTURES`` sub-venues
       (:func:`_cefi_venue_in_rule`).
    3. ``data_type`` is declared in the rule, OR ``data_type`` is blank
       (``""`` / ``None``) — the **unbound / any-MVP-data_type** convention for
       instrument-grain callers (:func:`_data_type_in_rule`). A blank data_type
       matches when the rule declares at least one data_type.
    4. If the rule declares ``base_ccys`` (non-empty), ``base_ccy`` must
       be in that set.
    5. If the rule declares ``underliers`` (non-empty, TradFi only), the
       caller's ``venue`` maps to an underlier in that set. (The
       ``instrument_type`` already gates the venue; the underlier check is
       advisory — see the NOTE below.)
    6. If the rule declares ``sources`` (non-empty), ``source`` must be in
       that set.
    7. For sports: ``league`` must be in the rule's ``leagues`` set.
    8. For prediction: if the rule declares ``market_groups`` (non-empty),
       ``market_group`` must be in that set.

    NOTE on TradFi underlier filtering:
        The ``underlier`` axis in :class:`TradFiMvpRule` gates which
        underlying indices are in scope (ES/NQ/VX). This is checked by
        looking for ``base_ccy`` (which carries the underlier code for
        TradFi futures — e.g. ``"ES"`` for an ES future). If ``base_ccy``
        is provided AND the rule has ``underliers``, it must be in the set.

    Args:
        asset_group: Lowercase asset-group key
            (``cefi`` / ``defi`` / ``tradfi`` / ``sports`` / ``prediction``).
        venue: Canonical venue identifier.
        instrument_type: Canonical instrument type string
            (a :class:`~unified_api_contracts.InstrumentType` string value).
        data_type: Canonical data_type string.
        base_ccy: Optional base currency or underlier code. Used for CeFi
            base_ccy filtering and TradFi underlier filtering.
        league: Sports league ID (e.g. ``"EPL"``, ``"NFL"``).
        market_group: Prediction market category (e.g. ``"crypto"``,
            ``"politics"``).
        source: Source key (e.g. ``"tardis"``, ``"databento"``).

    Returns:
        ``True`` if the cell is within the MVP scope; ``False`` otherwise.

    Example::

        from unified_api_contracts import is_mvp

        # CeFi BTC perpetual trade on Binance — in MVP scope
        assert is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "trades",
                      base_ccy="BTC")

        # A non-MVP venue — not in scope
        assert not is_mvp("cefi", "UPBIT", "SPOT_PAIR", "trades")

        # TradFi ES future — in MVP scope
        assert is_mvp("tradfi", "CME", "FUTURE", "trades",
                      base_ccy="ES")

        # Same venue/instrument_type, different expiry — ALSO in MVP scope
        # (grain is everything-or-nothing per venue/instrument_type)
        assert is_mvp("tradfi", "CME", "FUTURE", "trades",
                      base_ccy="ES")  # ESH26 and ESM26 both → True
    """
    rule = MVP_SCOPE.get(asset_group)
    if rule is None or isinstance(rule, FeaturesModelsMvpStub):
        return False

    if isinstance(rule, CeFiMvpRule):
        # Axis 1+2: venue + instrument_type (OKX bare → sub-venue aware)
        if not _cefi_venue_in_rule(venue, rule.venues):
            return False
        if instrument_type not in rule.instrument_types:
            return False
        # Axis 3: data_type (blank → any MVP data_type, unbound-grain convention).
        # Resolution order for the effective data_type set (v11):
        #   1. PER-VENUE OVERRIDE (``venue_data_types``) — highest priority.
        #      When the venue has a declared data_type set (e.g. COINBASE →
        #      {trades}, DERIBIT → {options_chain}), that set is final for ALL
        #      instrument_types at that venue.  The per-instrument_type override
        #      below does NOT apply when the venue override is set.
        #   2. PER-INSTRUMENT_TYPE OVERRIDE (``instrument_type_data_types``) —
        #      applies when the venue has NO override. Today OPTION →
        #      {options_chain} only (Deribit BTC/ETH options; this is now
        #      redundant for DERIBIT but kept for any other OPTION rows).
        #   3. FLAT ``data_types`` set — default when no override applies.
        # Single SSOT for this resolution (venue is already confirmed in-rule
        # above, so the helper returns the effective set, never ``frozenset()``).
        _dt_set = get_mvp_data_types_for_cefi_venue_itype(venue, instrument_type)
        if not _data_type_in_rule(data_type, _dt_set):
            return False
        # Axis 4: base_ccy (optional — if rule has a non-empty set, must match).
        # OPTION cells use the narrower options carve-out (Deribit-options =
        # BTC+ETH only) when ``options_base_ccys`` is declared; spot/perp legs
        # use the full ``base_ccys`` universe.
        if instrument_type == "OPTION" and rule.options_base_ccys:
            if base_ccy not in rule.options_base_ccys:
                return False
        elif rule.base_ccys and base_ccy not in rule.base_ccys:
            return False
        # Axis 5: source (optional)
        return not (rule.sources and source not in rule.sources)

    if isinstance(rule, DeFiMvpRule):
        if venue not in rule.venues:
            return False
        if instrument_type not in rule.instrument_types:
            return False
        if not _data_type_in_rule(data_type, rule.data_types):
            return False
        return not (rule.sources and source not in rule.sources)

    if isinstance(rule, TradFiMvpRule):
        # Equity-basis carve-out (2026-06-24): the DBEQ.BASIC cash equities/ETFs
        # that BACK a Binance tradfi-perp are the basis-reference leg of the
        # equity-basis arb archetype → MVP-scoped, gated to the basis universe.
        # This is a SEPARATE gate from the CME futures complex (a flat AND across
        # venues+types+underliers cannot express "(CME x FUTURE x {ES,NQ,VX}) OR
        # (NASDAQ/NYSE/ARCA/KRX x EQUITY/ETF x basis-universe)" — mirrors the cefi
        # OPTION venue carve-out pattern). data_type is still gated by the rule.
        # KRX (2026-06-24): the Korean single-stock underliers of the Binance
        # tradfi-perps are venue=KRX / source=yahoo (no US-listed twin) — added to
        # the equity-venue set so their basis cells are MVP. ``rule.sources`` is
        # empty so source=yahoo passes (US equities are databento; both in scope).
        _itype = (instrument_type or "").strip().upper()
        _venue_root = (venue or "").strip().upper().split("-", 1)[0]
        # Operator-designated extra MVP cells (2026-07-21): exact (venue_root,
        # instrument_type, base) triple match — see ``TradFiMvpRule.extra_mvp_cells``.
        if rule.extra_mvp_cells and (_venue_root, _itype, (base_ccy or "").strip().upper()) in rule.extra_mvp_cells:
            return not (rule.sources and source not in rule.sources)
        if _itype in ("EQUITY", "ETF") and _venue_root in ("NASDAQ", "NYSE", "ARCA", "AMEX", "BATS", "KRX"):
            # KRX (2026-07-12, operator decision): Yahoo-sourced with no reliable
            # intraday backfill over long historical windows -- narrowed to
            # ohlcv_24h only, separately from the US-listed equity-basis venues'
            # shared rule.data_types (ohlcv_1m). Keeps this MVP gate in sync with
            # expected_coverage.py's KRX entry (also narrowed the same day). See
            # krx_intraday_ohlcv_registry_vs_adapter_mismatch_2026_07_12.md.
            _basis_data_types = frozenset({"ohlcv_24h"}) if _venue_root == "KRX" else rule.data_types
            if not _data_type_in_rule(data_type, _basis_data_types):
                return False
            if (base_ccy or "").strip().upper() not in {t.upper() for t in TRADFI_EQUITY_PERP_BASIS_UNIVERSE}:
                return False
            return not (rule.sources and source not in rule.sources)
        # CME futures complex (ES/NQ/VX) — the original flat-AND rule.
        if venue not in rule.venues:
            return False
        if instrument_type not in rule.instrument_types:
            return False
        if not _data_type_in_rule(data_type, rule.data_types):
            return False
        # Axis: underlier — base_ccy carries the underlier code for TradFi.
        # ``_itype`` was already normalised above (equity-basis check).
        if not _tradfi_underlier_gate(_itype, base_ccy, rule):
            return False
        return not (rule.sources and source not in rule.sources)

    if isinstance(rule, SportsMvpRule):
        # Sports cells are keyed by (league, data_type); venue/instrument_type
        # are not axes in the sports MVP rule (the venues are data-source
        # providers, not instrument classification axes for sports).
        if league not in rule.leagues:
            return False
        return _data_type_in_rule(data_type, rule.data_types)

    if isinstance(rule, PredictionMvpRule):
        if venue not in rule.venues:
            return False
        if not _data_type_in_rule(data_type, rule.data_types):
            return False
        # market_group is the UNBOUND axis (mirrors the data_type convention): a
        # blank/None market_group means "any MVP market_group" — an
        # instrument-grain catalogue row carries no market_group axis, so the
        # venue/data_type axes decide membership. Without this, every prediction
        # catalogue row (the IS rollup never passes market_group) tagged mvp=0
        # despite POLYMARKET/KALSHI being in-MVP (decision #5). A NON-blank
        # market_group is still gated against the rule set.
        if rule.market_groups and market_group and market_group not in rule.market_groups:
            return False
        return not (rule.sources and source not in rule.sources)

    # Unknown rule type — conservative default: not MVP
    return False  # pragma: no cover

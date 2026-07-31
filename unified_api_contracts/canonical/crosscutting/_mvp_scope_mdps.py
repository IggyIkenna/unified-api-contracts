"""MVP-for-MDPS  =  MVP-for-MDS  (Concept 1 — same venue/instrument set).

Split out of ``mvp_scope.py`` (900-line file-size QG, 2026-07-09) — pure
file-organization move, no behavior change. ``mvp_scope.py`` re-exports
everything here so the public import path
(``unified_api_contracts.canonical.crosscutting.mvp_scope``) is unchanged.

Plan: ``plans/active/mvp_for_mdps_and_features_universe_uac_2026_06_28.md``.

MDPS does NOT maintain its own processing screen — it processes exactly the
instruments-catalogue cells MDS (market-tick-data-service) captures for the
asset group.  ``mdps_mvp_universe`` exposes that derived set so the "what
must MDPS cover" question is COMPUTED from ``MVP_SCOPE``, never coordinated
by hand — a separate hand-maintained list is the drift surface this helper
eliminates.

Grain: ``frozenset[tuple[venue, instrument_type, data_type]]`` (extended
2026-07-31, ``uac_mdps_mvp_universe_data_type_axis_2026_07_30.md`` — operator
ruling on BLK-fd70b57c). The prior grain was ``(venue, instrument_type)``
only; the ``data_type`` axis was added because the co-located MDPS+features
live-launcher exec-dispatch wiring needs, at boot, WHICH ``(venue,
data_type)`` shards are live for its ``asset_group`` — ``instrument_type``
alone cannot answer that. The per-(venue, base, day) capture predicate
(:func:`~unified_api_contracts.canonical.crosscutting._mvp_scope_capture.is_in_mvp_capture_universe`)
decides per-instrument membership at a finer grain still (with the perp-gate,
base-membership, the Deribit-options carve-out, etc.) — the MDPS universe at
the (venue, instrument_type, data_type) grain is the REACHABLE projection of
that predicate: for cefi it is the ``venues x instrument_types`` Cartesian
product with each ``(venue, instrument_type)`` pair expanded across its
EFFECTIVE data_type set (via
:func:`~unified_api_contracts.canonical.crosscutting._mvp_scope_predicate.get_mvp_data_types_for_cefi_venue_itype`
— the same per-venue / per-instrument_type override resolution ``is_mvp``
uses, so this stays the single SSOT for cefi data_type resolution); for defi
it is the flat ``venues x instrument_types x data_types`` Cartesian product
(no per-venue/per-itype override axis exists for defi); for tradfi it is the
same flat product PLUS the equity-basis carve-out cells the predicate's
tradfi branch hardcodes, each also expanded across the flat ``data_types``
set (tradfi has no per-venue/per-itype data_type override either).

Sports / prediction / models MVP rules have NO ``instrument_types`` axis
(sports keys on league + data_type; prediction on venue + market_group;
models on the ``generate_model_id`` identity axes) — MDPS handles
market-data AGs only (CLAUDE.md "MTDS is market-data only"), so it processes
ZERO shards for these asset_groups. The helper is TOTAL over every
asset_group value a co-located MDPS+features live VM can run for (same
ruling as above): it returns an EMPTY frozenset for these three AGs rather
than raising — a boot-time shard-discovery caller must never crash on an
asset_group it is legitimately allowed to run for. An asset_group NOT
declared in :data:`MVP_SCOPE` at all still raises ``ValueError`` (a genuine
config error, distinct from "declared but has no MDPS-relevant axis").

SSOT: ``plans/active/mvp_scope_catalogue_tagging_2026_06_08.md``,
``plans/active/issues/uac_mdps_mvp_universe_data_type_axis_2026_07_30.md``.
"""

from __future__ import annotations

from typing import Final

from unified_api_contracts.canonical.crosscutting._mvp_scope_predicate import (
    get_mvp_data_types_for_cefi_venue_itype,
)
from unified_api_contracts.canonical.crosscutting._mvp_scope_rules import (
    MVP_SCOPE,
    CeFiMvpRule,
    DeFiMvpRule,
    FeaturesModelsMvpStub,
    ModelsMvpRule,
    PredictionMvpRule,
    SportsMvpRule,
    TradFiMvpRule,
)

#: TradFi equity-basis venues — the cash equity twin of every Binance tradfi
#: perp underlier (NASDAQ/NYSE/ARCA/AMEX/BATS for US equities; KRX for the Korean
#: single-stock twins).  The ``is_mvp`` tradfi branch hardcodes this venue set
#: as the equity-basis carve-out (separate from the CME futures complex);
#: mirrored here so the MDPS universe derivation matches the predicate's
#: reachable ``(venue, instrument_type)`` set.  Keep in lockstep with the tuple
#: in :func:`~unified_api_contracts.canonical.crosscutting._mvp_scope_predicate.is_mvp`.
_TRADFI_EQUITY_BASIS_VENUES: Final[frozenset[str]] = frozenset({"NASDAQ", "NYSE", "ARCA", "AMEX", "BATS", "KRX"})

#: TradFi equity-basis instrument types — single-name equities + ETFs that back
#: a Binance tradfi-perp.  Mirrors the ``is_mvp`` tradfi branch's instrument-type
#: gate for the equity-basis carve-out.
_TRADFI_EQUITY_BASIS_TYPES: Final[frozenset[str]] = frozenset({"EQUITY", "ETF"})


def mdps_mvp_universe(asset_group: str) -> frozenset[tuple[str, str, str]]:
    """Return the ``(venue, instrument_type, data_type)`` cells MDPS processes for *asset_group*.

    MVP-for-MDPS == MVP-for-MDS: MDPS processes exactly the catalogue cells
    MDS captures for the asset group (Concept 1, plan
    ``mvp_for_mdps_and_features_universe_uac_2026_06_28.md``).  The returned
    set is DERIVED from :data:`MVP_SCOPE` so identity with the MDS capture
    universe is structural — there is no separate hand-maintained MDPS list.

    Per-AG composition (matches the reachable projection of
    :func:`~unified_api_contracts.canonical.crosscutting._mvp_scope_capture.is_in_mvp_capture_universe` /
    :func:`~unified_api_contracts.canonical.crosscutting._mvp_scope_predicate.is_mvp` at the
    ``(venue, instrument_type, data_type)`` grain):

    * **cefi** — ``rule.venues x rule.instrument_types``, each pair expanded
      across its EFFECTIVE data_type set via
      :func:`~unified_api_contracts.canonical.crosscutting._mvp_scope_predicate.get_mvp_data_types_for_cefi_venue_itype`
      (the same per-venue / per-instrument_type override resolution ``is_mvp``
      uses — a venue override like ``COINBASE-FUTURES`` -> ``{trades}`` or an
      instrument_type override like ``OPTION`` -> ``{options_chain}`` narrows
      the data_type axis exactly like it narrows capture). The Deribit-options
      carve-out, perp-gate, and base-membership all apply at the INSTRUMENT
      grain (per-base, per-cell) downstream of this set — at the AG/axis grain
      every declared ``(venue, instrument_type)`` pair is reachable.
    * **defi** — the flat ``rule.venues x rule.instrument_types x
      rule.data_types`` Cartesian product (no per-venue/per-instrument_type
      data_type override axis exists for defi).
    * **tradfi** — ``rule.venues x rule.instrument_types x rule.data_types``
      PLUS the equity-basis carve-out cells :data:`_TRADFI_EQUITY_BASIS_VENUES`
      x :data:`_TRADFI_EQUITY_BASIS_TYPES` x ``rule.data_types`` (the cash
      equity twins of Binance tradfi-perp underliers, hardcoded in
      ``is_mvp``'s tradfi branch; tradfi also has no per-venue/per-itype
      data_type override axis, so the flat set applies uniformly).
    * **sports / prediction / models** — no ``instrument_type`` axis at the
      MDPS grain (sports keys on ``league``; prediction on
      ``venue x market_group``; models on the ``generate_model_id`` identity
      axes — asset_group/asset/target_type/model_type/timeframe, no venue or
      instrument_type at all). MDPS handles market-data AGs only, so it
      processes ZERO shards for these AGs — returns an EMPTY frozenset (the
      function is TOTAL over these AGs, not a raise; see module docstring).

    Args:
        asset_group: Lowercase asset-group key.  Must be one of
            ``cefi`` / ``defi`` / ``tradfi`` (the market-data AGs MDPS processes)
            or one of ``sports`` / ``prediction`` / ``models`` / ``features`` /
            ``strategy`` (all return empty — no MDPS-relevant axis / not yet
            populated).

    Returns:
        Frozenset of canonical ``(venue, instrument_type, data_type)`` triples.
        Empty frozenset for a Phase-2+ stub (``features`` / ``strategy``) that
        has no rule yet, or for ``sports`` / ``prediction`` / ``models`` (no
        MDPS-relevant axis).

    Raises:
        ValueError: *asset_group* is not declared in :data:`MVP_SCOPE` at all
            (a genuine config error).

    Example::

        from unified_api_contracts import mdps_mvp_universe

        cefi_cells = mdps_mvp_universe("cefi")
        assert ("BINANCE-FUTURES", "PERPETUAL", "trades") in cefi_cells
        assert ("DERIBIT", "OPTION", "options_chain") in cefi_cells
        assert ("COINBASE-FUTURES", "PERPETUAL", "book_snapshot_5") not in cefi_cells
        assert ("CME", "FUTURE", "ohlcv_1m") in mdps_mvp_universe("tradfi")
        assert ("NASDAQ", "EQUITY", "ohlcv_1m") in mdps_mvp_universe("tradfi")
        assert mdps_mvp_universe("sports") == frozenset()
    """
    rule = MVP_SCOPE.get(asset_group)
    if rule is None:
        raise ValueError(f"mdps_mvp_universe: unknown asset_group {asset_group!r} (not declared in MVP_SCOPE)")
    if isinstance(rule, FeaturesModelsMvpStub):
        return frozenset()
    if isinstance(rule, CeFiMvpRule):
        return frozenset(
            (v, it, dt)
            for v in rule.venues
            for it in rule.instrument_types
            for dt in get_mvp_data_types_for_cefi_venue_itype(v, it)
        )
    if isinstance(rule, DeFiMvpRule):
        return frozenset((v, it, dt) for v in rule.venues for it in rule.instrument_types for dt in rule.data_types)
    if isinstance(rule, TradFiMvpRule):
        cells: set[tuple[str, str, str]] = {
            (v, it, dt) for v in rule.venues for it in rule.instrument_types for dt in rule.data_types
        }
        cells.update(
            (v, it, dt)
            for v in _TRADFI_EQUITY_BASIS_VENUES
            for it in _TRADFI_EQUITY_BASIS_TYPES
            for dt in rule.data_types
        )
        return frozenset(cells)
    # SportsMvpRule / PredictionMvpRule / ModelsMvpRule — no
    # (venue, instrument_type) axis at the MDPS grain. MDPS handles
    # market-data AGs only, so it processes ZERO shards for these AGs.
    # TOTAL over these asset_groups (2026-07-30 ruling, BLK-fd70b57c): return
    # empty, same convention as the Phase-2+ stub branch above, rather than
    # raise — a boot-time shard-discovery caller must never crash on an
    # asset_group it is legitimately allowed to run for.
    if isinstance(rule, SportsMvpRule | PredictionMvpRule | ModelsMvpRule):
        return frozenset()
    # Defensive fallback for a rule type not covered above — MVP_SCOPE's
    # static type is dict[str, object], so basedpyright cannot prove the
    # isinstance chain above is exhaustive even though every declared rule
    # class is handled. Unreachable given today's MVP_SCOPE contents.
    raise ValueError(
        f"mdps_mvp_universe: asset_group {asset_group!r} has an unrecognized MVP_SCOPE rule type "
        f"{type(rule).__name__!r} — no (venue, instrument_type, data_type) derivation is defined for it."
    )

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

Grain: ``frozenset[tuple[venue, instrument_type]]``.  This is the axis pair
every market-data AG's MVP rule declares.  The per-(venue, base, day)
capture predicate (:func:`~unified_api_contracts.canonical.crosscutting._mvp_scope_capture.is_in_mvp_capture_universe`)
decides per-instrument membership at a finer grain (with the perp-gate, base-
membership, the Deribit-options carve-out, etc.) — the MDPS universe at the
(venue, instrument_type) grain is the REACHABLE projection of that predicate,
which for cefi/defi equals the rule's ``venues x instrument_types`` Cartesian
product, and for tradfi adds the equity-basis carve-out cells the predicate's
tradfi branch hardcodes.

Sports / prediction MVP rules have NO ``instrument_types`` axis (sports keys
on league + data_type; prediction on venue + market_group) — MDPS handles
market-data AGs only (CLAUDE.md "MTDS is market-data only"), so the helper
raises ``ValueError`` for those AGs rather than returning a misleading empty
set.

SSOT: ``plans/active/mvp_scope_catalogue_tagging_2026_06_08.md``.
"""

from __future__ import annotations

from typing import Final

from unified_api_contracts.canonical.crosscutting._mvp_scope_rules import (
    MVP_SCOPE,
    CeFiMvpRule,
    DeFiMvpRule,
    FeaturesModelsMvpStub,
    ModelsMvpRule,
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


def mdps_mvp_universe(asset_group: str) -> frozenset[tuple[str, str]]:
    """Return the ``(venue, instrument_type)`` cells MDPS processes for *asset_group*.

    MVP-for-MDPS == MVP-for-MDS: MDPS processes exactly the catalogue cells
    MDS captures for the asset group (Concept 1, plan
    ``mvp_for_mdps_and_features_universe_uac_2026_06_28.md``).  The returned
    set is DERIVED from :data:`MVP_SCOPE` so identity with the MDS capture
    universe is structural — there is no separate hand-maintained MDPS list.

    Per-AG composition (matches the reachable projection of
    :func:`~unified_api_contracts.canonical.crosscutting._mvp_scope_capture.is_in_mvp_capture_universe` /
    :func:`~unified_api_contracts.canonical.crosscutting._mvp_scope_predicate.is_mvp` at the
    ``(venue, instrument_type)`` grain):

    * **cefi / defi** — ``rule.venues x rule.instrument_types``.  The Deribit-
      options carve-out, perp-gate, base-membership, and the per-venue /
      per-instrument_type data_type overrides all apply at the INSTRUMENT grain
      (per-base, per-cell) downstream of this set — at the AG/axis grain every
      declared ``(venue, instrument_type)`` pair is reachable.
    * **tradfi** — ``rule.venues x rule.instrument_types`` PLUS the equity-basis
      carve-out cells :data:`_TRADFI_EQUITY_BASIS_VENUES` x
      :data:`_TRADFI_EQUITY_BASIS_TYPES` (the cash equity twins of Binance
      tradfi-perp underliers, hardcoded in ``is_mvp``'s tradfi branch).
    * **sports / prediction / models** — no ``instrument_type`` axis at the
      MDPS grain (sports keys on ``league``; prediction on
      ``venue x market_group``; models on the ``generate_model_id`` identity
      axes — asset_group/asset/target_type/model_type/timeframe, no venue or
      instrument_type at all). MDPS handles market-data AGs only. Raises
      :class:`ValueError`.

    Args:
        asset_group: Lowercase asset-group key.  Must be one of
            ``cefi`` / ``defi`` / ``tradfi`` (the market-data AGs MDPS processes).

    Returns:
        Frozenset of canonical ``(venue, instrument_type)`` pairs.  Empty
        frozenset only if *asset_group* names a Phase-2+ stub
        (``features`` / ``strategy``) that has no rule yet.

    Raises:
        ValueError: *asset_group* is unknown, or is ``sports`` / ``prediction``
            / ``models`` (no ``instrument_type`` axis — MDPS handles
            market-data AGs only; ``models`` graduated from the stub to
            :class:`~unified_api_contracts.canonical.crosscutting._mvp_scope_rules.ModelsMvpRule`
            in P2b, but that rule's grain is the model_id identity axes, not
            ``(venue, instrument_type)``, so it is NOT a Phase-2+-stub empty
            return anymore — it is a real rule with no MDPS-relevant axis,
            same as sports/prediction).

    Example::

        from unified_api_contracts import mdps_mvp_universe

        cefi_cells = mdps_mvp_universe("cefi")
        assert ("BINANCE-FUTURES", "PERPETUAL") in cefi_cells
        assert ("DERIBIT", "OPTION") in cefi_cells
        assert ("CME", "FUTURE") in mdps_mvp_universe("tradfi")
        assert ("NASDAQ", "EQUITY") in mdps_mvp_universe("tradfi")
    """
    rule = MVP_SCOPE.get(asset_group)
    if rule is None:
        raise ValueError(f"mdps_mvp_universe: unknown asset_group {asset_group!r} (not declared in MVP_SCOPE)")
    if isinstance(rule, FeaturesModelsMvpStub):
        return frozenset()
    if isinstance(rule, CeFiMvpRule | DeFiMvpRule):
        return frozenset((v, it) for v in rule.venues for it in rule.instrument_types)
    if isinstance(rule, TradFiMvpRule):
        cells: set[tuple[str, str]] = {(v, it) for v in rule.venues for it in rule.instrument_types}
        cells.update((v, it) for v in _TRADFI_EQUITY_BASIS_VENUES for it in _TRADFI_EQUITY_BASIS_TYPES)
        return frozenset(cells)
    # SportsMvpRule / PredictionMvpRule / ModelsMvpRule — no
    # (venue, instrument_type) axis at the MDPS grain. MDPS handles
    # market-data AGs only. ModelsMvpRule (P2b) is a REAL rule (not a stub)
    # but its grain is the model_id identity axes, not venue/instrument_type —
    # same "no MDPS-relevant axis" reasoning as sports/prediction, so it is
    # explicitly checked here (not just falling through) for a clear error
    # message rather than relying on isinstance-exclusion silently catching it.
    if isinstance(rule, ModelsMvpRule):
        raise ValueError(
            f"mdps_mvp_universe: asset_group {asset_group!r} has no (venue, instrument_type) axis — "
            "models are keyed by the generate_model_id identity axes, not venue/instrument_type. "
            "MDPS handles market-data AGs (cefi/defi/tradfi) only."
        )
    raise ValueError(
        f"mdps_mvp_universe: asset_group {asset_group!r} has no (venue, instrument_type) axis — "
        "MDPS handles market-data AGs (cefi/defi/tradfi) only."
    )

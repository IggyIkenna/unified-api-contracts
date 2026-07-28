"""``ModelsMvpRule`` — the typed MVP rule for ml-service MODEL output (P2b).

Split out as its OWN leaf module (not folded into ``_mvp_scope_rules.py``) so
that file stays under the 900-line QG cap (``_mvp_scope_rules.py`` hit 949
lines with this class inline, 2026-07-28) — pure file-organization move, no
behavior change, mirroring the pre-existing ``_mvp_scope_capture.py`` /
``_mvp_scope_mdps.py`` split (2026-07-09). ``mvp_scope.py`` re-exports
``ModelsMvpRule`` so the public import path
(``unified_api_contracts.canonical.crosscutting.mvp_scope``) is unchanged.

SSOT: ``plans/active/mvp_scope_catalogue_tagging_2026_06_08.md`` P2b.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Models MVP rule
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelsMvpRule:
    """MVP rule for ml-service MODEL output (P2b —
    mvp_scope_catalogue_tagging_2026_06_08.md).

    Unlike the per-cell asset_group rules in ``_mvp_scope_rules.py`` (keyed by
    venue / instrument_type / data_type), a model has no venue/instrument_type/
    data_type axis — its stable, already-versioned identity is the
    ``generate_model_id`` / ``parse_model_id`` scheme
    (``ml-service/ml_service/training/ml/config_schema.py``):
    ``{ASSET_GROUP}_{ASSET}_{TARGET_TYPE}_{MODEL_TYPE}_{TIMEFRAME}_V{N}``.
    :func:`~unified_api_contracts.canonical.crosscutting._mvp_scope_predicate.is_model_mvp`
    matches on those SAME decomposed identity components. **UAC never imports
    ml-service** (a T4 service depends on UAC, never the reverse — see
    ``codex/04-architecture/tier-and-import-architecture.md``): a caller parses
    a raw ``model_id`` string with ml-service's own ``parse_model_id()``
    LOCALLY (in ml-service's or a consumer's own codebase, which already
    depends on ml-service) and passes the decomposed axes to
    ``is_model_mvp`` — mirrors how
    :func:`~unified_api_contracts.canonical.crosscutting._mvp_scope_predicate.is_mvp`
    takes plain ``venue``/``instrument_type``/``data_type`` args rather than an
    ``InstrumentCatalogEntry`` object imported from instruments-service.

    Grain (everything-or-nothing, mirrors the per-cell rules in
    ``_mvp_scope_rules.py``): a model_id is MVP iff its
    ``(asset_group, target_type, model_type)`` triple is declared AND
    (``assets`` is empty OR its ``asset`` is a member) AND (``timeframes`` is
    empty OR its ``timeframe`` is a member) — see :func:`is_model_mvp`.

    Casing convention (the rule's frozensets must be declared in these cases
    — ``is_model_mvp`` normalises its OWN inputs to match before comparing,
    mirroring ``generate_model_id``'s own casing):
        * ``asset_groups`` / ``model_types`` / ``assets``: UPPERCASE (matches
          ``generate_model_id``'s ``.upper()`` calls on those segments).
        * ``target_types``: lowercase, underscore-separated (matches
          ``parse_model_id``'s ``parts[2].replace("-", "_")`` — the id itself
          hyphenates target_type, e.g. ``swing-high``; the parsed dict key
          restores the underscore form ``swing_high``).
        * ``timeframes``: lowercase (the id segment is passed through
          ``generate_model_id`` unmodified; every observed timeframe token in
          ml-service config today is already lowercase, e.g. ``1h``/``4h``).

    Attributes:
        asset_groups: Frozenset of MVP asset_group tokens.
        target_types: Frozenset of MVP target_type tokens.
        model_types: Frozenset of MVP model_type tokens.
        assets: Optional frozenset of MVP asset tokens. Empty -> every asset
            is in scope for an otherwise-in-scope (asset_group, target_type,
            model_type) triple.
        timeframes: Optional frozenset of MVP timeframe tokens. Empty -> every
            timeframe is in scope.

    TODO(mvp-scope): operator sign-off on concrete membership — this ships
        with a CONSERVATIVE EMPTY default (matches nothing) pending a Phase-3
        ruling on what "MVP models" means (there is no existing ml-service
        model-OUTPUT tracking/manifest surface yet to derive an objective
        default from, unlike DeFi's "everything we currently produce" v13
        derivation — see ``mvp_scope_catalogue_tagging_2026_06_08.md`` P2b's
        follow-up note). Mirrors the conservative-default convention this
        module uses elsewhere pending operator sign-off (``mvp_scope.py``
        module docstring's TODO note). Structurally ready: the moment
        membership axes are declared here, :func:`is_model_mvp` starts
        returning ``True`` for exactly those cells with no code change.
    """

    asset_groups: frozenset[str] = field(default_factory=frozenset)
    target_types: frozenset[str] = field(default_factory=frozenset)
    model_types: frozenset[str] = field(default_factory=frozenset)
    assets: frozenset[str] = field(default_factory=frozenset)
    timeframes: frozenset[str] = field(default_factory=frozenset)

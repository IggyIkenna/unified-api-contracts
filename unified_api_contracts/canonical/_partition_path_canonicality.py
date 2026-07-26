"""Path-canonicality validator behind the :mod:`partition_paths` facade.

Split out of :mod:`unified_api_contracts.canonical.partition_paths` (2026-07-26
>900-line ratchet — the facade had grown to 1,297L) so the facade keeps the
``build_*_partition_path`` writers + :func:`~unified_api_contracts.canonical.partition_paths.candidate_parquet_paths`
dispatcher, and this module carries the READER-side validator (failure class
C3 — ``data_pipeline_hardening_self_monitoring_2026_06_22.md`` Phase 3 / Phase 4).

The ``build_*_partition_path`` builders (still on the facade) CONSTRUCT
canonical paths; :func:`is_canonical` here is the inverse — it parses an
arbitrary GCS path and asserts it matches the canonical shape, catching the
documented drift classes that have silently corrupted the manifest:
  - ``day-YYYY-MM-DD`` hyphen dir instead of ``day=YYYY-MM-DD``
  - a glued ``VENUE-CHAIN`` venue token instead of separate
    ``venue=.../chain=...`` segments (the legacy PROTOCOL-CHAIN overload)
  - a glued ``V{N}`` version inside the venue token (e.g. ``AAVEV3`` vs
    ``AAVE_V3``)
  - an ``asset_group=`` value outside the closed set
  - a missing ``pipeline_mode={mode}_{source}/`` segment (only when
    ``require_pipeline_mode=True`` — bare back-compat paths the builders
    still emit are accepted by default)

Pragmatic, not a full grammar: it catches the documented drift shapes, and
round-trips against every ``build_*_partition_path`` output (see the unit
tests). Used by the Phase 3 hygiene orchestrator and the Phase 4 writer-side
assert. Registry SSOT: DP-PATH-001..004.

Import surface is UNCHANGED for consumers: every name here is re-exported by
``partition_paths`` (and the ``gcs_paths`` / root facades) — import from
there, not from this private module.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Final

from unified_api_contracts.canonical.gcs_paths import AssetGroup

# Hive partition key for the asset_group axis. Canonical wire-format value.
# Legacy on-disk objects use ``category=`` — readers that need both should try
# canonical first then fall back, but new writes use this key.
ASSET_GROUP_HIVE_KEY = "asset_group"

# Bucket-relative root prefix shared by all market-tick parquets across every
# asset_group. Includes the trailing ``/``. SSOT — never duplicate this string
# in writer code or readers; import it from here.
RAW_TICK_DATA_PREFIX = "raw_tick_data/by_date/"

# Derived-candle root prefix (MDPS). Same buckets as RAW_TICK_DATA_PREFIX, a
# sibling top-level tree — candle_feature_canonical_path_divergence_2026_07_20.md
# todo 10 / data_pipeline_reconciliation_skill_2026_07_20.md todo 39. Sports
# candles live under a DIFFERENT root (``processed/``, not ``processed_candles/``)
# and stay out of scope — they fall through to the unrecognized-prefix branch.
PROCESSED_CANDLES_PREFIX = "processed_candles/by_date/"

# instrument_types that bundle an entire chain into a single file per
# underlying per day. Mirrors MTDS
# ``cefi/tardis_shared.py::CHAIN_INSTRUMENT_TYPES``.
CEFI_CHAIN_INSTRUMENT_TYPES: frozenset[str] = frozenset({"options_chain", "futures_chain"})

# instrument_types that bundle an entire chain into a single file per
# underlying per day. Mirrors MTDS
# ``tradfi/tradfi_shared.py::CHAIN_INSTRUMENT_TYPES`` and the CeFi v6 chain
# layout. ``combo`` is deliberately EXCLUDED (its leg-aware id format is
# unsettled — combo chains keep the bare ``underlying=.../ticks.parquet``
# fan-in without the quote/margin tail).
TRADFI_CHAIN_INSTRUMENT_TYPES: frozenset[str] = frozenset({"options_chain", "futures_chain"})

# Single-instrument tradfi types whose canonical shard filename is the FULL
# instrument_id (``NYSE:EQUITY:ABBV-USD.parquet``). Mirrors MTDS
# ``tradfi/tradfi_shared.py::SINGLE_INSTRUMENT_TYPES`` minus ``combo`` (excluded,
# bare-symbol). The write-time guard enforces the full-id filename for THESE
# itypes only — special bundle types (``event_contract`` / ``combo``) that do
# not yet carry a canonical id are left alone.
TRADFI_SINGLE_INSTRUMENT_TYPES: frozenset[str] = frozenset(
    {"equity", "etf", "index", "currency", "bond", "cds", "commodity", "future", "option", "spot_pair"}
)

_CANONICAL_ASSET_GROUPS: Final[frozenset[str]] = frozenset(member.value for member in AssetGroup)
"""Closed set of ``asset_group=`` hive values: {cefi, defi, tradfi, sports, prediction}."""

# A canonical ``day=`` partition value is an ISO date ``YYYY-MM-DD``.
_DAY_VALUE_RE: Final[re.Pattern[str]] = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Canonical pipeline_mode value is ``{mode}_{source}`` (mode ∈ batch/live/replay),
# optionally ``{mode}_{source}_{transport}``. The vendor source token may itself
# carry underscores, so we only assert the leading mode + at least one source
# segment separated by ``_``.
_PIPELINE_MODE_VALUE_RE: Final[re.Pattern[str]] = re.compile(r"^(batch|live|replay)_[a-z0-9]+(?:_[a-z0-9]+)*$")

# A glued ``V{N}`` version suffix directly fused onto an alphanumeric token
# (e.g. ``AAVEV3`` / ``UNISWAPV3``) — the canonical form separates it with an
# underscore (``AAVE_V3`` / ``UNISWAP_V3``).
_GLUED_VERSION_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9]V\d")


class CanonicalViolationClass(StrEnum):
    """Which QUESTION a canonical-path violation answers.

    Path-STRUCTURE canonicality and instrument-id FORM canonicality are
    ORTHOGONAL — neither alone proves a path is canonical:

    ``STRUCTURAL``
        The hive skeleton: canonical prefix, ``day=YYYY-MM-DD``, ``key=value``
        partition segments, ``pipeline_mode={mode}_{source}``, the closed
        ``asset_group=`` set, the glued ``VENUE-CHAIN`` / ``V{N}`` guards and
        the tradfi chain quote/margin tail.
    ``ID_FORM``
        The FILENAME STEM: whether the per-instrument shard is named for a
        canonical ``instrument_id`` (``VENUE:ITYPE:BASE-QUOTE[@LIN|@INV]…``)
        rather than a raw venue wire symbol (``ADAF0:USTF0``) or a
        double-wrapped ``VENUE:ITYPE:<raw wire>`` catalogue-miss id.

    Until 2026-07-20 this module validated the stem for ``asset_group=tradfi``
    single-instrument shards ONLY, so a CeFi corpus carrying ~811,200
    wire-named objects came back CANONICAL (zero violations) from the machine
    oracle — a FALSE-CLEAN verdict for the exact defect the four-surface
    reconciliation procedure exists to catch. Both classes are now reported by
    DEFAULT; ``violation_classes=`` narrows the answer for callers that must
    enforce one class at a time. SSOT:
    ``plans/active/issues/canonical_path_oracle_blind_to_filename_stem_2026_07_20.md``.
    """

    STRUCTURAL = "structural"
    ID_FORM = "id_form"


# Canonical instrument_id shape (the ID-FORM oracle). Mirrors the resolver SSOT
# ``VENUE:ITYPE:BASE-QUOTE[@LIN|@INV][-YYYYMMDD][-STRIKE-C|P]`` plus the COMBO
# arm (COMBO ids are canonical but carry a free-form tail). Also covers the
# chain-less DeFi ``PERPETUAL`` lane — ``VENUE:PERPETUAL:BASE-QUOTE`` —
# which deliberately has NO ``-CHAIN`` suffix (routes the cefi-simple builder
# branch, see ``canonical_id_builder.py``'s dispatch table).
_CANONICAL_INSTRUMENT_ID_RE: Final[re.Pattern[str]] = re.compile(
    r"^[A-Z0-9._-]+:(PERPETUAL|FUTURE|OPTION|SPOT_PAIR):[A-Z0-9]+-[A-Z0-9]+"
    r"(@(LIN|INV))?(-\d{8})?(-\d+(\.\d+)?-[CP])?$"
)
_COMBO_INSTRUMENT_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Z0-9._-]+:COMBO:.+$")

# Canonical DeFi instrument_id shape (ID-FORM oracle widening, 2026-07-21) — the
# ratified grammar per DeFi type (``defi_consolidated_closeout_2026_07_18.md``
# "Instrument-uid grammar per DeFi type"): base = ``VENUE-CHAIN:TYPE:SYMBOL``,
# DeFi being the only asset group whose venue segment carries a ``-CHAIN``
# suffix (the venue itself may be compound, e.g. ``ETHERFI-GOV-ETHEREUM``, so
# the venue-chain segment requires only >=1 hyphen, not exactly one). The
# per-type SYMBOL variants (POOL glues its fee tier INTO the symbol with a
# hyphen — ``TOKEN0-TOKEN1[-FEE_BPS]``, operator ruling 2026-07-18; A_TOKEN /
# DEBT_TOKEN append an isolated-market id the same way; a Curve/Balancer
# multi-token pool symbol is an arbitrary-length hyphen chain; a bare
# LST/YIELD_BEARING/STAKING/SPOT_ASSET/RESTAKING token has zero extra
# segments) all reduce to the SAME hyphen-joined-segment shape, so one
# permissive symbol class covers every DeFi type without per-type
# sub-patterns. Symbol case is PRESERVED (not upper-cased, unlike CeFi/TradFi)
# because on-chain token symbols are case-sensitive (``aUSDC``, ``stETH``,
# ``variableDebtUSDC``). The chain-less ``PERPETUAL`` DeFi lane is
# deliberately ABSENT from the type alternation here — it already matches
# :data:`_CANONICAL_INSTRUMENT_ID_RE` above. ``LENDING`` (the legacy flat
# lending type) stays in the alternation for the migration interim — see
# ``defi_consolidated_closeout_2026_07_18.md`` "Lending — ONE SSOT".
_DEFI_INSTRUMENT_ID_RE: Final[re.Pattern[str]] = re.compile(
    r"^[A-Z0-9_]+(?:-[A-Z0-9_]+)+:"
    r"(?:SPOT_ASSET|POOL|DEX_POOL|A_TOKEN|DEBT_TOKEN|LST|YIELD_BEARING|STAKING|RESTAKING|"
    r"SOLANA_AMM_POOL|SOLANA_LENDING|SOLANA_VAULT|LENDING):"
    r"[A-Za-z0-9_.]+(?:-[A-Za-z0-9_.]+)*$"
)

# Fan-in shard filenames that legitimately carry NO per-instrument stem: chain
# bundles (``underlying=…/ticks.parquet``) and the symbol-less prediction
# ``book_snapshot_5`` fallback. These must NEVER be flagged by the ID-FORM
# oracle — they are canonical BY SHAPE, not by stem.
_STEMLESS_FAN_IN_FILE_NAMES: Final[frozenset[str]] = frozenset({"ticks.parquet"})

# Asset groups whose per-instrument shard filename is contractually the FULL
# canonical instrument_id. ``sports`` / ``prediction`` are DELIBERATELY absent:
# their ids route through domain-specific builders (fixture ids, condition
# ids) whose grammar is not the ``VENUE:ITYPE:BASE-QUOTE``/``VENUE-CHAIN:TYPE:
# SYMBOL`` shape, so applying this regex there would manufacture false
# violations. ``prediction``'s id grammar is explicitly OUT OF SCOPE here — it
# is its own future closeout (``defi_consolidated_closeout_2026_07_18.md``
# Track 1). ``defi`` widened 2026-07-21 — the grammar is ratified (see
# :data:`_DEFI_INSTRUMENT_ID_RE`); this is expected to surface a large
# NON_CANONICAL population on the current corpus (today's DeFi single-instrument
# filenames are the bare ``symbol`` column, not yet the wrapped id — see
# ``market-tick-data-service/.../partitioned_writer.py::_resolve_file_symbol``,
# "defi/sports are untouched"), the same honest-disclosure outcome the CeFi
# widening produced (20.82% canonical, not 100%) — NOT a bug in this checker.
# Widening ``prediction`` requires an id grammar for that asset group first.
_ID_FORM_CHECKED_ASSET_GROUPS: Final[frozenset[str]] = frozenset({"cefi", "defi"})


def is_canonical_instrument_id(candidate: str) -> bool:
    """True iff ``candidate`` is a canonical instrument_id (incl. the COMBO arm).

    The ID-FORM half of canonicality — deliberately independent of
    :func:`canonical_path_violations`'s path-STRUCTURE checks. A raw venue wire
    symbol (``ADAF0:USTF0``), a double-wrapped catalogue-miss id
    (``BITFINEX-FUTURES:PERPETUAL:ADAF0:USTF0``) and a bare symbol (``BTCUSD``)
    all return False. Recognises the CeFi/TradFi ``VENUE:ITYPE:BASE-QUOTE``
    shape, the COMBO arm, and the DeFi ``VENUE-CHAIN:TYPE:SYMBOL`` shape
    (:data:`_DEFI_INSTRUMENT_ID_RE`) — the three alternatives never overlap
    (disjoint TYPE-token alternations), so widening acceptance here is
    additive and cannot turn a previously-rejected CeFi/TradFi stem into a
    false positive.
    """
    return bool(
        _CANONICAL_INSTRUMENT_ID_RE.match(candidate)
        or _COMBO_INSTRUMENT_ID_RE.match(candidate)
        or _DEFI_INSTRUMENT_ID_RE.match(candidate)
    )


def _tradfi_path_violations(
    kv: dict[str, str], partition_segments: list[str], file_name: str
) -> tuple[list[str], list[str]]:
    """(structural, id_form) violations for a tradfi shard — extracted from
    :func:`canonical_path_violations` to keep its cyclomatic complexity in
    budget (ruff C901). Caller has already confirmed ``asset_group == "tradfi"``.
    """
    structural: list[str] = []
    id_form: list[str] = []
    it_value = kv.get("instrument_type")
    if kv.get("pipeline_mode") == "batch_massive":
        structural.append(
            "tradfi pipeline_mode=batch_massive is forbidden — Massive is purged; "
            "Databento is the batch source of truth"
        )
    # ── garbage-underlying guard (chain + combo bundles) ─────────────────────
    # A tradfi CHAIN/COMBO bundle carries ``underlying=<ROOT>``. The forensic
    # sweep found 189,830 objects whose ``underlying=`` was a numeric CBOE
    # globex GROUP code (``12``/``13``) or an opaque CBOE user-defined leg
    # code (``GN``/``VT``/``3W``) — the product root is UNRECOVERABLE from the
    # path, so a fresh write MUST fail loud (shard-level isolation → honest
    # ``attempted_failed``) rather than fake-canonicalise a garbage bundle.
    # Real roots (``SP500``/``MES``/``XAB``) and resolved named-spread combos
    # (``WTI-BZ``/``NAT-GAS-HH``) PASS. Covers combo too (not in
    # TRADFI_CHAIN_INSTRUMENT_TYPES): the opaque ``UD:1V: GN`` combos land
    # here. SSOT: tradfi_canonical_path_migration_design_2026_07_19.md.
    underlying_value = kv.get("underlying")
    if underlying_value is not None:
        # Call-time import (canonical→registry) — avoids the load-time cycle
        # (registry/__init__ imports canonical); at call time both are loaded.
        from unified_api_contracts.registry.tradfi_symbology import (
            is_recognized_tradfi_underlying,
        )

        if not is_recognized_tradfi_underlying(underlying_value):
            structural.append(
                f"tradfi underlying={underlying_value!r} is not a real product root / "
                "named-spread combo (numeric globex group code or opaque CBOE "
                "user-defined leg code) — quarantine, never fake-canonicalize"
            )
    if it_value in TRADFI_CHAIN_INSTRUMENT_TYPES:
        # chain shard tail MUST be underlying=.../quote=.../margin=.../ticks.parquet
        tail_keys = [seg.partition("=")[0] for seg in partition_segments[-3:]]
        if tail_keys != ["underlying", "quote", "margin"] or file_name != "ticks.parquet":
            structural.append(
                f"tradfi {it_value} shard must end "
                "'.../underlying=<BASE>/quote=<Q>/margin=<M>/ticks.parquet' "
                f"(got tail {[*partition_segments[-3:], file_name]!r})"
            )
    elif it_value in TRADFI_SINGLE_INSTRUMENT_TYPES:
        # single-instrument shard: filename MUST be the full canonical
        # instrument_id (VENUE:TYPE:SYMBOL...), never a bare symbol or a
        # symbol-less ticks.parquet fan-in. Scoped to the canonical single
        # itypes only — ``combo`` (bare-symbol, leg-id unsettled) and special
        # bundle types like ``event_contract`` are deliberately NOT enforced.
        if file_name == "ticks.parquet":
            id_form.append(
                "tradfi single-instrument shard filename must be the full canonical "
                "instrument_id, got a symbol-less 'ticks.parquet' fan-in"
            )
        elif ":" not in file_name:
            id_form.append(
                f"tradfi single-instrument shard filename {file_name!r} must be the full "
                "canonical instrument_id ('VENUE:TYPE:SYMBOL...'), got a bare symbol"
            )
    return structural, id_form


def _partition_key_index(partition_segments: list[str], key: str) -> int | None:
    """Index of the first ``{key}=...`` segment in ``partition_segments``, or ``None``."""
    prefix = f"{key}="
    for idx, seg in enumerate(partition_segments):
        if seg.startswith(prefix):
            return idx
    return None


def _defi_partition_order_violations(partition_segments: list[str], kv: dict[str, str]) -> list[str]:
    """STRUCTURAL pin for the DeFi flat canonical shape: venue-BEFORE-chain, lowercase
    ``instrument_type``, ``pipeline_mode=`` (when present) left of ``asset_group=``.

    ``build_defi_partition_path`` (the single DeFi writer SSOT) emits an UNCONDITIONAL
    fixed template — ``day=/[pipeline_mode=]/asset_group=defi/venue=/chain=/
    instrument_type=/data_type=/{file}`` — so any REAL output of that one function
    always satisfies every check below; this can never produce a false positive
    against a canonical write. Before this, ``canonical_path_violations`` only
    checked segment PRESENCE/VALUES via a ``key -> value`` dict, never ORDER, so a
    second writer that spliced ``chain=`` ahead of ``venue=``
    (``market_tick_data_service.live.websocket_runner.live_tick_blob_path``,
    mtds@3043f2dc1 2026-06-26 — fixed alongside this check) read as CANONICAL for
    nearly a month. SSOT: codex/02-data/defi-canonical-naming-ssot.md,
    plans/active/defi_consolidated_closeout_2026_07_18.md ("pin the flat canonical
    path shape ... kill the second dexpool writer path").
    """
    violations: list[str] = []

    venue_idx = _partition_key_index(partition_segments, "venue")
    chain_idx = _partition_key_index(partition_segments, "chain")
    if venue_idx is not None and chain_idx is not None and chain_idx < venue_idx:
        violations.append(
            "defi path has 'chain=' before 'venue=' — canonical order is venue-before-chain "
            "('venue={V}/chain={C}/...', never the reverse)"
        )

    itype_value = kv.get("instrument_type")
    if itype_value is not None and itype_value != itype_value.lower():
        violations.append(
            f"instrument_type={itype_value!r} is not lowercase — the defi hive partition "
            "value must be lowercase (e.g. 'a_token', not 'A_TOKEN'; the canonical upper-case "
            "form lives only inside the instrument_id column)"
        )

    pm_idx = _partition_key_index(partition_segments, "pipeline_mode")
    ag_idx = _partition_key_index(partition_segments, ASSET_GROUP_HIVE_KEY)
    if pm_idx is not None and ag_idx is not None and pm_idx > ag_idx:
        violations.append(
            "defi path has 'pipeline_mode=' AFTER 'asset_group=' — canonical position is "
            "immediately after 'day=' and BEFORE 'asset_group='"
        )

    return violations


def _cefi_chain_tail_violations(
    asset_group: str | None, kv: dict[str, str], partition_segments: list[str], file_name: str
) -> list[str]:
    """STRUCTURAL violations for a cefi ``options_chain``/``futures_chain`` shard's tail.

    Operator ruling 2026-07-21: the cefi chain-tail v6 shape
    (``underlying=<BASE>/quote=<Q>/margin=<M>/ticks.parquet``) is canonical
    EVERYWHERE — the bare v5 tail (no quote/margin) is LOSSY (USD-vs-USDT /
    linear-vs-inverse chains on the same underlying collide and overwrite) and
    must not remain anywhere. Enforced write-time by the MTDS
    ``PartitionedTickWriter`` (asset_group=cefi) so a regressing backfill fails
    loud instead of silently reintroducing the collision. SSOT:
    cefi_chain_tail_v6_canonicalisation_2026_07_21.md.
    """
    if asset_group != "cefi":
        return []
    it_value = kv.get("instrument_type")
    if it_value not in CEFI_CHAIN_INSTRUMENT_TYPES:
        return []
    tail_keys = [seg.partition("=")[0] for seg in partition_segments[-3:]]
    if tail_keys == ["underlying", "quote", "margin"] and file_name == "ticks.parquet":
        return []
    return [
        f"cefi {it_value} shard must end "
        "'.../underlying=<BASE>/quote=<Q>/margin=<M>/ticks.parquet' "
        f"(got tail {[*partition_segments[-3:], file_name]!r}) — v5 bare chain "
        "tail is a lossy USD-vs-USDT / linear-vs-inverse collision, RULED v6-only "
        "everywhere (operator 2026-07-21)"
    ]


def _stem_id_form_violations(*, asset_group: str, instrument_type: str | None, file_name: str) -> list[str]:
    """ID-FORM violations for a single-instrument shard's filename stem.

    Returns ``[]`` for every legitimately stem-less shape (chain itypes and the
    ``ticks.parquet`` fan-in) and for asset groups outside
    :data:`_ID_FORM_CHECKED_ASSET_GROUPS`.
    """
    if asset_group not in _ID_FORM_CHECKED_ASSET_GROUPS:
        return []
    if file_name in _STEMLESS_FAN_IN_FILE_NAMES:
        return []
    if instrument_type in CEFI_CHAIN_INSTRUMENT_TYPES:
        return []
    stem = file_name.removesuffix(".parquet")
    if is_canonical_instrument_id(stem):
        return []
    expected_grammar = (
        "'VENUE-CHAIN:TYPE:SYMBOL'"
        if asset_group == "defi"
        else "'VENUE:ITYPE:BASE-QUOTE[@LIN|@INV][-YYYYMMDD][-STRIKE-C|P]'"
    )
    return [
        f"{asset_group} single-instrument shard filename {file_name!r} is not a canonical "
        f"instrument_id ({expected_grammar}) — raw venue wire symbol / bare symbol or a "
        "double-wrapped catalogue-miss id"
    ]


def _select_violation_classes(
    structural: list[str],
    id_form: list[str],
    violation_classes: frozenset[CanonicalViolationClass] | None,
) -> list[str]:
    """Flatten the two violation classes down to the caller's requested selection."""
    if violation_classes is None:
        return [*structural, *id_form]
    selected: list[str] = []
    if CanonicalViolationClass.STRUCTURAL in violation_classes:
        selected.extend(structural)
    if CanonicalViolationClass.ID_FORM in violation_classes:
        selected.extend(id_form)
    return selected


def _candle_path_violations(
    remainder: str,
    *,
    require_candle_migration_complete: bool,
) -> list[str]:
    """Violations for a ``processed_candles/by_date/...`` path (the LOCKED shape,
    CORRECTED RULING 2026-07-21): ``day=/pipeline_mode=/timeframe=/data_type=/
    instrument_type=/venue=/{canonical_id}.parquet`` for cefi/tradfi/defi;
    prediction candles use ``instrument_type=`` as the terminal axis in place of
    ``venue=`` and never carry ``pipeline_mode=``.

    Migration-window suppression (mirrors taxonomy exception AE-6): the whole
    existing corpus predates this ruling, so a missing ``instrument_type=`` (all
    shapes) or a missing ``pipeline_mode=`` (venue-shaped only — prediction never
    had it) is SUPPRESSED by default (``require_candle_migration_complete=False``)
    and only flagged once the caller asserts the migration has completed. Genuine
    defects (empty stem, malformed values, missing ``day=``/``timeframe=``/
    ``data_type=``) are NEVER suppressed.
    """
    violations: list[str] = []
    segments = remainder.split("/")
    partition_segments = segments[:-1]
    file_name = segments[-1]

    if not partition_segments:
        violations.append("no partition segments after the prefix")
        return violations

    day_seg = partition_segments[0]
    if day_seg.startswith("day-"):
        violations.append(f"legacy hyphen day segment {day_seg!r} — must be 'day=YYYY-MM-DD'")
    elif not day_seg.startswith("day="):
        violations.append(f"first partition is {day_seg!r}, expected 'day=YYYY-MM-DD'")
    elif not _DAY_VALUE_RE.match(day_seg[len("day=") :]):
        violations.append(f"day value {day_seg[len('day=') :]!r} is not ISO YYYY-MM-DD")

    kv: dict[str, str] = {}
    for seg in partition_segments[1:]:
        if "=" not in seg:
            violations.append(f"non-canonical partition segment {seg!r} (expected 'key=value')")
            continue
        key, _, value = seg.partition("=")
        if key == "pipeline_mode" and not _PIPELINE_MODE_VALUE_RE.match(value):
            violations.append(
                f"pipeline_mode value {value!r} is not canonical '{{mode}}_{{source}}' "
                "(mode ∈ batch/live/replay, source = vendor token)"
            )
        kv[key] = value

    if "timeframe" not in kv:
        violations.append("missing 'timeframe=' partition segment")
    if "data_type" not in kv:
        violations.append("missing 'data_type=' partition segment")

    if require_candle_migration_complete:
        if "instrument_type" not in kv:
            violations.append(
                "missing 'instrument_type=' partition segment (required once the candle "
                "migration is complete — LOCKED shape, 2026-07-21)"
            )
        if "venue" in kv and "pipeline_mode" not in kv:
            violations.append(
                "missing 'pipeline_mode={mode}_{source}/' segment (required once the "
                "candle migration is complete — venue-shaped candles only, prediction exempt)"
            )

    # Empty instrument stem: a chain-bundle write that never got renamed to the
    # bundled leaf (measured defect, e.g. '.../underlying=BTC/.parquet').
    stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
    if not stem:
        violations.append(f"empty instrument stem in filename {file_name!r} — unattributable to a shard")

    return violations


def canonical_path_violations(
    path: str,
    *,
    require_pipeline_mode: bool = False,
    require_candle_migration_complete: bool = False,
    violation_classes: frozenset[CanonicalViolationClass] | None = None,
) -> list[str]:
    """Return the list of canonical-form violations for ``path`` (empty == canonical).

    Parses a bucket-relative GCS partition path (the full
    ``raw_tick_data/by_date/...`` shape the ``build_*_partition_path`` builders
    emit) and returns one human-readable violation string per documented
    drift class found. An empty list means the path is canonical.

    Args:
        path: Bucket-relative path (no ``gs://bucket/`` prefix). A leading
            slash is tolerated and stripped.
        require_pipeline_mode: When True, a path lacking the
            ``pipeline_mode={mode}_{source}/`` segment left of ``asset_group=``
            is a violation. Default False accepts the back-compat bare paths
            the builders still emit (the segment is canonical-but-optional for
            CeFi/Prediction and back-compat for DeFi/TradFi). Applies to
            ``raw_tick_data/`` paths only.
        require_candle_migration_complete: When True, a ``processed_candles/``
            path is checked against the fully-migrated LOCKED shape (missing
            ``instrument_type=``/``pipeline_mode=`` is a violation). Default
            False suppresses those two during the migration_pending window
            (mirrors taxonomy exception AE-6) — see
            ``codex/02-data/mdps-candle-canonical-reconciliation.md``. No
            effect on ``raw_tick_data/`` paths.
        violation_classes: Restrict the answer to these
            :class:`CanonicalViolationClass` members. Default ``None`` reports
            BOTH classes — path STRUCTURE *and* filename instrument-id FORM.
            Pass ``frozenset({CanonicalViolationClass.STRUCTURAL})`` for the
            skeleton-only question (the pre-2026-07-20 behaviour). Every
            ``processed_candles/`` violation is classified STRUCTURAL.

    Note:
        Structure and id-form are ORTHOGONAL questions — an empty list means
        canonical only with respect to the classes actually requested.
    """
    structural: list[str] = []
    id_form: list[str] = []
    cleaned = path.lstrip("/")

    if cleaned.startswith(PROCESSED_CANDLES_PREFIX):
        structural.extend(
            _candle_path_violations(
                cleaned[len(PROCESSED_CANDLES_PREFIX) :],
                require_candle_migration_complete=require_candle_migration_complete,
            )
        )
        return _select_violation_classes(structural, id_form, violation_classes)

    if not cleaned.startswith(RAW_TICK_DATA_PREFIX):
        structural.append(
            f"path does not start with a recognized canonical prefix "
            f"({RAW_TICK_DATA_PREFIX!r} or {PROCESSED_CANDLES_PREFIX!r})"
        )
        return _select_violation_classes(structural, id_form, violation_classes)

    remainder = cleaned[len(RAW_TICK_DATA_PREFIX) :]
    segments = remainder.split("/")
    # Last segment is the file name; the rest are hive ``key=value`` partitions.
    partition_segments = segments[:-1]

    # ── day= segment (must be the first partition, value YYYY-MM-DD) ──────────
    if not partition_segments:
        structural.append("no partition segments after the prefix")
        return _select_violation_classes(structural, id_form, violation_classes)

    day_seg = partition_segments[0]
    if day_seg.startswith("day-"):
        structural.append(f"legacy hyphen day segment {day_seg!r} — must be 'day=YYYY-MM-DD'")
    elif not day_seg.startswith("day="):
        structural.append(f"first partition is {day_seg!r}, expected 'day=YYYY-MM-DD'")
    elif not _DAY_VALUE_RE.match(day_seg[len("day=") :]):
        structural.append(f"day value {day_seg[len('day=') :]!r} is not ISO YYYY-MM-DD")

    # ── locate the keyed partition map (key=value segments) ──────────────────
    kv: dict[str, str] = {}
    has_pipeline_mode = False
    for seg in partition_segments[1:]:
        if "=" not in seg:
            structural.append(f"non-canonical partition segment {seg!r} (expected 'key=value')")
            continue
        key, _, value = seg.partition("=")
        if key == "pipeline_mode":
            has_pipeline_mode = True
            if not _PIPELINE_MODE_VALUE_RE.match(value):
                structural.append(
                    f"pipeline_mode value {value!r} is not canonical '{{mode}}_{{source}}' "
                    "(mode ∈ batch/live/replay, source = vendor token)"
                )
        kv[key] = value

    # ── asset_group= (must be present + in the closed set) ───────────────────
    asset_group_value = kv.get(ASSET_GROUP_HIVE_KEY)
    if asset_group_value is None:
        structural.append(f"missing '{ASSET_GROUP_HIVE_KEY}=' partition segment")
    elif asset_group_value not in _CANONICAL_ASSET_GROUPS:
        structural.append(
            f"{ASSET_GROUP_HIVE_KEY}={asset_group_value!r} is outside the canonical set "
            f"{sorted(_CANONICAL_ASSET_GROUPS)}"
        )

    # ── pipeline_mode required-but-missing (opt-in) ──────────────────────────
    if require_pipeline_mode and not has_pipeline_mode:
        structural.append(
            "missing 'pipeline_mode={mode}_{source}/' segment left of "
            f"'{ASSET_GROUP_HIVE_KEY}=' (required for this check)"
        )

    # ── venue= (glued VENUE-CHAIN overload / glued V{N} version) ─────────────
    venue_value = kv.get("venue")
    if venue_value is not None:
        # A hyphen in the venue token is the legacy PROTOCOL-CHAIN glue
        # (e.g. ``AAVE_V3-ETHEREUM``); chain MUST be its own ``chain=`` segment.
        # This is a DEFI-ONLY concern — ``chain`` is a defi axis. CeFi venue names
        # legitimately CONTAIN a hyphen (``BINANCE-FUTURES`` / ``OKX-FUTURES`` /
        # ``BYBIT-FUTURES`` / ``KRAKEN-FUTURES`` — the canonical cefi venue tokens in
        # registry/data_type_capability.py), so flagging every hyphen crashed the cefi
        # LIVE producers at the writer boundary (``venue='BINANCE-FUTURES' carries a
        # glued 'VENUE-CHAIN' token``), silently freezing the deribit/hyperliquid/binance
        # live VMs for hours (2026-06-23). Gate on defi so the legacy-glue guard still
        # protects the on-chain paths without false-flagging cefi/tradfi venue names.
        if asset_group_value == "defi" and "-" in venue_value:
            structural.append(
                f"venue={venue_value!r} carries a glued 'VENUE-CHAIN' token — chain must be a separate 'chain=' segment"
            )
        if _GLUED_VERSION_RE.search(venue_value):
            structural.append(
                f"venue={venue_value!r} carries a glued 'V{{N}}' version — canonical form separates "
                "it with an underscore (e.g. 'AAVE_V3', 'UNISWAP_V3')"
            )

    # ── defi flat canonical shape (venue-before-chain, lowercase itype, pipeline_mode=
    # position) — see _defi_partition_order_violations for the second-writer regression
    # this closes.
    if asset_group_value == "defi":
        structural.extend(_defi_partition_order_violations(partition_segments, kv))

    # ── tradfi canonical shape (chain quote/margin tail + single full-id filename) ──
    # Enforced write-time by the MTDS PartitionedTickWriter (asset_group=tradfi)
    # so a regressing backfill fails loud instead of silently re-diverging the
    # migrated corpus (chain object at underlying=/quote=/margin= vs a manifest
    # atom / new write that dropped the tail). SSOT:
    # plans/active/issues/tradfi_canonical_path_migration_design_2026_07_19.md.
    if asset_group_value == "tradfi":
        _tradfi_structural, _tradfi_id_form = _tradfi_path_violations(kv, partition_segments, segments[-1])
        structural.extend(_tradfi_structural)
        id_form.extend(_tradfi_id_form)

    structural.extend(_cefi_chain_tail_violations(asset_group_value, kv, partition_segments, segments[-1]))

    # ── ID-FORM: the filename stem must BE a canonical instrument_id ─────────
    # The gap this closes: before 2026-07-20 the stem was dropped
    # (``partition_segments = segments[:-1]``) before validation for every
    # asset_group except tradfi, so a CeFi corpus of raw wire stems
    # (``ADAF0:USTF0.parquet``) and double-wrapped catalogue-miss ids
    # (``BITFINEX-FUTURES:PERPETUAL:ADAF0:USTF0.parquet``) measured CANONICAL.
    if asset_group_value is not None:
        id_form.extend(
            _stem_id_form_violations(
                asset_group=asset_group_value,
                instrument_type=kv.get("instrument_type"),
                file_name=segments[-1],
            )
        )

    return _select_violation_classes(structural, id_form, violation_classes)


def canonical_path_violations_classified(
    path: str,
    *,
    require_pipeline_mode: bool = False,
    require_candle_migration_complete: bool = False,
) -> dict[CanonicalViolationClass, list[str]]:
    """Canonical-form violations for ``path`` split by :class:`CanonicalViolationClass`.

    The audit-facing view: reconciliation reports need to say *which* surface
    is non-canonical (a wire-named file under a perfectly-shaped hive skeleton
    is a very different finding from a ``day-2026-05-01`` legacy prefix), and
    an enforcement boundary needs to act on one class at a time. Every class is
    always present as a key; a canonical path maps every class to ``[]``.
    """
    return {
        member: canonical_path_violations(
            path,
            require_pipeline_mode=require_pipeline_mode,
            require_candle_migration_complete=require_candle_migration_complete,
            violation_classes=frozenset({member}),
        )
        for member in CanonicalViolationClass
    }


def is_canonical(
    path: str,
    *,
    require_pipeline_mode: bool = False,
    require_candle_migration_complete: bool = False,
    violation_classes: frozenset[CanonicalViolationClass] | None = None,
) -> bool:
    """True iff ``path`` is a canonical GCS partition path (no drift violations).

    Thin boolean wrapper over :func:`canonical_path_violations` — accepts the
    output of every ``build_*_partition_path`` builder and rejects the
    documented non-canonical drift shapes (hyphen ``day-``, glued
    ``VENUE-CHAIN`` / ``V{N}``, out-of-set ``asset_group=``, a non-canonical
    filename instrument-id stem, and — when ``require_pipeline_mode=True`` — a
    missing ``pipeline_mode=`` segment). Also validates ``processed_candles/``
    paths (see ``require_candle_migration_complete``).

    Like :func:`canonical_path_violations` this answers BOTH the STRUCTURAL and
    the ID_FORM question by default; narrow with ``violation_classes``.
    """
    return not canonical_path_violations(
        path,
        require_pipeline_mode=require_pipeline_mode,
        require_candle_migration_complete=require_candle_migration_complete,
        violation_classes=violation_classes,
    )

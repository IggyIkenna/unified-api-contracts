"""TradFi raw-id canonicalization primitive — Phase-B migration SSOT (2026-07-18).

Single shared implementation for turning a raw, exchange-native TradFi
FUTURE/OPTION id (a bare Databento symbol like ``ESM6``, or one already
``VENUE:TYPE:``-prefixed by the pre-fix IS catalogue adapter, e.g.
``CME:FUTURE:GCQ26``) into the canonical
``VENUE:(FUTURE|OPTION):PRODUCT_ROOT-USD@LIN-YYYYMMDD[-STRIKE-C|P]`` shape —
see ``instrument_id_format_canonicalization_2026_07_08.md`` +
``tradfi_consolidated_closeout_2026_07_18.md`` Phase B ("Promote the shared
primitive ``canonicalize_raw_tradfi_id`` into UAC ... so IS+MTDS+migration+
gate share ONE implementation and can't drift").

Never a silent fallback: every input maps to exactly one :class:`CanonResult`
status.

Reuses (never reimplements):

* ``classify_databento_symbol`` (:mod:`unified_api_contracts.external.databento.databento_classifier`)
  — the SSOT raw-symbol classifier already used by the MTDS/IS writers.
  Lazy-imported inside :func:`_classify` — see that function's docstring
  for why (avoids a real circular-import hazard through this package's
  eager ``internal.reference`` init chain).
* :data:`unified_api_contracts.registry.EXCHANGE_CODE_TO_NAME` — root to
  human-readable underlying (``ES`` -> ``SP500``, ``GC`` -> ``GOLD``,
  ``BRN`` -> ``BRENT``). Roots with no entry (e.g. index tickers like
  ``SPX`` that are already human-readable) pass through unchanged.
* :func:`unified_api_contracts.internal.reference.canonical_id_builder.build_instrument_id`
  — already emits the ``-USD@LIN`` shape (shipped @8b7c4967).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Literal

from unified_api_contracts.internal.reference.canonical_id_builder import build_instrument_id
from unified_api_contracts.internal.reference.instrument import InstrumentType
from unified_api_contracts.registry import EXCHANGE_CODE_TO_NAME

if TYPE_CHECKING:
    from unified_api_contracts.external.databento.databento_classifier import DatabentoClassification

__all__ = [
    "TARGET_TRADFI_DERIVATIVE_ID_RE",
    "CanonResult",
    "CanonStatus",
    "assert_tradfi_derivative_ids_canonical",
    "canonicalize_raw_tradfi_id",
]

# Every input maps to exactly one of these — no silent fallback.
CanonStatus = Literal[
    "OK",
    "QUARANTINE_COMBO",
    "QUARANTINE_CONTINUOUS",
    "QUARANTINE_UNPARSEABLE",
    "ALREADY_CANONICAL",
    "NULL_OR_EMPTY",
]


@dataclass(frozen=True, slots=True)
class CanonResult:
    """Result of :func:`canonicalize_raw_tradfi_id` — never a silent fallback.

    Attributes:
        status: Exactly one :data:`CanonStatus` value.
        canonical_id: The built ``VENUE:TYPE:ROOT-USD@LIN-...`` id for
            ``OK``/``ALREADY_CANONICAL``; ``None`` for every quarantine
            status and for ``NULL_OR_EMPTY``.
        derived_instrument_type: The classifier-derived instrument type
            string (e.g. ``"FUTURE"``, ``"OPTION"``, ``"COMBO"``) once a
            classification was reached; ``None`` when the raw id never got
            that far (``NULL_OR_EMPTY``, or the classifier raised before any
            type was known).
        derived_underlying_human: The human-readable underlying (e.g.
            ``"SP500"``, ``"GOLD"``, ``"SPX"``) for ``OK``/
            ``ALREADY_CANONICAL``; ``None`` otherwise.
    """

    status: CanonStatus
    canonical_id: str | None
    derived_instrument_type: str | None
    derived_underlying_human: str | None


# Target shape asserted by both this module's OK/ALREADY_CANONICAL path and
# the Phase-B/D verify gate below. Every TradFi FUTURE/OPTION canonical id
# carries an explicit -USD quote (operator decision 2026-07-18).
TARGET_TRADFI_DERIVATIVE_ID_RE: Final[re.Pattern[str]] = re.compile(
    r"^[A-Z0-9-]+:(FUTURE|OPTION):[A-Z0-9]+-USD@LIN-\d{8}(-\d+(\.\d+)?-[CP])?$"
)

# Step (a): strip a leading VENUE:TYPE: prefix if present — e.g. the pre-fix
# IS catalogue adapter persisted raw ids as ``CME:FUTURE:GCQ26`` (venue+type
# glued onto the unclassified raw body). The venue segment here is NEVER
# trusted for output — the caller-supplied `venue` argument is authoritative
# (a bare ICE ``BRN_MK0023!`` must not mint ``CME:...`` just because some
# other row happened to carry a ``CME:`` prefix).
_VENUE_TYPE_PREFIX_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Z0-9-]+:[A-Za-z_]+:")

# Step (d): dash-before-strike -> space (event/weekly options,
# ``ECBTCN609-C52500`` -> ``ECBTCN609 C52500``). Surgical: only a dash
# immediately followed by C/P + a digit is treated as a strike separator; a
# bare ``-`` elsewhere is a combo leg-separator and must NOT be touched.
_DASH_STRIKE_RE: Final[re.Pattern[str]] = re.compile(r"-([CP]\d)")

_WHITESPACE_RE: Final[re.Pattern[str]] = re.compile(r"\s")

_MAX_VIOLATIONS_SAMPLE: Final[int] = 50


def _resolve_venue_prefix(body: str) -> str:
    """Strip step (a) — see :data:`_VENUE_TYPE_PREFIX_RE`."""
    match = _VENUE_TYPE_PREFIX_RE.match(body)
    if match is None:
        return body
    return body[match.end() :]


def _normalize_body(body: str) -> str:
    """Apply normalization steps (b)-(d) — the measured-necessary shape fixes.

    Step (a) (the ``VENUE:TYPE:`` prefix strip) and the CBOE ``UD_``
    short-circuit are handled by the caller before this runs.
    """
    # (b) CBOE OPRA O: root prefix (``O:SPX260618C00200000`` -> ``SPX...``).
    if body.startswith("O:"):
        body = body[2:]
    # (c) GCS-safe manifest encoding: `_` -> space (``EW1H0_P2785`` -> ``EW1H0 P2785``).
    body = body.replace("_", " ")
    # (d) dash-before-strike -> space.
    body = _DASH_STRIKE_RE.sub(r" \1", body)
    return body.strip()


def _classify(body: str) -> DatabentoClassification | None:
    """Lazy-imported classify call — returns ``None`` on any parse failure.

    ``databento_classifier.py`` imports the top-level ``unified_api_contracts``
    package at its own module scope. Importing it eagerly at THIS module's
    top level would pull ``external.databento`` into ``internal.reference``'s
    package-init chain — which the top-level ``unified_api_contracts/__init__.py``
    triggers partway through its own execution (before every name
    ``databento_classifier.py`` needs, e.g. ``UNDERLYING_NORMALIZATION``, is
    bound on the still-initializing module) — a real circular-import hazard.
    A local import defers the touch until this function actually runs, by
    which point the package is fully initialized. Same established pattern
    as e.g. ``canonical/crosscutting/liquid_representative.py``.
    """
    from unified_api_contracts.external.databento.databento_classifier import (
        classify_databento_symbol,
    )

    try:
        return classify_databento_symbol(body)
    except ValueError:
        return None


def canonicalize_raw_tradfi_id(raw: str, venue: str, instrument_type: str) -> CanonResult:
    """Canonicalize one raw TradFi FUTURE/OPTION id — the Phase-B SSOT primitive.

    Shared by the IS/MTDS writers, the Phase-B migration scripts, and
    :func:`assert_tradfi_derivative_ids_canonical` so none of them can drift
    from one another (``tradfi_consolidated_closeout_2026_07_18.md`` Phase B).
    Never a silent fallback — every input maps to exactly one
    :class:`CanonResult` status.

    Args:
        raw: The raw persisted id — either a bare exchange-native symbol
            (``ESM6``, ``E1AF0 C1600``, ``EW1H0_P2785``) or one already
            ``VENUE:TYPE:``-prefixed by the pre-fix IS catalogue adapter
            (``CME:FUTURE:GCQ26``). Any embedded VENUE segment is stripped
            and discarded — never trusted for the output venue.
        venue: The row's ``venue`` column (e.g. ``"CME"``, ``"CBOE"``,
            ``"ICE"``) — the ONLY source of truth for the output id's venue
            segment. Never parsed from ``raw`` and never defaulted to
            ``"CME"``.
        instrument_type: The row's stored ``instrument_type`` column.
            Accepted for call-site parity but intentionally NOT trusted —
            live manifest data carries ~400k mislabeled rows (options/combos
            stamped ``FUTURE``); the classifier-derived type is always
            authoritative instead.

    Returns:
        A :class:`CanonResult`.
    """
    del instrument_type  # never trusted — see docstring; classifier-derived type is authoritative.

    if raw is None or not raw.strip():
        return CanonResult(
            status="NULL_OR_EMPTY",
            canonical_id=None,
            derived_instrument_type=None,
            derived_underlying_human=None,
        )

    original = raw.strip()
    venue_up = venue.strip().upper()

    # Already-canonical fast path: if the FULL raw string (including any
    # VENUE:TYPE: prefix) already matches TARGET and its venue segment
    # agrees with the caller-supplied `venue`, it's already canonical — do
    # NOT feed it through the raw-symbol classifier. A `VENUE:TYPE:` id's
    # body (e.g. ``SP500-USD@LIN-20260619``) is not a valid raw Databento
    # symbol shape and would spuriously fail to classify.
    if TARGET_TRADFI_DERIVATIVE_ID_RE.match(original):
        parts = original.split(":", 2)
        if len(parts) == 3 and parts[0] == venue_up:
            _venue_segment, type_segment, symbol_part = parts
            root = symbol_part.split("-USD@LIN", 1)[0]
            return CanonResult(
                status="ALREADY_CANONICAL",
                canonical_id=original,
                derived_instrument_type=type_segment,
                derived_underlying_human=root,
            )

    body = _resolve_venue_prefix(original)

    # CBOE user-defined strategy — quarantine as COMBO without attempting
    # classification. The classifier's CBOE_UD_RE pattern requires literal
    # colons (``UD:1V: GN 0113805462``) which our GCS-safe `_`->space
    # normalization does not reconstruct (colons are never re-derived from
    # underscores), so a `UD_...`/`UD:...` body must be special-cased here —
    # otherwise it would raise inside the classifier and get mislabeled
    # QUARANTINE_UNPARSEABLE instead of QUARANTINE_COMBO.
    if body.startswith("UD_") or body.startswith("UD:"):
        return CanonResult(
            status="QUARANTINE_COMBO",
            canonical_id=None,
            derived_instrument_type=InstrumentType.COMBO.value,
            derived_underlying_human=None,
        )

    body = _normalize_body(body)
    if not body:
        return CanonResult(
            status="NULL_OR_EMPTY",
            canonical_id=None,
            derived_instrument_type=None,
            derived_underlying_human=None,
        )

    classification = _classify(body)
    if classification is None:
        return CanonResult(
            status="QUARANTINE_UNPARSEABLE",
            canonical_id=None,
            derived_instrument_type=None,
            derived_underlying_human=None,
        )

    derived_type = classification.instrument_type.value

    if classification.is_continuous:
        return CanonResult(
            status="QUARANTINE_CONTINUOUS",
            canonical_id=None,
            derived_instrument_type=derived_type,
            derived_underlying_human=None,
        )

    if classification.instrument_type is InstrumentType.COMBO:
        return CanonResult(
            status="QUARANTINE_COMBO",
            canonical_id=None,
            derived_instrument_type=derived_type,
            derived_underlying_human=None,
        )

    if classification.instrument_type not in (InstrumentType.FUTURE, InstrumentType.OPTION):
        return CanonResult(
            status="QUARANTINE_UNPARSEABLE",
            canonical_id=None,
            derived_instrument_type=derived_type,
            derived_underlying_human=None,
        )

    human_root = EXCHANGE_CODE_TO_NAME.get(classification.underlying, classification.underlying)

    try:
        built = build_instrument_id(
            venue,
            classification.instrument_type,
            human_root,
            expiry_date=classification.expiry_date,
            strike=classification.strike,
            option_right=classification.option_right,
            margin_marker="LIN",
            quote_asset="USD",
        )
    except ValueError:
        return CanonResult(
            status="QUARANTINE_UNPARSEABLE",
            canonical_id=None,
            derived_instrument_type=derived_type,
            derived_underlying_human=human_root,
        )

    if not TARGET_TRADFI_DERIVATIVE_ID_RE.match(built):
        # e.g. an ICE qualifier (`BRN_Z`) injects a banned `_`/`!` into the
        # underlying — do NOT emit a banned-char id.
        return CanonResult(
            status="QUARANTINE_UNPARSEABLE",
            canonical_id=None,
            derived_instrument_type=derived_type,
            derived_underlying_human=human_root,
        )

    if built == original:
        return CanonResult(
            status="ALREADY_CANONICAL",
            canonical_id=built,
            derived_instrument_type=derived_type,
            derived_underlying_human=human_root,
        )

    return CanonResult(
        status="OK",
        canonical_id=built,
        derived_instrument_type=derived_type,
        derived_underlying_human=human_root,
    )


def assert_tradfi_derivative_ids_canonical(ids: list[str], types: list[str]) -> tuple[int, int, list[str]]:
    """Phase-B/D verify-gate helper — proves 0 raw ids remain on a surface.

    For every row whose id-embedded TYPE segment (parsed from the id
    itself — ``ids[i].split(":", 2)[1]``, never the possibly-mislabeled
    ``types[i]`` column — live manifest data carries ~400k rows with a
    stale/wrong ``instrument_type``, see
    ``tradfi_consolidated_closeout_2026_07_18.md`` Phase B) is FUTURE or
    OPTION, assert the id matches :data:`TARGET_TRADFI_DERIVATIVE_ID_RE`
    AND carries 0 whitespace, 0 residual ``/``, and no bare ``@LIN``
    missing its ``-USD`` quote.

    Args:
        ids: Candidate post-migration canonical ids (one surface's full
            worklist, or a sampled slice).
        types: The row's stored ``instrument_type`` column, parallel to
            ``ids`` (same length) — carried through into the violation
            samples for debugging context only; NOT used to decide which
            rows are checked (see above — that column is not trusted).

    Returns:
        ``(checked, canonical, violations_sample)`` — ``checked`` is the
        count of FUTURE/OPTION rows examined (by id-embedded type),
        ``canonical`` is how many of those passed every assertion, and
        ``violations_sample`` holds up to 50 example violation descriptions
        (bounded, not unbounded — matches the migration scripts' sidecar-log
        convention).

    Raises:
        ValueError: If ``ids`` and ``types`` are not the same length.
    """
    if len(ids) != len(types):
        msg = f"ids and types must be the same length, got {len(ids)} and {len(types)}"
        raise ValueError(msg)

    checked = 0
    canonical = 0
    violations: list[str] = []

    for row_id, declared_type in zip(ids, types, strict=True):
        parts = row_id.split(":", 2) if row_id else []
        id_type = parts[1].strip().upper() if len(parts) >= 2 else ""
        if id_type not in ("FUTURE", "OPTION"):
            continue

        checked += 1
        reasons: list[str] = []
        if not TARGET_TRADFI_DERIVATIVE_ID_RE.match(row_id):
            reasons.append("shape-mismatch")
        if _WHITESPACE_RE.search(row_id):
            reasons.append("whitespace")
        if "/" in row_id:
            reasons.append("residual-slash")
        if "@LIN" in row_id and "-USD@LIN" not in row_id:
            reasons.append("at-LIN-without-USD")

        if reasons:
            if len(violations) < _MAX_VIOLATIONS_SAMPLE:
                violations.append(f"id={row_id!r} declared_type={declared_type!r} reasons={reasons}")
        else:
            canonical += 1

    return checked, canonical, violations

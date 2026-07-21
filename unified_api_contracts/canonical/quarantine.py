"""Instrument-id quarantine — the id-form axis orthogonal to ``capture_status``.

Design of record: ``plans/active/issues/fail_hard_canonical_enforcement_design_2026_07_20.md``
(workflow ``wf_3785e859-c1f``, map -> design -> adversarial verify, 7 agents,
0 errors). This module ships the design's §3 "quarantine model" + the
Stage-P/Stage-1 prerequisite the doc's §6 calls out: *"Stages 0-3 require zero
edits to fenced files: ``is_canonical_instrument_id`` is already exported; a
new UAC ``is_quarantined_instrument_id`` composes with it."*

Composes (READ-ONLY import) with
:func:`unified_api_contracts.canonical.partition_paths.is_canonical_instrument_id`
— that module is fenced and is NOT edited here.

The three-valued id-form verdict
---------------------------------

**NOT a fifth ``capture_status``.** A NEW, ORTHOGONAL axis over the filename
stem / ``instrument_id`` column value:

``canonical``
    Passes the existing ID-FORM oracle
    (:func:`~unified_api_contracts.canonical.partition_paths.is_canonical_instrument_id`).
``quarantined``
    Carries the positive ``UNRESOLVED:`` marker (see below) AND is registered
    in :data:`QUARANTINE_REGISTRY` with falsifiable
    :class:`ResolutionEvidence`.
``non_canonical``
    Neither of the above — a bare wire stem (``ADAF0:USTF0``) or a
    double-wrapped catalogue-miss id
    (``BITFINEX-FUTURES:PERPETUAL:ADAF0:USTF0``). Per the design doc's own
    rule, **this is the ONLY fail condition** once a later stage wires this
    module into read-enforcement (Stage 3) — a reconciliation reading "N
    canonical, M quarantined (registered, expiring), 0 non-canonical" is a
    PASS.

The ``UNRESOLVED:`` marker grammar
------------------------------------

A **positive** marker, never a bare wire stem — a bare stem is ambiguous
between "genuinely quarantined" and "the migration front hasn't reached this
row yet" (the design doc's §5 gap #3 names exactly this under-specification
risk for the read path). Grammar::

    UNRESOLVED:<VENUE>:<original-stem>

- ``UNRESOLVED:`` — literal positive-marker prefix. A canonical instrument_id
  never starts with this token (the canonical grammar's second field is one of
  ``PERPETUAL``/``FUTURE``/``OPTION``/``SPOT_PAIR``/``COMBO``), so there is no
  overlap between "canonical" and "quarantined" — the two verdicts are
  mutually exclusive by construction.
- ``<VENUE>`` — the uppercase venue token (same casing convention as
  :func:`~unified_api_contracts.canonical.partition_paths._normalize_venue_upper`),
  e.g. ``PACIFICA-SOLANA``. This is deliberately the SAME token used to key
  :data:`QUARANTINE_REGISTRY`, so a marker's venue slot is always the direct
  registry join key — no second parse rule needed when a later stage wires in
  registry-gated enforcement.
- ``<original-stem>`` — the raw wire stem / attempted id being quarantined,
  preserved verbatim (may itself contain colons, e.g. an attempted
  ``HYPERLIQUID:PERPETUAL:...`` catalogue-miss) so the original value is never
  lost. Only the first two colons are structural; everything after is the stem.

Example: ``UNRESOLVED:PACIFICA-SOLANA:SOL-PERP``.

Scope note (do not over-read this module)
-------------------------------------------

This ships **standalone** — nothing here is wired into any write or read
guard. :func:`classify_id_form` answers the marker-FORM question only (mirrors
the existing id-form oracle's own scope, a syntactic check); it does not
consult :data:`QUARANTINE_REGISTRY` for membership/expiry. Registry-gated
enforcement (Stage 1 write-enforce, Stage 3 read-enforce) is separate,
tracked work per the design doc's §7 todo list.

Seed membership
-----------------

:data:`QUARANTINE_REGISTRY` is seeded with exactly ONE entry —
``PACIFICA-SOLANA`` (265 objects, venue culled 2026-07-16, no lane / no rows /
no upstream catalogue — permanently honest-raw). The design doc is explicit
that the ~5,413 healthy-venue residue (OKX-SPOT fiat-quote pairs,
COINBASE-SPOT crypto-quote pairs, BITGET-FUTURES CME-letter-month futures)
classifies ``NON_CANONICAL`` and must eventually FAIL — it is a real catalogue
gap, NOT a quarantine case, and is deliberately absent from this registry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, Literal

from unified_api_contracts.canonical.partition_paths import is_canonical_instrument_id

# ---------------------------------------------------------------------------
# The UNRESOLVED: marker — positive, unambiguous quarantine form.
# ---------------------------------------------------------------------------

_UNRESOLVED_MARKER_RE: Final[re.Pattern[str]] = re.compile(r"^UNRESOLVED:[A-Z0-9_-]+:.+$")
"""``UNRESOLVED:<VENUE>:<original-stem>`` — see module docstring for the grammar."""


def is_quarantined_instrument_id(candidate: str) -> bool:
    """True iff ``candidate`` carries the POSITIVE ``UNRESOLVED:`` quarantine marker.

    Per the design doc's §3 explicit requirement: this checks for the
    positive marker FORM only — never a bare wire stem, which is ambiguous
    between "quarantined" and "the migration front hasn't reached this row
    yet". A bare stem, a canonical instrument_id, and an empty string all
    return ``False``.

    >>> is_quarantined_instrument_id("UNRESOLVED:PACIFICA-SOLANA:SOL-PERP")
    True
    >>> is_quarantined_instrument_id("SOL-PERP")
    False
    >>> is_quarantined_instrument_id("PACIFICA-SOLANA:PERPETUAL:SOL-USD@LIN")
    False
    """
    return bool(_UNRESOLVED_MARKER_RE.match(candidate))


# ---------------------------------------------------------------------------
# ResolutionEvidence + the registry.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolutionEvidence:
    """Falsifiable evidence backing one :data:`QUARANTINE_REGISTRY` entry.

    Every field is REQUIRED — an entry without concrete, checkable evidence is
    not a quarantine, it is an undocumented exception (the exact status quo
    the design doc's quarantine model replaces). ``__post_init__`` rejects
    empty strings and a naive ``expires_at`` loud, at construction time.

    Attributes:
        venue: The venue token this evidence covers. MUST match the registry
            key AND the ``<VENUE>`` slot of the corresponding
            ``UNRESOLVED:`` marker (see module docstring grammar).
        instrument_stem: The specific wire stem being quarantined, or
            ``"*"`` for a whole-venue bulk quarantine (e.g. PACIFICA-SOLANA —
            every object under the venue is quarantined because the venue
            itself was culled, not one specific instrument).
        reason: Human-readable explanation of WHY this cannot resolve to a
            canonical id (e.g. "venue culled 2026-07-16 — no lane, no rows,
            no upstream catalogue to resolve against").
        verified_by: FALSIFIABLE provenance — WHO/WHAT verified this claim
            and HOW, specific enough that a reviewer could go re-check it
            (e.g. "manifest-oracle corpus-wide check 2026-07-20"). A vague
            "looks fine" / "seems permanent" is NOT acceptable provenance.
        expires_at: UTC-aware review-by date
            (``datetime(..., tzinfo=UTC)`` — never naive). This is a REVIEW
            deadline that forces periodic re-confirmation the quarantine
            claim still holds; it is NOT a promise the underlying gap will
            resolve by this date. Even a "permanent" case (PACIFICA-SOLANA)
            gets a bounded horizon so the registry can't silently ossify into
            an unaudited standing exception — re-verify and roll the date
            forward if the claim still holds.
    """

    venue: str
    instrument_stem: str
    reason: str
    verified_by: str
    expires_at: datetime

    def __post_init__(self) -> None:
        if not self.venue:
            msg = "ResolutionEvidence.venue must be a non-empty string"
            raise ValueError(msg)
        if not self.instrument_stem:
            msg = "ResolutionEvidence.instrument_stem must be a non-empty string ('*' for whole-venue)"
            raise ValueError(msg)
        if not self.reason:
            msg = "ResolutionEvidence.reason must be a non-empty, human-readable string"
            raise ValueError(msg)
        if not self.verified_by:
            msg = "ResolutionEvidence.verified_by must be a non-empty, falsifiable provenance string"
            raise ValueError(msg)
        if self.expires_at.tzinfo is None:
            msg = f"ResolutionEvidence.expires_at must be UTC-aware, got naive {self.expires_at!r}"
            raise ValueError(msg)


QUARANTINE_REGISTRY: dict[str, ResolutionEvidence] = {
    "PACIFICA-SOLANA": ResolutionEvidence(
        venue="PACIFICA-SOLANA",
        instrument_stem="*",
        reason=(
            "Venue culled 2026-07-16 — no lane, no captured rows, no upstream "
            "catalogue to resolve wire stems against. 265 objects, permanently "
            "honest-raw per the design doc's 'Quarantine set for fail-hard "
            "enablement' table. Objects do NOT move — Surface D already measures "
            "PASS on reads; this is consistency debt, not broken access."
        ),
        verified_by=(
            "fail_hard_canonical_enforcement_design_2026_07_20.md workflow "
            "wf_3785e859-c1f (map -> design -> adversarial verify; 7 agents, 0 "
            "errors) - 'Quarantine set for fail-hard enablement' table, "
            "PACIFICA-SOLANA row (265 objects, culled 2026-07-16)"
        ),
        expires_at=datetime(2027, 7, 21, tzinfo=UTC),
    ),
}
"""Registry of registered instrument-id quarantines, keyed by venue.

Per the design doc's §3: "Registry-gated, with mandatory falsifiable
``ResolutionEvidence`` + an expiry. Unregistered misses fail from Stage 1."
Seeded with EXACTLY the one confirmed permanent member — do NOT add the
~5,413 healthy-venue residue (OKX-SPOT / COINBASE-SPOT / BITGET-FUTURES); that
classifies ``NON_CANONICAL`` and must fail, it is not a quarantine case.
"""


# ---------------------------------------------------------------------------
# The composing three-valued classifier.
# ---------------------------------------------------------------------------

IdFormVerdict = Literal["canonical", "quarantined", "non_canonical"]
"""The three-valued id-form verdict (design doc §3) — a NEW axis orthogonal to
``capture_status``. ``non_canonical`` is the ONLY fail condition once this is
wired into Stage 3 read-enforcement; ``quarantined`` (registry-gated,
evidenced, expiring) is a PASS alongside ``canonical``."""


def classify_id_form(candidate: str) -> IdFormVerdict:
    """Three-valued id-form verdict for an instrument_id / filename stem.

    Composes
    :func:`unified_api_contracts.canonical.partition_paths.is_canonical_instrument_id`
    (read-only import — that module is fenced, not edited here) with this
    module's :func:`is_quarantined_instrument_id`:

    1. ``"canonical"`` — passes the existing ID-FORM oracle.
    2. ``"quarantined"`` — carries the positive ``UNRESOLVED:`` marker.
    3. ``"non_canonical"`` — neither; a bare wire stem or a double-wrapped
       catalogue-miss id. Per the design doc §3 this is the ONLY fail
       condition once a future stage wires this into read-enforcement — this
       module does not perform that wiring itself.

    NOTE: this does NOT consult :data:`QUARANTINE_REGISTRY` for membership or
    expiry — it answers the marker-FORM question only, mirroring the existing
    id-form oracle's own scope (a syntactic check, not a registry lookup).
    Registry-gated enforcement (rejecting an ``UNRESOLVED:`` marker whose
    venue/stem is not actually registered, or whose entry has expired) is
    separate Stage-1/Stage-3 write/read-guard work — see the design doc's §7
    todo list.
    """
    if is_canonical_instrument_id(candidate):
        return "canonical"
    if is_quarantined_instrument_id(candidate):
        return "quarantined"
    return "non_canonical"


__all__ = [
    "QUARANTINE_REGISTRY",
    "IdFormVerdict",
    "ResolutionEvidence",
    "classify_id_form",
    "is_quarantined_instrument_id",
]

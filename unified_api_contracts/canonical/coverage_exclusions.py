"""Evidence-gated BOUNDED coverage exclusions — ranges genuinely never capturable.

SSOT for the *bounded* sibling of :mod:`unified_api_contracts.canonical.coverage_starts`.
Where ``SOURCE_COVERAGE_START`` expresses a **floor** ("the source has nothing before
date X"), this module expresses a **closed interval** ("the source has nothing between
X and Y, and never will"). A declared interval leaves the honest-coverage model
entirely: it is neither ``captured`` nor ``missing``, it is OUT OF MODEL — the oracle
emits ``EXPECTED_UPSTREAM_OUT_OF_BOUNDS``, which is a member of
``OUT_OF_COVERAGE_WINDOW_REASONS`` and is therefore clipped from BOTH the numerator and
the denominator, while still surfacing as its own visible reported line.

Operator proposal 2026-07-17: *"for a genuine bounded upstream capture outage sounds
like something to put in UAC as out of bounds so doesn't affect honest coverage
denominator and adaptors don't try those ranges"*.

WHY THIS MODULE IS EVIDENCE-GATED — read before adding ANY entry
================================================================

**This mechanism is a loaded gun, and the workspace has already shot itself with it.**

``SOURCE_COVERAGE_START`` is this same pattern without an evidence requirement, and it
was WRONG for months. Its per-source sports floors were justified by the claim that
*"our backfill never captured 2018-2020 dates"* — a claim that was factually FALSE. We
held that data the whole time; the floors made it **invisible by declaration**, clipping
the canonical index and hiding 2018-2020 from coverage and from ML. It was amended to
measured reality only on 2026-07-16 (UAC@c280e1ff), after someone finally probed the
buckets and found ~22,327 real objects — including 20/30/98-row ``fixture_events``
parquets at ``day=2018-01-01`` — sitting under floors that declared them impossible.
The earlier api_football 2015→2018 move (UAC@d858f67d) is the same class of error.

A *bounded* registry can repeat that mistake at greater scale: a floor is at least
visible as a single cliff at the start of history, whereas a mid-history interval hides
a hole in the middle of a corpus where nobody thinks to look. So this module makes the
mistake structurally hard rather than merely discouraged:

1. **Evidence is MANDATORY and validated at construction** — a :class:`CoverageExclusion`
   without a machine-checkable ``evidence_uri``, a re-runnable ``evidence_probe``, a
   ``verified_at`` and a ``verified_by`` raises :class:`CoverageExclusionError` at import
   time. There is no code path that accepts an unevidenced range.
2. **Every declaration is continuously FALSIFIABLE** — ``scripts/check_coverage_exclusions.py``
   re-probes each interval against real manifest rows and FAILS if any real data exists
   inside it. A declaration is a standing, testable claim about the world, not a
   one-time assertion. This is precisely what the floors never had, and precisely why
   they stayed wrong for months.
3. **Declarations go STALE** — ``verified_at`` older than
   :data:`EVIDENCE_MAX_AGE_DAYS` fails the check. "It was true once" is not a licence to
   stay excluded forever; upstreams backfill their own history.

THE ASYMMETRY OF PROOF (the core design principle)
==================================================

Declaring an exclusion and falsifying one require **deliberately different evidence
bars**, because their failure directions are not symmetric:

* **Declaring** an exclusion HIDES data → requires a HIGH bar (positive proof of
  absence: a probe that returns nothing *today*, a vendor outage notice, a subscription
  record). The floors' amendment commit set this bar explicitly: object existence alone
  is NOT evidence, because the corpus carries an artifact class of present-day reference
  data replicated under historical partitions (``day=2014-01-01`` standings carrying
  ``season=2026``), which would argue for bogus conclusions. Real data means a parquet
  that PARSES, carries >=1 row, and is HISTORICALLY COHERENT with its date partition.
* **Falsifying** an exclusion UN-HIDES data → uses a LOW bar (any hint of real data
  inside the range). A false alarm here is SAFE: it merely refuses an exclusion and
  leaves the denominator honestly wide. A missed falsification is the dangerous one —
  that is the floors' failure mode.

So the falsifier is deliberately SENSITIVE and the declaration gate deliberately STRICT.
When in doubt, the range stays IN the model.

WHAT DOES NOT BELONG HERE
=========================

This registry is only for ranges that are **genuinely, permanently uncapturable from
every source**. It is NOT a place to park inconvenient gaps:

* **A capture gap where we hold the data** → RECOVER it, do not declare it. Worked
  counter-example: the 32-day MDT window ``2022-09-07..2022-10-01`` (550,062 keys) is
  NOT a candidate — the legacy ``market-data-tick-sports`` bucket HOLDS those keys
  (verified two independent ways). It is a canonical capture gap with the data in hand.
* **Recurring calendar closure** (weekends / holidays / half-days) → already owned by
  ``venue_trading_calendar`` + ``EXPECTED_WEEKEND`` / ``EXPECTED_HOLIDAY``. Deliberately
  NOT modelled as an ``ExclusionReason`` (the operator's proposal listed ``MARKET_CLOSED``
  illustratively; encoding it here would duplicate a live primitive and let a recurring
  schedule masquerade as a one-off outage).
* **Before a source's archive begins** → that is a floor, ``SOURCE_COVERAGE_START``.
* **DeFi protocol pauses** → ``registry.protocol_pause_windows``, which is
  DETECTOR-POPULATED from on-chain governance events (operator directive 2026-05-20:
  *"I can't just tell you when protocols are out — it needs to be understood from
  data"*). That module is the exemplar this one follows, not a duplicate of it: a
  derived-from-data registry is evidence-gated by construction.
* **A sparse-but-not-empty window** → still expected, just under-captured.

Codex SSOT: ``codex/02-data/honest-coverage-model.md`` § Bounded coverage exclusions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Final

# Asset groups an exclusion may be declared against (workspace-canonical lowercase).
_VALID_ASSET_GROUPS: Final[frozenset[str]] = frozenset({"cefi", "defi", "tradfi", "sports", "prediction"})

# Wildcard data_type token — the exclusion applies to every data_type of the source.
DATA_TYPE_WILDCARD: Final[str] = "*"

# An evidence URI must be machine-checkable: an auditor has to be able to go and LOOK.
# ``_audits/`` = an audit artifact committed under a plan's audit results directory.
# ``audit://`` = a named audit run + artifact addressable by the audit tooling.
# ``https://`` = a vendor status page / API-probe permalink / support-ticket record.
# NOTE: object-store URIs are deliberately absent — bucket paths are resolved through
# ``resolve_bucket_name(...)``, never inlined (QG 5.69).
EVIDENCE_URI_PREFIXES: Final[tuple[str, ...]] = ("_audits/", "audit://", "https://")

# A declaration must be re-verified at least this often. Upstreams backfill their own
# history; an exclusion that was true two years ago may simply be stale today. Beyond
# this age the falsifier FAILS rather than warns — silence is not evidence.
EVIDENCE_MAX_AGE_DAYS: Final[int] = 365

# Minimum length of ``evidence_probe``. A probe must be a re-runnable INSTRUCTION
# ("curl X, observe empty payload"), not a mood ("checked, nothing there").
_MIN_PROBE_LENGTH: Final[int] = 30


class CoverageExclusionError(ValueError):
    """A :class:`CoverageExclusion` was declared without valid mandatory evidence.

    Raised at construction (therefore at import time for the module-level registry), so
    an unevidenced range cannot exist as a value anywhere in the process — it is not a
    lint that can be waived, it is a type that cannot be built.
    """


class ExclusionReason(StrEnum):
    """WHY a bounded range is permanently uncapturable.

    Deliberately a small closed set. Each member describes a distinct, provable state of
    the world; if a candidate range does not fit one of these cleanly, that is a strong
    signal it is a capture gap to RECOVER rather than an exclusion to declare.
    """

    UPSTREAM_OUTAGE = "UPSTREAM_OUTAGE"
    """The upstream itself lost or never produced the data for this window, and no longer
    serves it to anyone. Evidence: a vendor status-page incident / support-ticket record,
    plus a probe that returns nothing for the window TODAY."""

    VENDOR_NEVER_SERVED = "VENDOR_NEVER_SERVED"
    """The vendor's archive structurally omits this window (e.g. a feed's history begins
    after a re-platforming and the earlier window was never migrated). Evidence: the
    vendor's own coverage/availability API asserting the omission, plus a probe."""

    SUBSCRIPTION_GAP = "SUBSCRIPTION_GAP"
    """The window predates (or falls outside) our entitlement, and the entitlement is not
    purchasable retroactively. Evidence: the subscription/entitlement record + a probe
    returning an authorization error rather than an empty payload.

    CAUTION: if the data IS purchasable, this is a credential/procurement ask, NOT an
    exclusion — see ``codex/02-data/external-data-always-available-rule.md`` (external
    data is always available; exhausting the free path is a credential ask, not a
    descope). Declaring a purchasable window here is a misuse of this registry."""


@dataclass(frozen=True, kw_only=True)
class CoverageExclusion:
    """One closed, evidenced, falsifiable date interval that is OUT OF MODEL.

    Every field except ``data_type``'s wildcard default is mandatory. Construction
    validates the evidence contract and raises :class:`CoverageExclusionError` on any
    violation — see the module docstring for why the bar is set here rather than in a
    reviewer's judgement.
    """

    asset_group: str
    """Workspace-canonical lowercase asset group (``cefi`` / ``defi`` / ...)."""

    source: str
    """Venue/source token, cased as the asset group's registries case it (uppercase venue
    for cefi/defi/tradfi/prediction; lowercase source name for sports)."""

    start: date
    """First excluded day (inclusive)."""

    end: date
    """Last excluded day (inclusive). Closed intervals only — an open-ended exclusion is
    a floor or a coverage-END, not a bounded outage."""

    reason: ExclusionReason
    """Typed reason — see :class:`ExclusionReason`."""

    evidence_uri: str
    """Machine-checkable pointer to the PROOF. Must start with one of
    :data:`EVIDENCE_URI_PREFIXES` so an auditor can go and look at it."""

    evidence_probe: str
    """A re-runnable instruction that reproduces the proof of absence TODAY. This is what
    makes the declaration falsifiable by someone who does not trust it."""

    verified_at: date
    """The day the evidence was last actually checked (not the day it was written down)."""

    verified_by: str
    """Who/what verified it — an operator handle or the audit/tool identifier."""

    data_type: str = DATA_TYPE_WILDCARD
    """Specific data_type, or ``*`` for every data_type of the source."""

    def __post_init__(self) -> None:
        """Enforce the evidence contract. An unevidenced range must not be constructible."""
        if self.asset_group not in _VALID_ASSET_GROUPS:
            raise CoverageExclusionError(
                f"asset_group {self.asset_group!r} is not one of {sorted(_VALID_ASSET_GROUPS)}"
            )
        if not self.source.strip():
            raise CoverageExclusionError("source must be a non-empty token")
        if not self.data_type.strip():
            raise CoverageExclusionError("data_type must be non-empty (use '*' for all)")
        if self.end < self.start:
            raise CoverageExclusionError(
                f"{self._key_repr()}: end {self.end.isoformat()} precedes start {self.start.isoformat()}"
            )
        if not isinstance(self.reason, ExclusionReason):
            raise CoverageExclusionError(
                f"{self._key_repr()}: reason must be an ExclusionReason member, got {self.reason!r}"
            )
        self._validate_evidence()

    def _validate_evidence(self) -> None:
        """The mandatory-evidence gate — the whole point of this class."""
        uri = self.evidence_uri.strip()
        if not uri:
            raise CoverageExclusionError(
                f"{self._key_repr()}: evidence_uri is MANDATORY — a range may not be declared "
                "out-of-bounds without a machine-checkable pointer to its proof. See the "
                "coverage_exclusions module docstring (SOURCE_COVERAGE_START was wrong for months "
                "precisely because it had no evidence requirement)."
            )
        if not uri.startswith(EVIDENCE_URI_PREFIXES):
            raise CoverageExclusionError(
                f"{self._key_repr()}: evidence_uri {uri!r} is not machine-checkable — it must start "
                f"with one of {EVIDENCE_URI_PREFIXES} so an auditor can re-open the proof."
            )
        probe = self.evidence_probe.strip()
        if len(probe) < _MIN_PROBE_LENGTH:
            raise CoverageExclusionError(
                f"{self._key_repr()}: evidence_probe must be a re-runnable instruction of at least "
                f"{_MIN_PROBE_LENGTH} chars that reproduces the proof of absence today, got {probe!r}"
            )
        if not self.verified_by.strip():
            raise CoverageExclusionError(f"{self._key_repr()}: verified_by is MANDATORY")
        today = datetime.now(UTC).date()
        if self.verified_at > today:
            raise CoverageExclusionError(
                f"{self._key_repr()}: verified_at {self.verified_at.isoformat()} is in the future"
            )
        if self.verified_at < self.end:
            raise CoverageExclusionError(
                f"{self._key_repr()}: verified_at {self.verified_at.isoformat()} precedes the "
                f"window end {self.end.isoformat()} — the evidence cannot predate the window it "
                "claims to have checked."
            )

    def _key_repr(self) -> str:
        return f"({self.asset_group}, {self.source}, {self.data_type})"

    @property
    def key(self) -> tuple[str, str, str]:
        """Registry lookup key."""
        return (self.asset_group, self.source, self.data_type)

    def covers(self, day: date) -> bool:
        """True when ``day`` falls inside this closed interval."""
        return self.start <= day <= self.end

    def is_stale(self, *, as_of: date | None = None) -> bool:
        """True when the evidence is older than :data:`EVIDENCE_MAX_AGE_DAYS`."""
        reference = as_of if as_of is not None else datetime.now(UTC).date()
        return (reference - self.verified_at).days > EVIDENCE_MAX_AGE_DAYS

    def describe(self) -> str:
        """Human/diagnostic rendering carrying the provenance, not just the dates."""
        return (
            f"{self.source} {self.data_type} out-of-bounds {self.start.isoformat()} → "
            f"{self.end.isoformat()} ({self.reason.value}; evidence={self.evidence_uri}; "
            f"verified {self.verified_at.isoformat()} by {self.verified_by})"
        )


# ---------------------------------------------------------------------------
# THE REGISTRY
# ---------------------------------------------------------------------------
# ZERO DECLARATIONS — and that is the honest default, exactly as
# ``PROTOCOL_PAUSE_WINDOWS`` keeps ("don't encode pauses we can't prove from data").
# The gate exists and never fires until someone can PROVE a range.
#
# Before adding an entry, satisfy ALL of:
#   1. The range is uncapturable from EVERY source in SOURCE_PRIORITY — not just the one
#      adapter that failed. A second vendor serving the window makes this a sourcing bug.
#   2. We do not already HOLD the data on any surface (legacy buckets included). If we
#      hold it, RECOVER it — see the MDT counter-example in the module docstring.
#   3. ``evidence_uri`` + ``evidence_probe`` let a sceptic reproduce the absence TODAY.
#   4. ``scripts/check_coverage_exclusions.py --index <availability_index.parquet>``
#      passes against the real manifest — i.e. your claim survives falsification.
COVERAGE_EXCLUSIONS: Final[tuple[CoverageExclusion, ...]] = ()


_INDEX: Final[dict[tuple[str, str, str], tuple[CoverageExclusion, ...]]] = {}
for _exclusion in COVERAGE_EXCLUSIONS:
    _INDEX.setdefault(_exclusion.key, ())
    _INDEX[_exclusion.key] = (*_INDEX[_exclusion.key], _exclusion)


def find_coverage_exclusion(
    asset_group: str,
    source: str,
    data_type: str,
    day: date,
) -> CoverageExclusion | None:
    """Return the exclusion covering this cell, or ``None`` when the cell is IN MODEL.

    ``None`` is the answer for every cell today (the registry is empty by design) and
    must remain the answer unless a range has been PROVEN uncapturable. Checks the exact
    ``data_type`` first, then the source-wide ``*`` wildcard.

    Args:
        asset_group: workspace-canonical lowercase asset group.
        source: venue/source token as cased by the asset group's registries.
        data_type: the data_type being queried.
        day: the date being queried.
    """
    ag = asset_group.lower()
    for candidate_key in ((ag, source, data_type), (ag, source, DATA_TYPE_WILDCARD)):
        for exclusion in _INDEX.get(candidate_key, ()):
            if exclusion.covers(day):
                return exclusion
    return None


def is_out_of_bounds(asset_group: str, source: str, data_type: str, day: date) -> bool:
    """True when the cell falls in a declared, evidenced out-of-bounds range.

    Consumers that need the provenance for a diagnostic should call
    :func:`find_coverage_exclusion` instead — an out-of-bounds cell must always be
    REPORTABLE with its reason and evidence, never silently dropped.
    """
    return find_coverage_exclusion(asset_group, source, data_type, day) is not None


def coverage_exclusions_for(
    asset_group: str,
    source: str,
    data_type: str,
) -> tuple[CoverageExclusion, ...]:
    """Return every declared interval for this key (exact data_type + wildcard)."""
    ag = asset_group.lower()
    return (
        *_INDEX.get((ag, source, data_type), ()),
        *_INDEX.get((ag, source, DATA_TYPE_WILDCARD), ()),
    )


def all_coverage_exclusions() -> tuple[CoverageExclusion, ...]:
    """Every declared interval — the falsifier's input."""
    return COVERAGE_EXCLUSIONS


__all__ = [
    "COVERAGE_EXCLUSIONS",
    "DATA_TYPE_WILDCARD",
    "EVIDENCE_MAX_AGE_DAYS",
    "EVIDENCE_URI_PREFIXES",
    "CoverageExclusion",
    "CoverageExclusionError",
    "ExclusionReason",
    "all_coverage_exclusions",
    "coverage_exclusions_for",
    "find_coverage_exclusion",
    "is_out_of_bounds",
]

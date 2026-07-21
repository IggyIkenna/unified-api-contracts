"""Unit tests for the instrument-id quarantine model (id-form axis).

Design of record:
``plans/active/issues/fail_hard_canonical_enforcement_design_2026_07_20.md``
§3 ("The quarantine model"). Covers the three verdicts
:func:`~unified_api_contracts.classify_id_form` must produce:
  1. a genuinely canonical id -> ``"canonical"``
  2. the PACIFICA-SOLANA registered quarantine case -> ``"quarantined"``
  3. a genuinely non-canonical id -> ``"non_canonical"``
Plus the ``UNRESOLVED:`` marker grammar and :class:`ResolutionEvidence`
falsifiability guards.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from unified_api_contracts import (
    QUARANTINE_REGISTRY,
    ResolutionEvidence,
    classify_id_form,
    is_quarantined_instrument_id,
)

# ---------------------------------------------------------------------------
# is_quarantined_instrument_id — the positive UNRESOLVED: marker form.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        ("UNRESOLVED:PACIFICA-SOLANA:SOL-PERP", True),
        ("UNRESOLVED:PACIFICA-SOLANA:*", True),
        ("UNRESOLVED:HYPERLIQUID:HYPERLIQUID:PERPETUAL:BTC-USD@LIN", True),  # stem itself carries colons
        # A bare wire stem is AMBIGUOUS (quarantined vs not-yet-migrated) —
        # must NOT be recognized as quarantined.
        ("SOL-PERP", False),
        ("ADAF0:USTF0", False),
        # A genuinely canonical instrument_id is not a quarantine marker.
        ("PACIFICA-SOLANA:PERPETUAL:SOL-USD@LIN", False),
        ("BITFINEX-FUTURES:PERPETUAL:ADA-USDT", False),
        # Malformed marker shapes.
        ("UNRESOLVED:", False),
        ("UNRESOLVED", False),
        ("unresolved:pacifica-solana:sol-perp", False),  # lowercase prefix rejected
        ("", False),
    ],
)
def test_is_quarantined_instrument_id(candidate: str, expected: bool) -> None:
    assert is_quarantined_instrument_id(candidate) is expected


# ---------------------------------------------------------------------------
# classify_id_form — the composing three-valued verdict.
# ---------------------------------------------------------------------------


def test_classify_id_form_canonical() -> None:
    """A genuinely canonical id verdicts 'canonical'."""
    assert classify_id_form("BITFINEX-FUTURES:PERPETUAL:ADA-USDT") == "canonical"
    assert classify_id_form("HYPERLIQUID:PERPETUAL:BTC-USD@LIN") == "canonical"
    assert classify_id_form("DERIBIT:OPTION:BTC-USD-20260327-65000-C") == "canonical"


def test_classify_id_form_quarantined_pacifica_solana() -> None:
    """The PACIFICA-SOLANA registered-quarantine case verdicts 'quarantined'."""
    assert classify_id_form("UNRESOLVED:PACIFICA-SOLANA:SOL-PERP") == "quarantined"


def test_classify_id_form_non_canonical() -> None:
    """A genuinely non-canonical id (raw wire stem, no marker) verdicts 'non_canonical'."""
    assert classify_id_form("ADAF0:USTF0") == "non_canonical"
    assert classify_id_form("BTCUSD") == "non_canonical"
    assert classify_id_form("BITFINEX-FUTURES:PERPETUAL:ADAF0:USTF0") == "non_canonical"  # double-wrapped
    assert classify_id_form("") == "non_canonical"


def test_classify_id_form_verdicts_are_mutually_exclusive() -> None:
    """Canonical ids never ALSO match the UNRESOLVED: marker, and vice versa."""
    canonical_id = "BITFINEX-FUTURES:PERPETUAL:ADA-USDT"
    marker = "UNRESOLVED:PACIFICA-SOLANA:SOL-PERP"
    assert not is_quarantined_instrument_id(canonical_id)
    from unified_api_contracts import is_canonical_instrument_id

    assert not is_canonical_instrument_id(marker)


# ---------------------------------------------------------------------------
# QUARANTINE_REGISTRY — seeded with EXACTLY the one confirmed permanent member.
# ---------------------------------------------------------------------------


def test_registry_has_exactly_one_seed_member() -> None:
    """The design doc names PACIFICA-SOLANA as the ONE confirmed seed member.

    The ~5,413 healthy-venue residue (OKX-SPOT / COINBASE-SPOT / BITGET-FUTURES)
    classifies NON_CANONICAL and must NOT appear here.
    """
    assert set(QUARANTINE_REGISTRY) == {"PACIFICA-SOLANA"}


def test_registry_entry_is_falsifiable_evidence() -> None:
    entry = QUARANTINE_REGISTRY["PACIFICA-SOLANA"]
    assert entry.venue == "PACIFICA-SOLANA"
    assert entry.instrument_stem  # non-empty ("*" for whole-venue)
    assert entry.reason
    assert entry.verified_by
    assert entry.expires_at.tzinfo is not None


@pytest.mark.parametrize("bad_venue", ["OKX-SPOT", "COINBASE-SPOT", "BITGET-FUTURES"])
def test_registry_excludes_healthy_venue_residue(bad_venue: str) -> None:
    assert bad_venue not in QUARANTINE_REGISTRY


# ---------------------------------------------------------------------------
# ResolutionEvidence — construction-time falsifiability guards.
# ---------------------------------------------------------------------------


def _valid_evidence_kwargs() -> dict[str, object]:
    return {
        "venue": "TESTVENUE",
        "instrument_stem": "*",
        "reason": "test reason",
        "verified_by": "test-provenance 2026-07-21",
        "expires_at": datetime(2027, 1, 1, tzinfo=UTC),
    }


def test_resolution_evidence_accepts_valid_construction() -> None:
    evidence = ResolutionEvidence(**_valid_evidence_kwargs())
    assert evidence.venue == "TESTVENUE"


def test_resolution_evidence_is_frozen() -> None:
    evidence = ResolutionEvidence(**_valid_evidence_kwargs())
    with pytest.raises(FrozenInstanceError):
        evidence.venue = "OTHER"  # pyright: ignore[reportAttributeAccessIssue]  # frozen dataclass — assignment forbidden


def test_resolution_evidence_rejects_naive_expiry() -> None:
    kwargs = _valid_evidence_kwargs()
    kwargs["expires_at"] = datetime(2027, 1, 1)  # naive — no tzinfo
    with pytest.raises(ValueError, match="UTC-aware"):
        ResolutionEvidence(**kwargs)


@pytest.mark.parametrize("field", ["venue", "instrument_stem", "reason", "verified_by"])
def test_resolution_evidence_rejects_empty_strings(field: str) -> None:
    kwargs = _valid_evidence_kwargs()
    kwargs[field] = ""
    with pytest.raises(ValueError, match="non-empty"):
        ResolutionEvidence(**kwargs)

"""Dimension-6 guardrail: ``validate_data_type_for_venue(strict=...)``.

The default (``strict=False``) stays permissive/advisory for an unknown venue
(back-compat for warn-only callers). The live CAPTURE path passes ``strict=True``
so an unknown/typo'd venue fails CLOSED (a venue UAC does not recognise cannot have
a valid (venue × data_type) combo, so it must not be attempted / phantom-written).
"""

from __future__ import annotations

from unified_api_contracts import validate_data_type_for_venue


def test_known_venue_valid_combo_true() -> None:
    # A known cefi venue + a data_type it supports is valid in BOTH modes.
    assert validate_data_type_for_venue("BINANCE-FUTURES", "trades") is True
    assert validate_data_type_for_venue("BINANCE-FUTURES", "trades", strict=True) is True


def test_unknown_venue_permissive_default_strict_failclosed() -> None:
    unknown = "NOT-A-REAL-VENUE-XYZ"
    # default permissive (advisory) — preserves back-compat
    assert validate_data_type_for_venue(unknown, "trades") is True
    # strict — fail-closed (Dimension-6 guardrail)
    assert validate_data_type_for_venue(unknown, "trades", strict=True) is False

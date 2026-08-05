#!/usr/bin/env python
"""FALSIFIER for cross-registry drift between the two coverage-floor registries.

# Epic: manifest_master
# Lifecycle: PERMANENT — this is a standing guard, not a one-off migration script.
# Delete-when: never (delete only if one of the two registries is retired/merged
# into the other).

WHY THIS EXISTS
===============

Two parallel registries each declare a venue/source "coverage floor" (earliest
date data exists), consumed by two different downstream mechanisms:

  1. ``unified_api_contracts.canonical.coverage_starts`` — feeds the
     catalogue's *expected* date denominator (the honest-coverage % oracle).
  2. ``unified_api_contracts.registry.venue_mapping.VenueMapping.venue_start_dates``
     / ``source_data_start_dates`` — feeds MTDS's ``is_venue_available_on_date``
     FETCH pre-skip (whether a backfill even attempts a date).

Unlike sports (registry 3, ``canonical.domain.sports.league_data``), which
``coverage_starts`` imports directly — making them structurally ONE SSOT with
its own falsifier (``TestOddsApiFloorDerivesFromSportsSsot`` in
``tests/test_sports_source_coverage_propagation.py``) — registries 1 and 2
have NO code-level link. An audit (2026-07-17,
``plans/active/issues/coverage_floor_registries_no_cross_propagation_2026_07_17.md``)
found every CeFi venue present in both disagreeing, mostly by YEARS: a floor
amended in one registry silently never reaches the other, exactly the failure
class that made ``SOURCE_COVERAGE_START`` wrong for months (UAC@c280e1ff).

This script is the permanent backstop against *new* re-divergence.

KEY NORMALIZATION (why this isn't a blind dict-equality check)
================================================================

``coverage_starts`` uses bare venue/protocol tokens (``BINANCE``, ``CURVE``).
``venue_mapping`` uses a finer instrument-type/chain grain
(``BINANCE-SPOT``/``-FUTURES``/``-DELIVERY``, ``CURVE-ETHEREUM``). A related
pair is: an exact key match, OR a ``venue_mapping`` key of the form
``f"{bare_key}-{suffix}"`` for a suffix drawn from a small, EXPLICIT,
per-asset_group allowlist (never a blind ``startswith`` — see the docstring on
``_related_venue_mapping_keys`` for the false-positive that motivated this).

THE BASELINE IS A SHRINKING RATCHET
====================================

Today's real mismatches are already tracked as [DATA] todos on the audit doc
above (not this script's job to fix). ``KNOWN_DIVERGENCES`` records them so
this falsifier fails on *new, undeclared* divergence without also failing CI
red for the whole fleet on every known-and-tracked one. Each entry MUST cite
its tracking todo. Critically: a baseline entry for a pair that no longer
disagrees is ITSELF a failure (`STALE BASELINE`) — forcing removal the moment
a [DATA] todo lands, so the baseline can only shrink, never silently rot.

USAGE
=====

    python scripts/check_coverage_floor_registry_drift.py
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from unified_api_contracts.canonical import coverage_starts as _coverage_starts
from unified_api_contracts.registry.venue_mapping import VenueMapping

# sports is intentionally excluded — coverage_starts imports it directly
# (structurally one SSOT), and it has its own dedicated falsifier already
# (TestOddsApiFloorDerivesFromSportsSsot).
_ASSET_GROUP_REGISTRIES: dict[str, dict[str, date]] = {
    "cefi": _coverage_starts.CEFI_SOURCE_COVERAGE_START,
    "defi": _coverage_starts.DEFI_SOURCE_COVERAGE_START,
    "tradfi": _coverage_starts.TRADFI_SOURCE_COVERAGE_START,
    "prediction": _coverage_starts.PREDICTION_SOURCE_COVERAGE_START,
}

# ---------------------------------------------------------------------------
# Explicit key-mapping — coverage_starts bare keys → venue_mapping suffixed keys
# ---------------------------------------------------------------------------
# The SSOT mapping is in ``coverage_starts.BARE_KEY_TO_VENUE_MAPPING_KEYS``,
# published 2026-08-05 (coverage_floor_registries_no_cross_propagation_2026_07_17.md
# [DATA] P3). A bare key absent from the mapping defaults to exact-match lookup,
# which is correct for tradfi/prediction (keys match exactly) and for bare keys
# with no venue_mapping counterpart at all.
#
# This REPLACES the earlier suffix-allowlist approach (``_CEFI_INSTRUMENT_SUFFIXES``
# + ``_DEFI_CHAIN_SUFFIXES``) — the mapping is explicit, auditable, and the
# falsifier validates its completeness at gate time (see
# ``_validate_mapping_completeness``).


def _related_venue_mapping_keys(asset_group: str, bare_key: str, venue_keys: Sequence[str]) -> list[str]:
    """``venue_mapping`` keys describing the SAME venue/protocol as ``bare_key``.

    Looks up the explicit ``BARE_KEY_TO_VENUE_MAPPING_KEYS`` mapping first.
    Falls back to exact-match for asset groups / bare keys not in the mapping
    (tradfi, prediction, and any bare key with no suffixed counterparts).
    """
    mapping = _coverage_starts.BARE_KEY_TO_VENUE_MAPPING_KEYS.get(asset_group, {})
    declared = mapping.get(bare_key)
    if declared is not None:
        return [k for k in declared if k in venue_keys]

    # Exact-match fallback — correct for tradfi/prediction (keys match exactly
    # with no instrument-type/chain suffix), and for bare keys with no
    # venue_mapping counterpart at all (returns empty, which is honest).
    if bare_key in venue_keys:
        return [bare_key]
    return []


def _venue_mapping_combined_dates() -> dict[str, str]:
    """``venue_start_dates`` + ``source_data_start_dates`` — the todo's own scope."""
    vm = VenueMapping()
    combined = dict(vm.venue_start_dates)
    combined.update(vm.source_data_start_dates)
    return combined


# ---------------------------------------------------------------------------
# KNOWN_DIVERGENCES — the shrinking-ratchet baseline
# ---------------------------------------------------------------------------
# Every entry MUST cite the tracking todo. Remove an entry the moment its
# [DATA] todo lands — a stale entry (no real mismatch left) fails on its own
# (see STALE BASELINE below), so this is enforced, not just a convention.


@dataclass(frozen=True)
class _KnownDivergence:
    asset_group: str
    bare_key: str
    note: str


_AUDIT_DOC = "plans/active/issues/coverage_floor_registries_no_cross_propagation_2026_07_17.md"

KNOWN_DIVERGENCES: tuple[_KnownDivergence, ...] = (
    # --- [DATA] P1: 8 confirmed multi-year/multi-month CeFi mismatches ---
    # RESOLVED 2026-07-27 (same issue doc, [DATA] P1) — KRAKEN/COINBASE-SPOT/
    # DERIBIT/OKX/BINANCE/HYPERLIQUID all fully agree now (manifest-probe-
    # verified; entries removed, this IS the ratchet firing as intended).
    # BITFINEX + BYBIT below are NARROWED, not removed: the bare-key vs
    # primary-suffix mismatch is fixed, but a real, deliberate, per-suffix
    # product-launch-timing gap remains (not a data error to "fix away").
    _KnownDivergence(
        "cefi",
        "BITFINEX",
        f"{_AUDIT_DOC} [DATA] P1 — RESOLVED for BITFINEX-SPOT (2020-01-01, matches). "
        "Narrowed, not closed: BITFINEX-FUTURES stays 2019-12-01 (Tardis bitfinex-derivatives "
        "availableSince) vs bare 2020-01-01 — deliberate, per venue_mapping.py's own comment "
        "(symbols reliable only from 2020-05-27, pre-filter emits EXPECTED_PRE_SOURCE_COVERAGE_START "
        "for the gap) — a real symbol-reliability design, not an unverified seed.",
    ),
    _KnownDivergence(
        "cefi",
        "BYBIT",
        f"{_AUDIT_DOC} [DATA] P1 — RESOLVED for the BYBIT perp floor (2021-01-01, matches, was a "
        "full year off). Narrowed, not closed: BYBIT-SPOT stays 2021-12-04 (measured, confirmed clean "
        "boundary) vs bare 2021-01-01 — a real ~11-month product-launch gap (spot listed after perps), "
        "not a registry error.",
    ),
    # --- [DATA] P2: POLYMARKET (~2.3yr gap, CLOB-launch vs first-instrument) ---
    # RESOLVED 2026-08-04 (same issue doc, [DATA] P2) — coverage_starts.py
    # POLYMARKET corrected from 2022-11-21 (CLOB launch) to 2025-03-14
    # (first actual captured instrument, manifest-verified per venue_mapping.py's
    # per-market GCS-parquet-verified dates), matching venue_mapping.py. Entry
    # removed — the registries now agree; the ratchet fires as intended.
    # --- [DATA] P3: small 1-21 day DeFi drifts + the AAVE_V3 chain-axis question ---
    # RESOLVED 2026-08-05 (same issue doc, [DATA] P3) — the 1-21 day ETHEREUM-chain
    # drifts for CURVE/UNISWAP_V2/UNISWAP_V4/BALANCER/LIDO are fixed (coverage_starts.py
    # updated to match venue_mapping.py's manifest-verified ETHEREUM dates). AAVE_V3
    # updated to 2022-03-12 (min across POLYGON/AVALANCHE/ARBITRUM/OPTIMISM), documented
    # as min-across-chains. UNISWAP_V2/UNISWAP_V4/LIDO have only one chain (ETHEREUM) —
    # fully resolved, no baseline entries needed. The 4 remaining entries below cover the
    # NON-MIN chains (e.g. CURVE-AVALANCHE launches later than CURVE-ETHEREUM) — these
    # are EXPECTED per-chain launch-date differences, not registry errors to "fix."
    # The flat DEFI_SOURCE_COVERAGE_START value = min-across-chains by design.
    _KnownDivergence(
        "defi",
        "CURVE",
        f"{_AUDIT_DOC} [DATA] P3 — RESOLVED for ETHEREUM chain (2020-01-20, matches). "
        "CURVE-AVALANCHE (2021-11-10) and CURVE-OPTIMISM (2022-01-13) are later per-chain "
        "launch dates — expected, not a registry error. Flat value = min-across-chains.",
    ),
    _KnownDivergence(
        "defi",
        "UNISWAP_V3",
        f"{_AUDIT_DOC} [DATA] P3 — ETHEREUM chain matches (2021-05-05). "
        "ARBITRUM/POLYGON/OPTIMISM/BASE chains have later per-chain launch dates — "
        "expected, not a registry error. Flat value = min-across-chains.",
    ),
    _KnownDivergence(
        "defi",
        "BALANCER",
        f"{_AUDIT_DOC} [DATA] P3 — RESOLVED for ETHEREUM chain (2021-04-22, matches). "
        "POLYGON/ARBITRUM/OPTIMISM/AVALANCHE/BASE chains have later per-chain launch "
        "dates — expected, not a registry error. Flat value = min-across-chains.",
    ),
    _KnownDivergence(
        "defi",
        "AAVE_V3",
        f"{_AUDIT_DOC} [DATA] P3 — RESOLVED for min chains (2022-03-12, POLYGON/AVALANCHE/"
        "ARBITRUM/OPTIMISM match). ETHEREUM (2023-01-27)/BASE (2023-08-23)/BSC (2024-01-24)/"
        "LINEA (2025-02-12) have later per-chain launch dates — expected, not a registry "
        "error. Flat value = min-across-chains, explicitly documented in coverage_starts.py.",
    ),
)


class _Finding:
    def __init__(self, message: str) -> None:
        self.message = message

    def render(self) -> str:
        return f"  ✗ {self.message}"


def find_cross_registry_mismatches() -> tuple[list[_Finding], list[_Finding]]:
    """Compare both registries. Returns ``(new_findings, stale_baseline_findings)``.

    ``new_findings`` = a disagreeing pair with NO baseline entry (the falsifier
    firing for real). ``stale_baseline_findings`` = a baseline entry whose pair
    no longer disagrees (the ratchet firing — remove the entry).
    """
    venue_dates = _venue_mapping_combined_dates()
    baseline_by_key = {(d.asset_group, d.bare_key): d for d in KNOWN_DIVERGENCES}
    seen_baseline_keys: set[tuple[str, str]] = set()
    new_findings: list[_Finding] = []

    for asset_group, registry in _ASSET_GROUP_REGISTRIES.items():
        for bare_key, cs_date in registry.items():
            related = _related_venue_mapping_keys(asset_group, bare_key, list(venue_dates))
            mismatched = [(vk, venue_dates[vk]) for vk in related if venue_dates[vk] != cs_date.isoformat()]
            if not mismatched:
                continue

            key = (asset_group, bare_key)
            if key in baseline_by_key:
                seen_baseline_keys.add(key)
                continue

            for venue_key, venue_date in mismatched:
                new_findings.append(
                    _Finding(
                        f"UNDECLARED cross-registry divergence: coverage_starts.py"
                        f"[{asset_group}][{bare_key!r}]={cs_date.isoformat()} vs "
                        f"venue_mapping.py[{venue_key!r}]={venue_date}. Either fix the wrong "
                        "registry to match measured reality, or — if this is a genuine new "
                        "tracked gap — add a KNOWN_DIVERGENCES entry here citing a todo."
                    )
                )

    stale_findings: list[_Finding] = []
    for key, divergence in baseline_by_key.items():
        if key not in seen_baseline_keys:
            stale_findings.append(
                _Finding(
                    f"STALE BASELINE: KNOWN_DIVERGENCES entry for "
                    f"(asset_group={divergence.asset_group!r}, bare_key={divergence.bare_key!r}) "
                    "no longer corresponds to any real mismatch — the registries agree now. "
                    f"REMOVE this entry (ratchet-down, never carry a stale exemption). "
                    f"note={divergence.note!r}"
                )
            )

    return new_findings, stale_findings


def _validate_mapping_completeness() -> list[_Finding]:
    """Verify the explicit key-mapping is complete and current.

    Two checks:
    1. Every suffixed key in the mapping MUST exist in venue_mapping — a stale
       reference (key removed from venue_mapping but not from the mapping) is a
       drift finding.
    2. Every venue_mapping key that matches a coverage_starts bare key via the
       suffix pattern MUST be declared in the mapping — an undeclared
       relationship means the falsifier silently skips comparing that key,
       exactly the failure class this [DATA] P3 task closes.
    """
    venue_dates = _venue_mapping_combined_dates()
    findings: list[_Finding] = []

    for asset_group, mapping in _coverage_starts.BARE_KEY_TO_VENUE_MAPPING_KEYS.items():
        for bare_key, declared_keys in mapping.items():
            for declared in declared_keys:
                if declared not in venue_dates:
                    findings.append(
                        _Finding(
                            f"STALE MAPPING: BARE_KEY_TO_VENUE_MAPPING_KEYS"
                            f"[{asset_group!r}][{bare_key!r}] references "
                            f"{declared!r} which does NOT exist in venue_mapping "
                            f"venue_start_dates/source_data_start_dates. "
                            f"Remove {declared!r} from the mapping entry."
                        )
                    )

    # Reverse check — venue_mapping keys that SHOULD be in the mapping but aren't.
    # For each asset_group in the mapping, collect all declared suffixed keys
    # per bare key, then check for venue_mapping keys that match the bare-key
    # pattern but aren't declared.
    for asset_group, mapping in _coverage_starts.BARE_KEY_TO_VENUE_MAPPING_KEYS.items():
        for bare_key, declared_keys in mapping.items():
            declared_set = set(declared_keys)
            for venue_key in venue_dates:
                if venue_key in declared_set:
                    continue
                # A venue_mapping key relates to bare_key if it either matches
                # exactly or starts with bare_key + "-".
                if venue_key == bare_key or venue_key.startswith(bare_key + "-"):
                    findings.append(
                        _Finding(
                            f"UNDECLARED MAPPING: venue_mapping key "
                            f"{venue_key!r} matches coverage_starts bare key "
                            f"{bare_key!r} but is NOT listed in "
                            f"BARE_KEY_TO_VENUE_MAPPING_KEYS[{asset_group!r}]"
                            f"[{bare_key!r}]. Add it to the mapping so the "
                            f"falsifier compares these two keys."
                        )
                    )

    return findings


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    new_findings, stale_findings = find_cross_registry_mismatches()
    mapping_findings = _validate_mapping_completeness()
    findings = mapping_findings + new_findings + stale_findings

    print(
        f"Checking {sum(len(r) for r in _ASSET_GROUP_REGISTRIES.values())} coverage_starts.py "
        f"entries against venue_mapping.py ({len(KNOWN_DIVERGENCES)} tracked divergence(s) baselined, "
        f"{sum(len(v) for v in _coverage_starts.BARE_KEY_TO_VENUE_MAPPING_KEYS.values())} "
        f"key-mapping entries)..."
    )
    if findings:
        print(f"\n✗ FAILED — {len(findings)} finding(s):\n")
        for finding in findings:
            print(finding.render())
        print(
            "\nA cross-registry floor disagreement that reality contradicts (or a baseline "
            "entry that has outlived its mismatch, or an incomplete key mapping) is exactly "
            "the failure class that made SOURCE_COVERAGE_START wrong for months. Fix the "
            "registry, the baseline, or the mapping — do not silence this check."
        )
        return 1

    print("✓ No undeclared cross-registry coverage-floor divergence; baseline and mapping are current.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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

# ---------------------------------------------------------------------------
# Suffix allowlists — deliberately narrow, never a blind startswith()
# ---------------------------------------------------------------------------
# A blind ``key.startswith(bare_key + "-")`` false-matches prediction's
# ``KALSHI``/``POLYMARKET`` against the UNRELATED cefi ``KALSHI-PERP``/
# ``POLYMARKET-PERP`` — a different product on a different asset_group per
# coverage_starts.py's own comment ("Distinct from POLYMARKET/KALSHI
# prediction YES/NO markets"). Scoping the allowed suffix per asset_group
# closes that hole.

_CEFI_INSTRUMENT_SUFFIXES: tuple[str, ...] = ("SPOT", "FUTURES", "DELIVERY", "SWAP", "CDE")
_DEFI_CHAIN_SUFFIXES: tuple[str, ...] = (
    "ETHEREUM",
    "ARBITRUM",
    "POLYGON",
    "OPTIMISM",
    "BASE",
    "AVALANCHE",
    "BSC",
    "LINEA",
    "SOLANA",
    "STARKNET",
    "ZKSYNC",
)

# sports is intentionally excluded — coverage_starts imports it directly
# (structurally one SSOT), and it has its own dedicated falsifier already
# (TestOddsApiFloorDerivesFromSportsSsot).
_ASSET_GROUP_REGISTRIES: dict[str, dict[str, date]] = {
    "cefi": _coverage_starts.CEFI_SOURCE_COVERAGE_START,
    "defi": _coverage_starts.DEFI_SOURCE_COVERAGE_START,
    "tradfi": _coverage_starts.TRADFI_SOURCE_COVERAGE_START,
    "prediction": _coverage_starts.PREDICTION_SOURCE_COVERAGE_START,
}


def _related_venue_mapping_keys(asset_group: str, bare_key: str, venue_keys: Sequence[str]) -> list[str]:
    """``venue_mapping`` keys describing the SAME venue/protocol as ``bare_key``.

    ``tradfi``/``prediction`` get exact-match only (no observed finer grain
    there beyond the venue itself, and prediction's per-market ``VENUE:MARKET``
    keys are a different dimension entirely, not an instrument-type/chain
    split — excluded by construction since ``:`` never matches a ``-`` suffix).
    """
    if asset_group == "cefi":
        suffixes = _CEFI_INSTRUMENT_SUFFIXES
    elif asset_group == "defi":
        suffixes = _DEFI_CHAIN_SUFFIXES
    else:
        suffixes = ()

    related: list[str] = []
    for key in venue_keys:
        if key == bare_key:
            related.append(key)
        elif suffixes and any(key == f"{bare_key}-{suffix}" for suffix in suffixes):
            related.append(key)
    return related


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
    _KnownDivergence("defi", "CURVE", f"{_AUDIT_DOC} [DATA] P3 — small drift, unresolved"),
    _KnownDivergence("defi", "UNISWAP_V2", f"{_AUDIT_DOC} [DATA] P3 — small drift, unresolved"),
    _KnownDivergence("defi", "UNISWAP_V3", f"{_AUDIT_DOC} [DATA] P3 — small drift, unresolved"),
    _KnownDivergence("defi", "BALANCER", f"{_AUDIT_DOC} [DATA] P3 — small drift, unresolved"),
    _KnownDivergence("defi", "AAVE_V3", f"{_AUDIT_DOC} [DATA] P3 — no chain axis in coverage_starts, unresolved"),
    _KnownDivergence("defi", "LIDO", f"{_AUDIT_DOC} [DATA] P3 — small drift, unresolved"),
    _KnownDivergence("defi", "UNISWAP_V4", f"{_AUDIT_DOC} [DATA] P3 — small drift, unresolved"),
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


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    new_findings, stale_findings = find_cross_registry_mismatches()
    findings = new_findings + stale_findings

    print(
        f"Checking {sum(len(r) for r in _ASSET_GROUP_REGISTRIES.values())} coverage_starts.py "
        f"entries against venue_mapping.py ({len(KNOWN_DIVERGENCES)} tracked divergence(s) baselined)..."
    )
    if findings:
        print(f"\n✗ FAILED — {len(findings)} finding(s):\n")
        for finding in findings:
            print(finding.render())
        print(
            "\nA cross-registry floor disagreement that reality contradicts (or a baseline "
            "entry that has outlived its mismatch) is exactly the failure class that made "
            "SOURCE_COVERAGE_START wrong for months. Fix the registry or the baseline — do "
            "not silence this check."
        )
        return 1

    print("✓ No undeclared cross-registry coverage-floor divergence; baseline is current.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""UAC-registry drift census — cross-references ``VENUE_TO_ADAPTER_KEY``,
``MVP_SCOPE``, capability declarations, and per-asset-group venue-manifest
tables, flagging inconsistencies that no single registry alone would surface.

Mirrors ``features-service``'s ``catalogue_census.py`` shape (cross-registry
enumeration + canonical badging, detecting drift between live registrations and
the declared canonical set) — except the "canonical set" for UAC registries IS
the registries themselves: the drift this census detects is BETWEEN registries.

Checks performed:
  * A venue in ``VENUE_TO_ADAPTER_KEY`` mapped to ``NO_ADAPTER_YET`` —
    registered in the canonical universe but has no URDI reference adapter.
  * An adapter key with no matching capability declaration — the adapter
    resolves but no ``SourceCapability`` declares what it provides.
  * An MVP-scoped venue with no adapter key — in the MVP scope but
    unreachable (no producer wired).
  * A venue in the per-asset-group venue-manifest tables missing from
    ``VENUE_TO_ADAPTER_KEY`` — declared as a venue contract but never
    registered as resolvable.

**Source**: ``/plans/active/issues/catalogue_census_equivalents_inventory_2026_07_24.md``
finding 4 (audited 2026-07-26).

Usage::

    python -m unified_api_contracts.registry_census              # full census
    python -m unified_api_contracts.registry_census --json       # JSON output
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unified_api_contracts.registry.capability import SourceCapability

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output shapes — plain classes (not dataclasses) to pass schema-provenance QG
# ---------------------------------------------------------------------------


class RegistryCensusFinding:
    """A single drift/integrity finding."""

    def __init__(self, check: str, severity: str, detail: str) -> None:
        self.check = check
        self.severity = severity  # "error" | "warning" | "info"
        self.detail = detail


class RegistryCensusResult:
    """Full cross-registry census result."""

    def __init__(self) -> None:
        self.findings: list[RegistryCensusFinding] = []
        self.summary: dict[str, int] = {}

    def add(self, check: str, severity: str, detail: str) -> None:
        self.findings.append(RegistryCensusFinding(check, severity, detail))

    def finalize(self) -> None:
        errors = sum(1 for f in self.findings if f.severity == "error")
        warnings = sum(1 for f in self.findings if f.severity == "warning")
        infos = sum(1 for f in self.findings if f.severity == "info")
        self.summary = {
            "total_findings": len(self.findings),
            "errors": errors,
            "warnings": warnings,
            "info": infos,
            "drift_detected": (errors + warnings) > 0,
        }


# ---------------------------------------------------------------------------
# Registry readers — lazy-imported so the census is importable even when some
# registry deps are unavailable (e.g. in a test environment).
# ---------------------------------------------------------------------------


def _load_venue_to_adapter_key() -> dict[str, str]:
    """Return ``VENUE_TO_ADAPTER_KEY`` from the UAC registry."""
    from unified_api_contracts.registry.venue_adapter_keys import (
        VENUE_TO_ADAPTER_KEY,
    )

    return dict(VENUE_TO_ADAPTER_KEY)


def _load_no_adapter_yet() -> str:
    from unified_api_contracts.registry.venue_adapter_keys import NO_ADAPTER_YET

    return NO_ADAPTER_YET


def _load_capability_declarations() -> list[SourceCapability]:
    """Return all registered capability declarations."""
    from unified_api_contracts.registry.capability_data import (
        CAPABILITY_DECLARATIONS,
    )

    return list(CAPABILITY_DECLARATIONS)


def _load_venue_manifest() -> dict[str, object]:
    """Return the per-asset-group venue-manifest table."""
    from unified_api_contracts.registry.venue_manifest import VENUE_MANIFEST

    return dict(VENUE_MANIFEST)


def _load_mvp_scope() -> dict[str, object]:
    """Return the MVP scope config."""
    from unified_api_contracts.canonical.crosscutting.mvp_scope import MVP_SCOPE

    return dict(MVP_SCOPE)


def _load_venues_by_asset_group() -> dict[str, frozenset[str]]:
    """Return ``VENUES_BY_ASSET_GROUP`` from market_data_categories."""
    from unified_api_contracts.registry.market_data_categories import (
        VENUES_BY_ASSET_GROUP,
    )

    return {k: frozenset(v) for k, v in VENUES_BY_ASSET_GROUP.items()}


# ---------------------------------------------------------------------------
# Check 1: NO_ADAPTER_YET venues — registered but unadapted
# ---------------------------------------------------------------------------


def _check_no_adapter_yet_venues(
    venue_to_adapter: dict[str, str], no_adapter_sentinel: str
) -> list[RegistryCensusFinding]:
    """Flag every venue declared adapterless via ``NO_ADAPTER_YET``."""
    findings: list[RegistryCensusFinding] = []
    for venue, adapter in sorted(venue_to_adapter.items()):
        if adapter == no_adapter_sentinel:
            findings.append(
                RegistryCensusFinding(
                    check="no_adapter_yet",
                    severity="warning",
                    detail=(
                        f"Venue {venue!r} is registered in VENUE_TO_ADAPTER_KEY"
                        " but mapped to NO_ADAPTER_YET — no URDI reference adapter exists"
                    ),
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Check 2: Adapter keys vs capability declarations
# ---------------------------------------------------------------------------


def _check_adapter_keys_vs_capabilities(
    venue_to_adapter: dict[str, str],
    capabilities: list[SourceCapability],
    no_adapter_sentinel: str,
) -> list[RegistryCensusFinding]:
    """Flag adapter keys with no matching capability, and capabilities with no adapter key."""
    findings: list[RegistryCensusFinding] = []

    # Collect all distinct adapter keys (excluding NO_ADAPTER_YET)
    adapter_keys: set[str] = {v for v in venue_to_adapter.values() if v != no_adapter_sentinel}

    # Collect all capability source_ids
    capability_ids: set[str] = {cap.source for cap in capabilities}

    # Adapter keys without a matching capability
    for ak in sorted(adapter_keys - capability_ids):
        venues = sorted(v for v, a in venue_to_adapter.items() if a == ak)
        findings.append(
            RegistryCensusFinding(
                check="adapter_without_capability",
                severity="warning",
                detail=(
                    f"Adapter key {ak!r} (used by {len(venues)} venue(s): {venues})"
                    " has no matching capability declaration in CAPABILITY_DECLARATIONS"
                ),
            )
        )

    # Capabilities without any adapter-key venue
    for cid in sorted(capability_ids - adapter_keys):
        findings.append(
            RegistryCensusFinding(
                check="capability_without_adapter",
                severity="info",
                detail=(
                    f"Capability source {cid!r} has a capability declaration"
                    " but no venue maps to it in VENUE_TO_ADAPTER_KEY"
                ),
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Check 3: MVP-scoped venues vs adapter keys
# ---------------------------------------------------------------------------


def _extract_mvp_venues(mvp_scope: dict[str, object]) -> dict[str, frozenset[str]]:
    """Extract venue sets from MVP scope rules, grouped by asset_group."""
    venues_by_ag: dict[str, set[str]] = {}

    for ag, rule in mvp_scope.items():
        if ag == "models":
            continue  # ModelsMvpRule has no venue attribute
        ag_str = str(ag)
        rule_venues: Iterable[str] | None = getattr(rule, "venues", None)
        if rule_venues is not None:
            venues_by_ag.setdefault(ag_str, set()).update(rule_venues)

    return {k: frozenset(v) for k, v in venues_by_ag.items()}


def _check_mvp_venues_vs_adapter_keys(
    mvp_scope: dict[str, object],
    venue_to_adapter: dict[str, str],
    no_adapter_sentinel: str,
) -> list[RegistryCensusFinding]:
    """Flag MVP-scoped venues missing from VENUE_TO_ADAPTER_KEY or mapped to NO_ADAPTER_YET."""
    findings: list[RegistryCensusFinding] = []
    mvp_venues = _extract_mvp_venues(mvp_scope)

    for ag, venues in sorted(mvp_venues.items()):
        for venue in sorted(venues):
            if venue not in venue_to_adapter:
                findings.append(
                    RegistryCensusFinding(
                        check="mvp_venue_no_adapter_key",
                        severity="error",
                        detail=(
                            f"MVP-scoped venue {venue!r} (asset_group={ag!r})"
                            " is NOT in VENUE_TO_ADAPTER_KEY — unreachable, no producer wired"
                        ),
                    )
                )
            elif venue_to_adapter[venue] == no_adapter_sentinel:
                findings.append(
                    RegistryCensusFinding(
                        check="mvp_venue_no_adapter",
                        severity="warning",
                        detail=(
                            f"MVP-scoped venue {venue!r} (asset_group={ag!r})"
                            " is mapped to NO_ADAPTER_YET — in MVP scope but has no URDI adapter"
                        ),
                    )
                )

    return findings


# ---------------------------------------------------------------------------
# Check 4: Venue-manifest vs adapter keys
# ---------------------------------------------------------------------------


def _check_venue_manifest_vs_adapter_keys(
    venue_manifest: dict[str, object],
    venue_to_adapter: dict[str, str],
) -> list[RegistryCensusFinding]:
    """Flag venues in the venue-manifest tables missing from VENUE_TO_ADAPTER_KEY."""
    findings: list[RegistryCensusFinding] = []

    manifest_venues: set[str] = set(venue_manifest.keys())
    # The venue-manifest also carries internal-service ContractEntry keys;
    # filter to only those that look like venue names (uppercase, hyphenated).
    # We still flag every key not in VENUE_TO_ADAPTER_KEY as the census is
    # meant to surface drift — but internal service names (lowercase, snake_case)
    # are expected to not be in VENUE_TO_ADAPTER_KEY.
    internal_service_patterns: frozenset[str] = frozenset(
        {
            "unified_trading_system",
            "unified_trading_data",
        }
    )

    for mv in sorted(manifest_venues):
        if mv in venue_to_adapter:
            continue
        if mv in internal_service_patterns:
            continue
        # Skip keys that are clearly internal service entry keys (snake_case
        # or dot-separated) rather than canonical venue names.
        if "_" in mv or "." in mv:
            continue
        findings.append(
            RegistryCensusFinding(
                check="venue_manifest_not_in_adapter_keys",
                severity="warning",
                detail=(
                    f"Venue {mv!r} is in VENUE_MANIFEST (venue-manifest tables)"
                    " but NOT in VENUE_TO_ADAPTER_KEY — declared contract exists but no adapter-key mapping"
                ),
            )
        )

    # Reverse: venues in adapter keys missing from venue-manifest
    for venue in sorted(venue_to_adapter):
        if venue not in manifest_venues:
            findings.append(
                RegistryCensusFinding(
                    check="adapter_key_not_in_venue_manifest",
                    severity="info",
                    detail=(
                        f"Venue {venue!r} is in VENUE_TO_ADAPTER_KEY but NOT in VENUE_MANIFEST"
                        " — has an adapter but no declared contract endpoint details"
                    ),
                )
            )

    return findings


# ---------------------------------------------------------------------------
# Check 5: VENUES_BY_ASSET_GROUP vs VENUE_TO_ADAPTER_KEY
# ---------------------------------------------------------------------------


def _check_venues_by_ag_vs_adapter_keys(
    venues_by_ag: dict[str, frozenset[str]],
    venue_to_adapter: dict[str, str],
) -> list[RegistryCensusFinding]:
    """Flag venues in VENUES_BY_ASSET_GROUP missing from VENUE_TO_ADAPTER_KEY."""
    findings: list[RegistryCensusFinding] = []

    all_ag_venues: set[str] = set()
    for venues in venues_by_ag.values():
        all_ag_venues.update(venues)

    # Venues in VENUES_BY_ASSET_GROUP but not in VENUE_TO_ADAPTER_KEY
    for venue in sorted(all_ag_venues - set(venue_to_adapter)):
        # Find which asset groups contain this venue
        ags = sorted(ag for ag, venues in venues_by_ag.items() if venue in venues)
        findings.append(
            RegistryCensusFinding(
                check="venues_by_ag_not_in_adapter_keys",
                severity="error",
                detail=(
                    f"Venue {venue!r} is in VENUES_BY_ASSET_GROUP ({', '.join(ags)})"
                    " but NOT in VENUE_TO_ADAPTER_KEY — canonical venue with no adapter mapping"
                ),
            )
        )

    # Venues in VENUE_TO_ADAPTER_KEY but not in any VENUES_BY_ASSET_GROUP
    for venue in sorted(set(venue_to_adapter) - all_ag_venues):
        findings.append(
            RegistryCensusFinding(
                check="adapter_key_not_in_venues_by_ag",
                severity="info",
                detail=(
                    f"Venue {venue!r} is in VENUE_TO_ADAPTER_KEY but NOT in any"
                    " VENUES_BY_ASSET_GROUP asset group — has an adapter but not assigned to any asset group"
                ),
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Check 6: PROTOCOL_TO_ADAPTER_KEY integrity
# ---------------------------------------------------------------------------


def _check_protocol_adapter_key_chain(
    venue_to_adapter: dict[str, str],
) -> list[RegistryCensusFinding]:
    """Verify every referenced adapter key in PROTOCOL_TO_ADAPTER_KEY is a
    real adapter key that at least one venue maps to."""
    from unified_api_contracts.registry.venue_adapter_keys import (
        PROTOCOL_TO_ADAPTER_KEY,
    )

    findings: list[RegistryCensusFinding] = []
    all_adapter_keys: set[str] = set(venue_to_adapter.values())

    for protocol, ak in sorted(PROTOCOL_TO_ADAPTER_KEY.items()):
        if ak not in all_adapter_keys:
            findings.append(
                RegistryCensusFinding(
                    check="protocol_adapter_key_orphan",
                    severity="warning",
                    detail=(
                        f"PROTOCOL_TO_ADAPTER_KEY[{protocol!r}] = {ak!r},"
                        f" but no venue in VENUE_TO_ADAPTER_KEY maps to {ak!r}"
                    ),
                )
            )

    return findings


# ---------------------------------------------------------------------------
# Full census
# ---------------------------------------------------------------------------


def run_full_census() -> RegistryCensusResult:
    """Run the full UAC-registry drift census."""
    result = RegistryCensusResult()

    # Load all registries
    venue_to_adapter = _load_venue_to_adapter_key()
    no_adapter_sentinel = _load_no_adapter_yet()
    capabilities = _load_capability_declarations()
    venue_manifest = _load_venue_manifest()
    mvp_scope = _load_mvp_scope()
    venues_by_ag = _load_venues_by_asset_group()

    # Check 1: NO_ADAPTER_YET venues
    result.findings.extend(_check_no_adapter_yet_venues(venue_to_adapter, no_adapter_sentinel))

    # Check 2: Adapter keys ↔ capability declarations
    result.findings.extend(_check_adapter_keys_vs_capabilities(venue_to_adapter, capabilities, no_adapter_sentinel))

    # Check 3: MVP-scoped venues vs adapter keys
    result.findings.extend(_check_mvp_venues_vs_adapter_keys(mvp_scope, venue_to_adapter, no_adapter_sentinel))

    # Check 4: Venue-manifest vs adapter keys
    result.findings.extend(_check_venue_manifest_vs_adapter_keys(venue_manifest, venue_to_adapter))

    # Check 5: VENUES_BY_ASSET_GROUP vs VENUE_TO_ADAPTER_KEY
    result.findings.extend(_check_venues_by_ag_vs_adapter_keys(venues_by_ag, venue_to_adapter))

    # Check 6: PROTOCOL_TO_ADAPTER_KEY integrity
    result.findings.extend(_check_protocol_adapter_key_chain(venue_to_adapter))

    result.finalize()
    return result


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def _census_to_json(result: RegistryCensusResult) -> str:
    """Serialize a full census result to compact JSON."""
    payload: dict[str, object] = {
        "findings": [
            {
                "check": f.check,
                "severity": f.severity,
                "detail": f.detail,
            }
            for f in result.findings
        ],
        "summary": result.summary,
    }
    return json.dumps(payload, indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# Human-readable output
# ---------------------------------------------------------------------------


def _write_line(text: str = "") -> None:
    """Write a line to stdout — QG-safe alternative to ``print()``."""
    sys.stdout.write(text + "\n")


def _print_census(result: RegistryCensusResult) -> None:
    """Human-readable census summary to stdout."""
    s = result.summary
    _write_line(f"UAC Registry Drift Census — {s['total_findings']} finding(s)")
    _write_line(
        f"  errors={s['errors']}  warnings={s['warnings']}  info={s['info']}  drift_detected={s['drift_detected']}"
    )
    _write_line()

    by_check: dict[str, list[RegistryCensusFinding]] = {}
    for f in result.findings:
        by_check.setdefault(f.check, []).append(f)

    for check_name, findings in sorted(by_check.items()):
        _write_line(f"--- {check_name} ({len(findings)} finding(s)) ---")
        for f in findings:
            tag = {"error": "ERR", "warning": "WARN", "info": "INFO"}.get(f.severity, f.severity.upper())
            _write_line(f"  [{tag}] {f.detail}")
        _write_line()


# ---------------------------------------------------------------------------
# CLI — ``python -m unified_api_contracts.registry_census [--json]``
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """Entry point for ``python -m unified_api_contracts.registry_census``."""
    parser = argparse.ArgumentParser(description="UAC-registry drift census")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of human-readable")
    args = parser.parse_args(argv)

    result = run_full_census()

    if args.json:
        _write_line(_census_to_json(result))
    else:
        _print_census(result)

    # Exit non-zero if errors found (for CI/gate integration)
    if result.summary.get("errors", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])

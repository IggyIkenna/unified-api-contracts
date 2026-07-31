"""Cross-repo invariant: cefi registry data-dicts vs instruments-service's real expected universe.

Closes Layer 2 of breaking_change_differ_blind_to_registry_data_dicts_2026_07_09.md: even after
the AST differ (scripts/cicd/detect_breaking_change.py) is taught to treat registry data-dicts as
contract surface (Layer 1), `full-workspace-sit` itself ran GREEN on the 2026-07-07/08 incident
because no test re-derived instruments-service's real `build_expected('cefi')` from the LIVE UAC
registry. This test is that missing backstop.

Loads instruments-service's `scripts/expected_universe.py` directly by file path (it is a
top-level dev script, not part of the installable `instruments_service` package, so it cannot be
imported normally even when the sibling repo is checked out) and:

  (a) runs the real `build_expected('cefi')` against the live UAC registry in THIS process —
      proves the producer executes cleanly end to end, not just that it type-checks;
  (b) asserts every `VENUE_DATA_TYPE_CAPABILITIES` entry (excluding the separately-tracked DeFi
      merge) resolves to a venue declared somewhere in `VENUES_BY_ASSET_GROUP` — a capability
      entry for a venue nobody declares is either dead code or a stale/removed vendor (exactly the
      `POLYGON` entry this same fix removed — Polygon.io was retired as a tradfi source 2026-07-19
      but its capability block was never cleaned up until this invariant caught it);
  (c) asserts every `CEFI_VENUE_FOLD` target venue (the writer-dialect fold — e.g. OKX-SWAP/
      OKX-FUTURES -> OKX) actually appears in the real `build_expected('cefi')` output — a fold
      target that produces no expected tuples means captured data folds into a venue Layer-1
      never expects, silently invisible (the exact 23fa3a99 symptom: 75->71 tuples, zero CI catch).

Skips in per-repo CI (instruments-service sibling absent, matching the established pattern in
test_utl_cross_repo_invariant.py); runs for real in the full-workspace SIT where all repos are
assembled as siblings — wired into system-integration-tests/scripts/run_cross_repo_invariants.sh.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _workspace_root() -> Path:
    """tests/<file>.py -> tests/ -> repo root -> workspace root."""
    return Path(__file__).resolve().parents[2]


def _instruments_service_root() -> Path:
    return _workspace_root() / "instruments-service"


def _load_expected_universe_module() -> ModuleType:
    """Load instruments-service/scripts/expected_universe.py by file path.

    Not part of the installable `instruments_service` package (it lives in the repo's
    top-level `scripts/` dev-script dir), so a normal `import instruments_service...`
    cannot reach it even when the sibling repo is pip-installed. Direct file-path
    loading (mirroring tests/unit/test_detect_breaking_change.py's own pattern in
    unified-trading-pm) sidesteps that without needing a packaging change, and avoids
    colliding with any other repo's own top-level `scripts` module/namespace.
    """
    path = _instruments_service_root() / "scripts" / "expected_universe.py"
    spec = importlib.util.spec_from_file_location("is_expected_universe_invariant", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["is_expected_universe_invariant"] = module
    spec.loader.exec_module(module)
    return module


def _require_instruments_service_sibling() -> None:
    if not _instruments_service_root().is_dir():
        pytest.skip(
            "per-repo CI checkout: instruments-service not present at "
            f"{_instruments_service_root()}; cross-repo cefi expected-universe invariant "
            "runs in full-workspace SIT only"
        )


def test_build_expected_cefi_runs_against_live_registry() -> None:
    """`build_expected('cefi')` executes end to end against the live UAC registry."""
    _require_instruments_service_sibling()
    module = _load_expected_universe_module()

    expected = module.build_expected("cefi")

    assert expected, "build_expected('cefi') returned an EMPTY expected universe — producer broke"
    for venue, instrument_type, data_type in expected:
        assert venue and instrument_type and data_type, (
            f"malformed expected tuple: {(venue, instrument_type, data_type)}"
        )


def test_venue_data_type_capabilities_venues_are_declared() -> None:
    """Every non-DeFi VENUE_DATA_TYPE_CAPABILITIES entry names a venue declared in
    VENUES_BY_ASSET_GROUP.

    DeFi capability entries are excluded — defi venue validity is a genuinely separate,
    dynamically-computed axis (PROTOCOL_CAPABILITIES / the live "defi" VENUES_BY_ASSET_GROUP
    list), not a static registry a Removed-key check can safely assert on here.
    """
    _require_instruments_service_sibling()

    from unified_api_contracts.registry.defi_venue_capabilities import (
        DEFI_VENUE_DATA_TYPE_CAPABILITIES,
    )
    from unified_api_contracts.registry.market_data_categories import (
        ALL_VENUES,
        VENUE_DATA_TYPE_CAPABILITIES,
    )

    declared = set(ALL_VENUES)
    non_defi_capability_venues = {v for v in VENUE_DATA_TYPE_CAPABILITIES if v not in DEFI_VENUE_DATA_TYPE_CAPABILITIES}
    missing = sorted(non_defi_capability_venues - declared)
    assert not missing, (
        f"VENUE_DATA_TYPE_CAPABILITIES declares capabilities for venue(s) not present in "
        f"VENUES_BY_ASSET_GROUP: {missing}. Either the venue was removed from "
        "VENUES_BY_ASSET_GROUP and this capability block is stale dead code (see the POLYGON "
        "removal this same invariant caught), or it needs to be added back to "
        "VENUES_BY_ASSET_GROUP."
    )


def test_cefi_venue_fold_targets_are_expected() -> None:
    """Every CEFI_VENUE_FOLD target venue produces at least one tuple in build_expected('cefi').

    A fold target with zero expected tuples means captured data (folded from a Tardis-grain
    dialect like OKX-SWAP/OKX-FUTURES) lands on a venue the Layer-1 expected-universe producer
    never enumerates — real data becomes silently invisible, the exact 23fa3a99 symptom.
    """
    _require_instruments_service_sibling()
    module = _load_expected_universe_module()

    from unified_api_contracts.registry.market_data_categories import CEFI_VENUE_FOLD

    expected = module.build_expected("cefi")
    venues_in_expected = {venue for venue, _instrument_type, _data_type in expected}

    fold_targets = sorted(set(CEFI_VENUE_FOLD.values()))
    missing = [v for v in fold_targets if v not in venues_in_expected]
    assert not missing, (
        f"CEFI_VENUE_FOLD target venue(s) produce NO tuples in build_expected('cefi'): {missing}. "
        "Data captured under a dialect that folds to one of these venues would be silently "
        "invisible to Layer-1 completeness."
    )

"""Cross-repo invariant: greeks-service greeks/risk output contract matches consumers.

Validates that greeks-service's kernel public API surface (symbols, dataclass field
sets, and GreekResult slot names) still aligns with the UAC canonical types that
consuming sibling repos and the strategy layer depend on.

Uses static AST analysis for the greeks-service source (not installed in UAC venv).
UAC canonical types are imported directly (installed in this venv).

Negative-control contract: removing any symbol in EXPECTED_KERNEL_SYMBOLS from
``greeks_service/kernels/__init__.py``, or removing a required field from
``SurfacePoint`` / ``IVSurface`` / ``GreekResult``, makes these tests fail — that IS
the guard for a cross-repo breaking change.

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — task -025
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from unified_api_contracts.canonical.domain.derivatives.greeks import (
    CanonicalGreeksSnapshot,
    CanonicalImpliedVolSurface,
    CanonicalIVSurfacePoint,
)

# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _workspace_root() -> Path:
    """tests/<file>.py → tests/ → repo root → workspace root."""
    return Path(__file__).resolve().parents[2]


def _greeks_root() -> Path:
    return _workspace_root() / "greeks-service" / "greeks_service"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _exported_names(init_path: Path) -> set[str]:
    """Return the set of names declared/exported in a module via AST."""
    src = init_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(init_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                exported = alias.asname if alias.asname else alias.name
                names.add(exported)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                exported = alias.asname if alias.asname else alias.name.split(".")[0]
                names.add(exported)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def _dataclass_fields(source_path: Path, class_name: str) -> set[str]:
    """Return the annotated field names declared in a dataclass via AST.

    Collects all AnnAssign names in the class body (ignores ClassVar / __dunder__).
    """
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            fields: set[str] = set()
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    name = stmt.target.id
                    if not name.startswith("__"):
                        fields.add(name)
            return fields
    return set()


def _slots_names(source_path: Path, class_name: str) -> set[str]:
    """Return the string literals in __slots__ = (...) for a class via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for stmt in node.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                for t in stmt.targets:
                    if isinstance(t, ast.Name) and t.id == "__slots__":
                        slots: set[str] = set()
                        val = stmt.value
                        elts = val.elts if isinstance(val, (ast.Tuple, ast.List)) else []
                        for elt in elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                slots.add(elt.value)
                        return slots
    return set()


# ---------------------------------------------------------------------------
# Expected contracts
# ---------------------------------------------------------------------------

# Public symbols that must remain in greeks_service/kernels/__init__.py.
# Consumers (via SIT cassettes + strategy layer) depend on all of these.
EXPECTED_KERNEL_SYMBOLS: frozenset[str] = frozenset(
    [
        "BlackScholesKernel",
        "GreekKernel",
        "GreekResult",
        "IVSurface",
        "OptionQuote",
        "SurfacePoint",
        "assemble_iv_surface",
        "implied_vol_from_price",
    ]
)

# SurfacePoint field names that must match CanonicalIVSurfacePoint (single-canonical
# convergence — see codex/04-architecture/greeks-service-overview.md).
EXPECTED_SURFACE_POINT_FIELDS: frozenset[str] = frozenset(
    [
        "instrument_key",
        "strike",
        "expiry",
        "right",
        "moneyness",
        "tenor_years",
        "implied_vol",
        "iv_source",
    ]
)

# IVSurface core fields consumed when serialising to CanonicalImpliedVolSurface.
# (venue is UAC-only metadata; by_expiry/by_strike are read-time indices not persisted)
EXPECTED_IV_SURFACE_FIELDS: frozenset[str] = frozenset(
    [
        "underlying",
        "underlying_mark",
        "as_of",
        "points",
    ]
)

# GreekResult slotted fields that flow into CanonicalGreeksSnapshot greeks columns.
EXPECTED_GREEK_RESULT_SLOTS: frozenset[str] = frozenset(
    [
        "delta",
        "gamma",
        "vega",
        "theta",
        "rho",
    ]
)


# ---------------------------------------------------------------------------
# Sibling guard (skip in per-repo CI; fail LOUDLY in full-workspace SIT)
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    greeks_sibling = _workspace_root() / "greeks-service"
    if not greeks_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: greeks-service not present at {greeks_sibling}; "
            "cross-repo greeks-service invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_greeks_service_kernel_symbols_stable() -> None:
    """All expected public symbols are declared in greeks_service/kernels/__init__.py.

    Skips in per-repo CI (no greeks-service sibling); runs in full-workspace SIT.
    Fails CLOSED if any expected symbol disappears — that is the cross-repo breaking
    change this invariant exists to catch (consumers depend on these names at import
    time via SIT cassettes + the strategy routing layer).
    """
    _skip_if_absent()

    kernels_init = _greeks_root() / "kernels" / "__init__.py"
    assert kernels_init.is_file(), f"greeks-service kernels/__init__.py missing at {kernels_init}"

    exported = _exported_names(kernels_init)
    missing = sorted(EXPECTED_KERNEL_SYMBOLS - exported)
    assert not missing, (
        f"greeks_service/kernels/__init__.py is MISSING the following public symbols "
        f"that the greeks/risk output contract depends on:\n  {missing}\n\n"
        "Removing or renaming these is a cross-repo BREAKING CHANGE — add the "
        "renamed/moved symbol back as a re-export or update the consuming repos first."
    )


def test_greeks_service_surface_point_fields_match_canonical() -> None:
    """SurfacePoint dataclass fields match CanonicalIVSurfacePoint (single-canonical convergence).

    The UAC docs explicitly state that ``CanonicalIVSurfacePoint`` mirrors
    ``greeks_service.kernels.iv_surface.SurfacePoint`` field-for-field.  If a field is
    removed or renamed in SurfacePoint, the serialisation to ``CanonicalIVSurfacePoint``
    breaks silently — this test catches that before SIT validates the promote.
    """
    _skip_if_absent()

    iv_surface_py = _greeks_root() / "kernels" / "iv_surface.py"
    assert iv_surface_py.is_file(), f"greeks-service kernels/iv_surface.py missing at {iv_surface_py}"

    fields = _dataclass_fields(iv_surface_py, "SurfacePoint")
    missing = sorted(EXPECTED_SURFACE_POINT_FIELDS - fields)
    assert not missing, (
        f"greeks_service.kernels.iv_surface.SurfacePoint is MISSING fields "
        f"that CanonicalIVSurfacePoint consumers expect:\n  {missing}\n\n"
        "Removing these fields breaks the single-canonical convergence between "
        "greeks-service internal types and the UAC wire-format schema."
    )


def test_greeks_service_iv_surface_core_fields_present() -> None:
    """IVSurface core fields consumed when serialising to CanonicalImpliedVolSurface are present.

    CanonicalImpliedVolSurface is assembled from IVSurface; the ``underlying``,
    ``underlying_mark``, ``as_of``, and ``points`` fields must remain stable.
    """
    _skip_if_absent()

    iv_surface_py = _greeks_root() / "kernels" / "iv_surface.py"
    assert iv_surface_py.is_file(), f"greeks-service kernels/iv_surface.py missing at {iv_surface_py}"

    fields = _dataclass_fields(iv_surface_py, "IVSurface")
    missing = sorted(EXPECTED_IV_SURFACE_FIELDS - fields)
    assert not missing, (
        f"greeks_service.kernels.iv_surface.IVSurface is MISSING core fields "
        f"consumed when building CanonicalImpliedVolSurface:\n  {missing}\n\n"
        "These fields are required for the greeks-service → UAC serialisation path."
    )


def test_greeks_service_greek_result_slots_stable() -> None:
    """GreekResult.__slots__ contains the greeks that flow into CanonicalGreeksSnapshot.

    CanonicalGreeksSnapshot carries delta/gamma/vega/theta/rho from GreekResult.
    Removing any of these slots silently drops a column from the output schema.
    """
    _skip_if_absent()

    black_scholes_py = _greeks_root() / "kernels" / "black_scholes.py"
    assert black_scholes_py.is_file(), (
        f"greeks-service kernels/black_scholes.py missing at {black_scholes_py}"
    )

    slots = _slots_names(black_scholes_py, "GreekResult")
    missing = sorted(EXPECTED_GREEK_RESULT_SLOTS - slots)
    assert not missing, (
        f"greeks_service.kernels.black_scholes.GreekResult is MISSING __slots__ "
        f"that flow into CanonicalGreeksSnapshot greeks columns:\n  {missing}\n\n"
        "These fields are emitted to the PricingLedger and consumed by the strategy layer."
    )


def test_greeks_service_uac_canonical_types_present() -> None:
    """UAC exports the canonical greeks types that downstream consumers import.

    Confirms CanonicalGreeksSnapshot, CanonicalIVSurfacePoint, and
    CanonicalImpliedVolSurface are still reachable from unified_api_contracts.
    This is the consumer-side of the same contract — the greeks-service writes
    to these shapes; other services read from them.
    """
    _skip_if_absent()

    canonical_snapshot_fields = set(CanonicalGreeksSnapshot.model_fields.keys())
    for greek_field in EXPECTED_GREEK_RESULT_SLOTS:
        assert greek_field in canonical_snapshot_fields, (
            f"CanonicalGreeksSnapshot.model_fields is MISSING '{greek_field}' — "
            "this field is emitted by greeks-service and consumed by the strategy layer."
        )

    canonical_surface_point_fields = set(CanonicalIVSurfacePoint.model_fields.keys())
    for field in EXPECTED_SURFACE_POINT_FIELDS:
        assert field in canonical_surface_point_fields, (
            f"CanonicalIVSurfacePoint.model_fields is MISSING '{field}' — "
            "this field mirrors greeks_service.kernels.iv_surface.SurfacePoint."
        )

    canonical_surface_fields = set(CanonicalImpliedVolSurface.model_fields.keys())
    for field in EXPECTED_IV_SURFACE_FIELDS:
        assert field in canonical_surface_fields, (
            f"CanonicalImpliedVolSurface.model_fields is MISSING '{field}' — "
            "this field mirrors greeks_service.kernels.iv_surface.IVSurface."
        )

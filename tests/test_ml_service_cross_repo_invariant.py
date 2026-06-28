"""Cross-repo invariant: ml-service model/feature contract matches features-service + strategy.

Validates that ml-service's published prediction contract (CascadePredictionEvent,
PredictionSnapshot, InferenceRequest, InferenceResult) aligns with the UAC canonical
types that strategy-service and other consumers import.  Also validates ml-service's
inference engine public API surface (symbols) via AST.

Uses static AST analysis for the ml-service source (not installed in UAC venv).
UAC canonical types are imported directly (installed in this venv).

Negative-control contract: removing any field from PredictionSnapshot / CascadePredictionEvent
or any symbol from the engine's __init__.py makes the relevant test fail — that IS the guard
for a cross-repo breaking change (strategy-service deserialises these fields by name).

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — task -004
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from unified_api_contracts.internal import (
    CascadePredictionEvent,
    InferenceResult,
    PredictionSnapshot,
)
from unified_api_contracts.internal.domain.ml.schemas import (
    InferenceRequest,
)

# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _workspace_root() -> Path:
    """tests/<file>.py → tests/ → repo root → workspace root."""
    return Path(__file__).resolve().parents[2]


def _ml_root() -> Path:
    return _workspace_root() / "ml-service" / "ml_service"


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
    """Return the annotated field names declared in a dataclass via AST."""
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


# ---------------------------------------------------------------------------
# Expected contracts
# ---------------------------------------------------------------------------

# Public symbols that must remain in ml_service/inference/engine/__init__.py.
# strategy-service + features-service depend on InferenceOrchestrator; the
# inference_result_to_ml_prediction and build_model_scorecard functions are
# consumed by the inference pipeline plumbing.
EXPECTED_ENGINE_SYMBOLS: frozenset[str] = frozenset(
    [
        "DriftMonitor",
        "InferenceOrchestrator",
        "build_model_scorecard",
        "inference_result_to_ml_prediction",
    ]
)

# PredictionSnapshot fields consumed by strategy-service/adapters/cascade_subscriber.py.
# strategy-service reads each of these by name via _parse_prediction_snapshot().
# Removing any field silently drops a column from the deserialized event.
EXPECTED_PREDICTION_SNAPSHOT_FIELDS: frozenset[str] = frozenset(
    [
        "instrument_id",
        "timeframe",
        "direction",
        "confidence",
        "model_id",
        "predicted_at",
    ]
)

# CascadePredictionEvent fields consumed by strategy-service/adapters/cascade_subscriber.py.
# strategy-service reads cascade_confidence_score and cascade_aligned directly
# (it does NOT re-implement cross-TF logic); trigger_direction + context inform entry timing.
EXPECTED_CASCADE_EVENT_FIELDS: frozenset[str] = frozenset(
    [
        "instrument_id",
        "profile_name",
        "trigger_timeframe",
        "trigger_direction",
        "trigger_confidence",
        "context",
        "cascade_confidence_score",
        "cascade_aligned",
        "recommended_entry_timeframes",
        "published_at",
    ]
)

# InferenceRequest fields: the wire shape that callers send to ml-service.
EXPECTED_INFERENCE_REQUEST_FIELDS: frozenset[str] = frozenset(
    [
        "instrument_id",
        "features",
        "timeframe",
        "target_type",
    ]
)

# InferenceResult fields: the wire shape that ml-service returns to callers.
EXPECTED_INFERENCE_RESULT_FIELDS: frozenset[str] = frozenset(
    [
        "request_id",
        "model_id",
        "instrument_id",
        "prediction",
        "confidence",
        "target_type",
    ]
)


# ---------------------------------------------------------------------------
# Sibling guard (skip in per-repo CI; fail LOUDLY in full-workspace SIT)
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    ml_sibling = _workspace_root() / "ml-service"
    if not ml_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: ml-service not present at {ml_sibling}; "
            "cross-repo ml-service invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ml_service_engine_symbols_stable() -> None:
    """All expected public symbols are declared in ml_service/inference/engine/__init__.py.

    Skips in per-repo CI (no ml-service sibling); runs in full-workspace SIT.
    Fails CLOSED if any expected symbol disappears — that is the cross-repo breaking
    change this invariant exists to catch (the inference pipeline depends on these
    symbols being importable from ml_service.inference.engine).
    """
    _skip_if_absent()

    engine_init = _ml_root() / "inference" / "engine" / "__init__.py"
    assert engine_init.is_file(), f"ml-service inference/engine/__init__.py missing at {engine_init}"

    exported = _exported_names(engine_init)
    missing = sorted(EXPECTED_ENGINE_SYMBOLS - exported)
    assert not missing, (
        f"ml_service/inference/engine/__init__.py is MISSING the following public symbols "
        f"that the model/feature contract depends on:\n  {missing}\n\n"
        "Removing or renaming these is a cross-repo BREAKING CHANGE — add the "
        "renamed/moved symbol back as a re-export or update the consuming repos first."
    )


def test_ml_service_prediction_snapshot_fields_stable() -> None:
    """PredictionSnapshot dataclass fields match the consumer contract in strategy-service.

    strategy-service/adapters/cascade_subscriber.py reads PredictionSnapshot fields by
    name in _parse_prediction_snapshot().  Removing any field silently drops data from
    the deserialized cascade event — this test catches that before SIT validates the promote.
    """
    _skip_if_absent()

    cascade_py = (
        _workspace_root()
        / "unified-api-contracts"
        / "unified_api_contracts"
        / "internal"
        / "domain"
        / "ml_inference_service"
        / "cascade_prediction.py"
    )
    assert cascade_py.is_file(), f"UAC cascade_prediction.py missing at {cascade_py}"

    fields = _dataclass_fields(cascade_py, "PredictionSnapshot")
    missing = sorted(EXPECTED_PREDICTION_SNAPSHOT_FIELDS - fields)
    assert not missing, (
        f"PredictionSnapshot is MISSING fields that strategy-service cascade_subscriber "
        f"reads by name:\n  {missing}\n\n"
        "These fields are deserialized from PubSub by _parse_prediction_snapshot() — "
        "removing them silently drops data from the cross-service payload."
    )


def test_ml_service_cascade_event_fields_stable() -> None:
    """CascadePredictionEvent dataclass fields match the consumer contract in strategy-service.

    strategy-service reads cascade_confidence_score, cascade_aligned, trigger_direction,
    context, and other fields directly from CascadePredictionEvent — it does NOT
    re-implement cross-TF logic, so all of these must remain stable.
    """
    _skip_if_absent()

    cascade_py = (
        _workspace_root()
        / "unified-api-contracts"
        / "unified_api_contracts"
        / "internal"
        / "domain"
        / "ml_inference_service"
        / "cascade_prediction.py"
    )
    assert cascade_py.is_file(), f"UAC cascade_prediction.py missing at {cascade_py}"

    fields = _dataclass_fields(cascade_py, "CascadePredictionEvent")
    missing = sorted(EXPECTED_CASCADE_EVENT_FIELDS - fields)
    assert not missing, (
        f"CascadePredictionEvent is MISSING fields that strategy-service cascade_subscriber "
        f"reads directly:\n  {missing}\n\n"
        "These fields are deserialized by _deserialize_cascade_event() and used to build "
        "the direction signal — removing them breaks the strategy layer's prediction pipeline."
    )


def test_ml_service_uac_canonical_types_importable() -> None:
    """UAC exports the canonical ML inference types that ml-service and consumers import.

    Confirms PredictionSnapshot, CascadePredictionEvent, InferenceRequest, and
    InferenceResult are still importable from unified_api_contracts.internal and carry
    the expected fields.  This is the consumer-side of the cross-service contract.
    """
    _skip_if_absent()

    # PredictionSnapshot must have the fields strategy-service reads
    if hasattr(PredictionSnapshot, "__dataclass_fields__"):
        snap_fields = set(PredictionSnapshot.__dataclass_fields__.keys())
    else:
        snap_fields = {
            f for f in dir(PredictionSnapshot) if not f.startswith("_")
        }
    for field in EXPECTED_PREDICTION_SNAPSHOT_FIELDS:
        assert field in snap_fields, (
            f"PredictionSnapshot is MISSING field '{field}' — "
            "strategy-service reads this field by name from PubSub payloads."
        )

    # CascadePredictionEvent must have the fields strategy-service reads
    if hasattr(CascadePredictionEvent, "__dataclass_fields__"):
        event_fields = set(CascadePredictionEvent.__dataclass_fields__.keys())
    else:
        event_fields = {
            f for f in dir(CascadePredictionEvent) if not f.startswith("_")
        }
    for field in EXPECTED_CASCADE_EVENT_FIELDS:
        assert field in event_fields, (
            f"CascadePredictionEvent is MISSING field '{field}' — "
            "strategy-service reads this field directly from cascade events."
        )

    # InferenceRequest and InferenceResult must carry the expected wire-format fields
    req_fields = set(InferenceRequest.model_fields.keys())
    for field in EXPECTED_INFERENCE_REQUEST_FIELDS:
        assert field in req_fields, (
            f"InferenceRequest.model_fields is MISSING '{field}' — "
            "this field is in the wire format sent to ml-service."
        )

    res_fields = set(InferenceResult.model_fields.keys())
    for field in EXPECTED_INFERENCE_RESULT_FIELDS:
        assert field in res_fields, (
            f"InferenceResult.model_fields is MISSING '{field}' — "
            "this field is in the wire format returned by ml-service."
        )

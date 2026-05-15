"""Golden-schema pin for DrilldownNode.to_dict() response shape.

Pins the canonical TypedDict contract that deployment-api's ``DrilldownNode.to_dict()``
must satisfy. UAC owns the schema spec; deployment-api owns the implementation.
Catching a renamed field on either side requires both this test (spec integrity)
and the corresponding implementation test in deployment-api.

Plan: ``data_status_comprehensive_test_coverage_2026_05_07`` § B.2.
"""

from __future__ import annotations

from typing import Any, TypedDict, get_type_hints

import pytest


class DrilldownNodeDict(TypedDict):
    """Canonical shape of the dict emitted by ``DrilldownNode.to_dict()``.

    This TypedDict is the UAC-side SSOT for the drilldown wire format. Any
    rename or addition on the deployment-api side must update this spec first.
    """

    axis: str
    value: str
    captured: int
    empty_confirmed: int
    attempted_failed: int
    total: int
    completion_pct: float
    row_key: dict[str, str]
    children: list[Any]
    is_leaf: bool


_EXPECTED_KEYS: frozenset[str] = frozenset(
    {
        "axis",
        "value",
        "captured",
        "empty_confirmed",
        "attempted_failed",
        "total",
        "completion_pct",
        "row_key",
        "children",
        "is_leaf",
    }
)

_EXPECTED_PRIMITIVE_TYPES: dict[str, type] = {
    "axis": str,
    "value": str,
    "captured": int,
    "empty_confirmed": int,
    "attempted_failed": int,
    "total": int,
    "completion_pct": float,
    "is_leaf": bool,
}


# ---------------------------------------------------------------------------
# Schema integrity tests — spec side (UAC)
# ---------------------------------------------------------------------------


class TestDrilldownNodeDictSchema:
    def test_typeddict_has_exactly_ten_keys(self) -> None:
        hints = get_type_hints(DrilldownNodeDict)
        assert set(hints.keys()) == _EXPECTED_KEYS, (
            f"DrilldownNodeDict key set drifted. Missing: {_EXPECTED_KEYS - set(hints.keys())}. "
            f"Extra: {set(hints.keys()) - _EXPECTED_KEYS}."
        )

    def test_typeddict_has_ten_keys_exactly(self) -> None:
        hints = get_type_hints(DrilldownNodeDict)
        assert len(hints) == 10, f"Expected 10 fields, got {len(hints)}: {list(hints)}"

    def test_axis_is_str(self) -> None:
        assert get_type_hints(DrilldownNodeDict)["axis"] is str

    def test_value_is_str(self) -> None:
        assert get_type_hints(DrilldownNodeDict)["value"] is str

    def test_captured_is_int(self) -> None:
        assert get_type_hints(DrilldownNodeDict)["captured"] is int

    def test_empty_confirmed_is_int(self) -> None:
        assert get_type_hints(DrilldownNodeDict)["empty_confirmed"] is int

    def test_attempted_failed_is_int(self) -> None:
        assert get_type_hints(DrilldownNodeDict)["attempted_failed"] is int

    def test_total_is_int(self) -> None:
        assert get_type_hints(DrilldownNodeDict)["total"] is int

    def test_completion_pct_is_float(self) -> None:
        assert get_type_hints(DrilldownNodeDict)["completion_pct"] is float

    def test_is_leaf_is_bool(self) -> None:
        assert get_type_hints(DrilldownNodeDict)["is_leaf"] is bool


# ---------------------------------------------------------------------------
# Conformant-dict validation — a correctly-shaped dict must pass all checks
# ---------------------------------------------------------------------------


def _make_sample_drilldown_dict(
    *,
    axis: str = "venue",
    value: str = "BINANCE",
    captured: int = 10,
    empty_confirmed: int = 2,
    attempted_failed: int = 1,
    total: int = 13,
    completion_pct: float = 76.92,
    row_key: dict[str, str] | None = None,
    children: list[Any] | None = None,
    is_leaf: bool = True,
) -> dict[str, Any]:
    return {
        "axis": axis,
        "value": value,
        "captured": captured,
        "empty_confirmed": empty_confirmed,
        "attempted_failed": attempted_failed,
        "total": total,
        "completion_pct": completion_pct,
        "row_key": row_key if row_key is not None else {},
        "children": children if children is not None else [],
        "is_leaf": is_leaf,
    }


class TestConformantDictValidation:
    def test_conformant_dict_has_all_required_keys(self) -> None:
        d = _make_sample_drilldown_dict()
        assert set(d.keys()) == _EXPECTED_KEYS

    def test_conformant_dict_no_extra_keys(self) -> None:
        d = _make_sample_drilldown_dict()
        assert set(d.keys()) - _EXPECTED_KEYS == set()

    @pytest.mark.parametrize(("key", "expected_type"), _EXPECTED_PRIMITIVE_TYPES.items())
    def test_conformant_dict_primitive_type(self, key: str, expected_type: type) -> None:
        d = _make_sample_drilldown_dict()
        assert isinstance(d[key], expected_type), (
            f"Key {key!r}: expected {expected_type.__name__}, got {type(d[key]).__name__}"
        )

    def test_row_key_is_dict(self) -> None:
        d = _make_sample_drilldown_dict(row_key={"venue": "BINANCE", "date": "2024-03-01"})
        assert isinstance(d["row_key"], dict)

    def test_row_key_values_are_strings(self) -> None:
        d = _make_sample_drilldown_dict(row_key={"venue": "BINANCE", "date": "2024-03-01"})
        rk = d["row_key"]
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in rk.items())

    def test_children_is_list(self) -> None:
        child = _make_sample_drilldown_dict(axis="date", value="2024-03-01")
        parent = _make_sample_drilldown_dict(
            axis="venue",
            value="BINANCE",
            children=[child],
            is_leaf=False,
        )
        assert isinstance(parent["children"], list)

    def test_children_items_are_dicts(self) -> None:
        child = _make_sample_drilldown_dict(axis="date", value="2024-03-01")
        parent = _make_sample_drilldown_dict(axis="venue", value="BINANCE", children=[child], is_leaf=False)
        for c in parent["children"]:
            assert isinstance(c, dict)

    def test_leaf_has_empty_children(self) -> None:
        d = _make_sample_drilldown_dict(is_leaf=True, children=[])
        assert d["children"] == []
        assert d["is_leaf"] is True

    def test_non_leaf_has_children(self) -> None:
        child = _make_sample_drilldown_dict()
        d = _make_sample_drilldown_dict(is_leaf=False, children=[child])
        assert len(d["children"]) == 1
        assert d["is_leaf"] is False

    def test_total_equals_captured_plus_empty_plus_failed(self) -> None:
        d = _make_sample_drilldown_dict(captured=10, empty_confirmed=2, attempted_failed=1, total=13)
        assert d["total"] == d["captured"] + d["empty_confirmed"] + d["attempted_failed"]

    def test_completion_pct_is_float_not_int(self) -> None:
        d = _make_sample_drilldown_dict(completion_pct=100.0)
        assert isinstance(d["completion_pct"], float)


# ---------------------------------------------------------------------------
# Regression: missing-key detection (catches a renamed field on either side)
# ---------------------------------------------------------------------------


class TestMissingKeyDetection:
    @pytest.mark.parametrize("missing_key", sorted(_EXPECTED_KEYS))
    def test_dict_missing_one_key_fails_schema_check(self, missing_key: str) -> None:
        d = _make_sample_drilldown_dict()
        del d[missing_key]
        assert missing_key not in d
        assert set(d.keys()) != _EXPECTED_KEYS

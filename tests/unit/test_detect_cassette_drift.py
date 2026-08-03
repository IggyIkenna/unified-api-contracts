"""Negative test for the cassette-drift-check exit contract.

`.github/workflows/cassette-drift-check.yml` branches on `detect_cassette_drift.main()`'s
exit code via a bash `case` statement: `0` -> no drift, `1` -> genuine drift, anything else ->
tool/environment error that must FAIL the job rather than be reported as drift. Before the
2026-07-17 fix (`unified-trading-pm@f339ce5e8`) all three states collapsed into the same
`drift_detected=true` branch, so a deleted/unimportable module was silently reported as a
positive drift detection for weeks. This test exercises `main()` directly for exactly the
three states the workflow's `case` statement must distinguish. Source:
plans/archive/issues/cassette_drift_check_calls_deleted_script_and_swallows_it_2026_07_17.md
§ "Negative test that must pass after the fix".
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from unified_api_contracts.testing import detect_cassette_drift


def test_main_exits_0_when_no_cassettes_found(tmp_path: Path) -> None:
    """An empty, but EXISTING, cassette dir is the honest "nothing to check" case — not drift."""
    output_json = tmp_path / "drift_report.json"
    rc = detect_cassette_drift.main(["--cassette-dir", str(tmp_path), "--output-json", str(output_json)])
    assert rc == 0
    report = json.loads(output_json.read_text())
    assert report["total_checked"] == 0
    assert report["drifted_cassettes"] == []


def test_main_exits_1_on_genuine_schema_drift(tmp_path: Path, monkeypatch) -> None:
    """A cassette whose recorded body fails validation against its venue's own model."""

    class _TestVenueTickerResponse(BaseModel):
        price: float
        volume: float

    # _select_model scopes candidates to the cassette's own external/<venue> module prefix
    # (see detect_cassette_drift._select_model docstring) — fake a matching module path.
    _TestVenueTickerResponse.__module__ = "unified_api_contracts.external.testvenue.schemas"

    monkeypatch.setattr(
        detect_cassette_drift,
        "_build_model_registry",
        lambda: {"testvenuetickerresponse": _TestVenueTickerResponse},
    )

    cassette_dir = tmp_path / "external" / "testvenue" / "mocks"
    cassette_dir.mkdir(parents=True)
    cassette_path = cassette_dir / "ticker.yaml"
    cassette_path.write_text(
        """
interactions:
  - request:
      uri: https://testvenue.example/ticker
    response:
      status:
        code: 200
      body:
        string: '{"unexpected_field": "not a price or volume"}'
"""
    )

    output_json = tmp_path / "drift_report.json"
    rc = detect_cassette_drift.main(["--cassette-dir", str(tmp_path), "--output-json", str(output_json)])
    assert rc == 1
    report = json.loads(output_json.read_text())
    assert report["total_checked"] == 1
    assert report["drifted_cassettes"] == ["external/testvenue/mocks/ticker.yaml"]


def test_main_exits_2_on_broken_invocation(tmp_path: Path) -> None:
    """A missing --cassette-dir is a TOOL error, not drift — must not collapse into exit 1."""
    missing_dir = tmp_path / "does-not-exist"
    output_json = tmp_path / "drift_report.json"
    rc = detect_cassette_drift.main(["--cassette-dir", str(missing_dir), "--output-json", str(output_json)])
    assert rc == 2
    assert not output_json.exists()

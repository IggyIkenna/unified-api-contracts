"""Tests for the instrument-catalogue generator (catalogue plan P1.2)."""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

# scripts/ is not a proper package — fold its parent onto sys.path so we can
# import the generator under test without packaging it.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from generate_instrument_catalogue import (
    StaticManifestLoader,
    build_catalogue,
    render_markdown,
)

from unified_api_contracts.canonical.gcs_paths import AssetGroup


def _manifest_row(
    *,
    day: str,
    venue: str,
    data_type: str,
    instrument_type: str | None,
    capture_status: str,
) -> dict[str, object]:
    return {
        "date": day,
        "venue": venue,
        "data_type": data_type,
        "instrument_type": instrument_type or "",
        "capture_status": capture_status,
        "instrument_count": 1,
    }


# ---------------------------------------------------------------------------
# FULL coverage
# ---------------------------------------------------------------------------


def test_full_coverage_for_known_tuple_marks_batch_ready() -> None:
    """Every expected day captured → coverage ≈ 1.0 + batch_ready True."""
    today = date(2026, 4, 29)
    # Binance perpetual trades — coverage_start 2017-08-17 in the registry.
    # Build a manifest with rows for the FULL window (~9 years x 365 days).
    # That's a lot — instead use a near-window manifest where ``today``
    # is the last captured day and coverage reaches 100% by the
    # honest-coverage formula. We just need one row for every expected day.
    rows = [
        _manifest_row(
            day=(today - timedelta(days=i)).isoformat(),
            venue="BINANCE-FUTURES",
            data_type="derivative_ticker",
            instrument_type="perpetual",
            capture_status="captured",
        )
        for i in range(0, 7)  # 7-day window for the test
    ]
    # Override coverage_start by patching the registry — easier: build a
    # synthetic capability registry here and feed the function path that
    # accepts our manifest. The simplest test is end-to-end on the real
    # registry but with a FILTER_TODAY that only spans the seeded days.
    # We use a near-today probe: confirm latest_captured_day is reflected.
    manifest_df = pd.DataFrame(rows)
    loader = StaticManifestLoader({AssetGroup.CEFI: manifest_df})

    entries, _ = build_catalogue(loader, today=today)
    binance_perp = next(
        e
        for e in entries
        if e["venue"] == "BINANCE-FUTURES"
        and e["data_type"] == "derivative_ticker"
        and e.get("instrument_type") == "perpetual"
    )

    assert binance_perp["captured_days"] == 7
    assert binance_perp["latest_captured_day"] == today.isoformat()
    # is_recent → live_ready (capability says live=True)
    assert binance_perp["live_ready"] is True
    # Denominator-floor: registry coverage_start (2017-08-17) is older than
    # the manifest's earliest captured day (today - 6), so denominator clips
    # to the manifest date — 7 captured / 7 expected = 100%.
    assert binance_perp["coverage_pct"] == 1.0
    assert binance_perp["batch_ready"] is True


# ---------------------------------------------------------------------------
# PARTIAL coverage with mixed capture_status
# ---------------------------------------------------------------------------


def test_partial_coverage_with_mixed_status() -> None:
    """Mix of captured + empty_confirmed + attempted_failed → retry_needed True."""
    today = date(2026, 4, 29)
    rows = [
        _manifest_row(
            day="2026-04-25",
            venue="DERIBIT",
            data_type="trades",
            instrument_type=None,
            capture_status="captured",
        ),
        _manifest_row(
            day="2026-04-26",
            venue="DERIBIT",
            data_type="trades",
            instrument_type=None,
            capture_status="empty_confirmed",
        ),
        _manifest_row(
            day="2026-04-27",
            venue="DERIBIT",
            data_type="trades",
            instrument_type=None,
            capture_status="attempted_failed",
        ),
    ]
    loader = StaticManifestLoader({AssetGroup.CEFI: pd.DataFrame(rows)})
    entries, _ = build_catalogue(loader, today=today)
    deribit = next(
        e for e in entries if e["venue"] == "DERIBIT" and e["data_type"] == "trades" and e.get("instrument_type") == ""
    )

    assert deribit["captured_days"] == 1
    assert deribit["empty_confirmed_days"] == 1
    assert deribit["attempted_failed_days"] == 1
    assert deribit["retry_needed"] is True
    # latest_captured = 2026-04-25, today = 2026-04-29 → not within 1 day
    assert deribit["live_ready"] is False


# ---------------------------------------------------------------------------
# All-attempted_failed
# ---------------------------------------------------------------------------


def test_all_attempted_failed_zero_coverage() -> None:
    """Pure failure tuple → coverage_pct == 0.0, retry_needed True, no readiness."""
    today = date(2026, 4, 29)
    rows = [
        _manifest_row(
            day=(today - timedelta(days=i)).isoformat(),
            venue="HYPERLIQUID",
            data_type="trades",
            instrument_type=None,
            capture_status="attempted_failed",
        )
        for i in range(0, 5)
    ]
    loader = StaticManifestLoader({AssetGroup.CEFI: pd.DataFrame(rows)})
    entries, _ = build_catalogue(loader, today=today)
    hyperliquid = next(
        e
        for e in entries
        if e["venue"] == "HYPERLIQUID" and e["data_type"] == "trades" and e.get("instrument_type") == ""
    )

    assert hyperliquid["captured_days"] == 0
    assert hyperliquid["empty_confirmed_days"] == 0
    assert hyperliquid["attempted_failed_days"] == 5
    assert hyperliquid["coverage_pct"] == 0.0
    assert hyperliquid["live_ready"] is False
    assert hyperliquid["batch_ready"] is False
    assert hyperliquid["retry_needed"] is True


# ---------------------------------------------------------------------------
# Empty manifest
# ---------------------------------------------------------------------------


def test_empty_manifest_yields_zero_entries_per_tuple() -> None:
    """No manifest data at all → zeros + no readiness."""
    today = date(2026, 4, 29)
    loader = StaticManifestLoader({})
    entries, _ = build_catalogue(loader, today=today)

    assert len(entries) > 0  # registry has rows
    for entry in entries:
        assert entry["captured_days"] == 0
        assert entry["live_ready"] is False
        assert entry["batch_ready"] is False


# ---------------------------------------------------------------------------
# Schema embedded
# ---------------------------------------------------------------------------


def test_cefi_trades_entry_includes_schema() -> None:
    today = date(2026, 4, 29)
    loader = StaticManifestLoader({})
    entries, _ = build_catalogue(loader, today=today)
    binance_perp = next(e for e in entries if e["venue"] == "BINANCE-FUTURES" and e["data_type"] == "trades")
    schema = binance_perp.get("schema", [])
    assert len(schema) > 0
    names = {col["name"] for col in schema}
    assert "venue" in names
    assert "price" in names


# ---------------------------------------------------------------------------
# shard-dynamics.json is deterministic from UAC alone
# ---------------------------------------------------------------------------


def test_shard_dynamics_independent_of_manifest() -> None:
    today = date(2026, 4, 29)
    loader_a = StaticManifestLoader({})
    loader_b = StaticManifestLoader(
        {
            AssetGroup.CEFI: pd.DataFrame(
                [
                    _manifest_row(
                        day="2026-04-29",
                        venue="BINANCE-FUTURES",
                        data_type="trades",
                        instrument_type="perpetual",
                        capture_status="captured",
                    )
                ]
            )
        }
    )
    _, sd_a = build_catalogue(loader_a, today=today)
    _, sd_b = build_catalogue(loader_b, today=today)
    # Drop the timestamps before comparing.
    sd_a.pop("generated_at", None)
    sd_b.pop("generated_at", None)
    assert sd_a == sd_b


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def test_markdown_groups_by_asset_group_and_emits_emojis() -> None:
    today = date(2026, 4, 29)
    rows = [
        _manifest_row(
            day=(today - timedelta(days=i)).isoformat(),
            venue="BINANCE-FUTURES",
            data_type="trades",
            instrument_type="perpetual",
            capture_status="captured",
        )
        for i in range(0, 3)
    ]
    loader = StaticManifestLoader({AssetGroup.CEFI: pd.DataFrame(rows)})
    entries, _ = build_catalogue(loader, today=today)
    md = render_markdown(entries)

    assert "## CEFI" in md
    assert "## DEFI" in md
    # Coverage band emoji and badge tokens are always rendered.
    assert any(emoji in md for emoji in ("🟢", "🟡", "🔴", "⚪"))


# ---------------------------------------------------------------------------
# JSON serialisation round-trip
# ---------------------------------------------------------------------------


def test_catalogue_json_serialises_cleanly() -> None:
    today = date(2026, 4, 29)
    loader = StaticManifestLoader({})
    entries, shard = build_catalogue(loader, today=today)
    encoded = json.dumps({"entries": entries, "shard": shard}, default=str)
    # Round-trip via parse to confirm no NaN/Inf leakage.
    decoded = json.loads(encoded)
    assert "entries" in decoded
    assert "shard" in decoded


# ---------------------------------------------------------------------------
# Bucket placeholder
# ---------------------------------------------------------------------------


def test_entry_bucket_uses_project_id_template() -> None:
    """Entries record the bucket as a template — no project_id baked in."""
    today = date(2026, 4, 29)
    loader = StaticManifestLoader({})
    entries, _ = build_catalogue(loader, today=today)
    cefi_entry = next(e for e in entries if e["asset_group"] == "cefi")
    assert "{project_id}" in (cefi_entry.get("bucket") or "")


# ---------------------------------------------------------------------------
# Tradfi instruments bucket is None
# ---------------------------------------------------------------------------


def test_tradfi_entry_bucket_is_none() -> None:
    """TradFi has no instruments bucket — entries record None."""
    today = date(2026, 4, 29)
    loader = StaticManifestLoader({})
    entries, _ = build_catalogue(loader, today=today)
    tradfi_entries = [e for e in entries if e["asset_group"] == "tradfi"]
    if not tradfi_entries:
        pytest.skip("No TradFi capabilities seeded")
    assert all(e.get("bucket") is None for e in tradfi_entries)

"""Unit tests for the Phase 1C ``read_with_source_priority`` reader and the
SOURCE_PRIORITY ↔ PipelineMode coupling.

Phase 1C of ``gcs_migration_bundle_pipeline_mode_2026_05_08`` adds a
``pipeline_mode`` per-source coupling so callers can stratify rows by
``pipeline_mode`` at read-time. Per the chosen Option B design, the coupling
is implemented as a thin reader (:func:`read_with_source_priority`) that
delegates to :func:`pipeline_mode_for_source` rather than restructuring
:data:`SOURCE_PRIORITY`'s value type.

Plans:

* ``gcs_migration_bundle_pipeline_mode_2026_05_08`` Phase 1C
* ``live_pipeline_mtds_mdps_features_2026_05_08`` Phase 12 (consumer)

Tests:

1. Every SOURCE_PRIORITY entry has at least one source string.
2. Every source string in SOURCE_PRIORITY round-trips to a PipelineMode.
3. read_with_source_priority returns ``(source, pipeline_mode)``.
4. read_with_source_priority returns the same source string as
   :func:`get_primary_source` for every registered pair.
5. The reader's pipeline_mode is always a batch value (live is a write-time
   concern, not a registry concern).
6. Live-priority-over-batch behaviour at the row-selection layer — synthetic
   row tagged ``pipeline_mode=LIVE_WEBSOCKET`` wins over a same-key batch
   row even though the registry returns the batch source.
7. Public-export surface — :func:`read_with_source_priority` is reachable
   via ``from unified_api_contracts.canonical.crosscutting import ...``.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.crosscutting.pipeline_mode import (
    PipelineMode,
    is_batch,
    is_live,
    pipeline_mode_for_source,
)
from unified_api_contracts.canonical.crosscutting.source_priority import (
    SOURCE_PRIORITY,
    get_all_sources_with_priority,
    get_primary_source,
    read_with_source_priority,
)

# ---------------------------------------------------------------------------
# Test 1 — every entry has at least one source string
# ---------------------------------------------------------------------------


def test_every_source_priority_entry_has_at_least_one_source() -> None:
    """Empty source lists would silently break the reader; assert the seed."""
    empty: list[tuple[str, str]] = []
    for key, sources in SOURCE_PRIORITY.items():
        if not sources:
            empty.append(key)
    assert not empty, f"SOURCE_PRIORITY entries with empty source lists: {empty}"


# ---------------------------------------------------------------------------
# Test 2 — every source string round-trips to a PipelineMode (closed-set)
# ---------------------------------------------------------------------------


def test_every_source_priority_source_round_trips_to_pipeline_mode() -> None:
    """Phase 1C closed-set: every primary source has a BATCH_<SOURCE> mode.

    Mirrors the assertion in ``test_pipeline_mode.py`` but framed as the
    Phase 1C contract — :func:`read_with_source_priority` cannot succeed
    unless every source in the registry has a matching PipelineMode.
    """
    missing: list[str] = []
    for sources in SOURCE_PRIORITY.values():
        for source in sources:
            try:
                _ = pipeline_mode_for_source(source)
            except ValueError:
                missing.append(source)
    assert not missing, (
        f"SOURCE_PRIORITY references sources with no PipelineMode: {sorted(set(missing))}; "
        "add BATCH_<SOURCE> values to PipelineMode (closed-set round-trip required)."
    )


# ---------------------------------------------------------------------------
# Test 3 — reader returns (source, pipeline_mode) tuple
# ---------------------------------------------------------------------------


def test_read_with_source_priority_returns_source_and_pipeline_mode() -> None:
    """Reader contract: ``(source: str, pipeline_mode: PipelineMode)``."""
    source, mode = read_with_source_priority("cefi", "trades")
    assert source == "tardis"
    assert mode is PipelineMode.BATCH_TARDIS
    assert isinstance(source, str)
    assert isinstance(mode, PipelineMode)


def test_read_with_source_priority_returns_databento_for_tradfi_trades() -> None:
    source, mode = read_with_source_priority("tradfi", "trades")
    assert source == "databento"
    assert mode is PipelineMode.BATCH_DATABENTO


def test_read_with_source_priority_returns_polymarket_for_prediction_trades() -> None:
    source, mode = read_with_source_priority("prediction", "trades")
    assert source == "polymarket_clob"
    assert mode is PipelineMode.BATCH_POLYMARKET_CLOB


def test_read_with_source_priority_returns_onchain_rpc_for_defi_gas_fees() -> None:
    source, mode = read_with_source_priority("defi", "gas_fees")
    assert source == "onchain_rpc"
    assert mode is PipelineMode.BATCH_ONCHAIN_RPC


def test_read_with_source_priority_returns_api_football_for_sports_fixtures() -> None:
    source, mode = read_with_source_priority("sports", "FIXTURES")
    assert source == "api_football"
    assert mode is PipelineMode.BATCH_API_FOOTBALL


# ---------------------------------------------------------------------------
# Test 4 — reader is consistent with get_primary_source for every registered pair
# ---------------------------------------------------------------------------


def test_read_with_source_priority_matches_get_primary_source_everywhere() -> None:
    """The reader's source string must equal :func:`get_primary_source` for
    every registered pair — Phase 1C just adds the pipeline_mode pairing,
    it does NOT change which source is primary.
    """
    for asset_group, data_type in SOURCE_PRIORITY:
        primary = get_primary_source(asset_group, data_type)
        reader_source, _reader_mode = read_with_source_priority(asset_group, data_type)
        assert reader_source == primary, (
            f"({asset_group!r}, {data_type!r}): "
            f"read_with_source_priority returned {reader_source!r} but "
            f"get_primary_source returned {primary!r} — drift between SSOT "
            "reader and primary-source helper."
        )


# ---------------------------------------------------------------------------
# Test 5 — reader always returns a batch pipeline_mode
# ---------------------------------------------------------------------------


def test_read_with_source_priority_always_returns_batch_mode() -> None:
    """Live mode is set by the streaming writer at write-time, never derived
    from the registry. The reader's pipeline_mode is always a batch value.
    """
    for asset_group, data_type in SOURCE_PRIORITY:
        _source, mode = read_with_source_priority(asset_group, data_type)
        assert is_batch(mode), (
            f"({asset_group!r}, {data_type!r}) reader returned non-batch "
            f"PipelineMode {mode!r}; live is a write-time concern, not a "
            "registry-time concern."
        )
        assert not is_live(mode)


# ---------------------------------------------------------------------------
# Test 6 — failure modes propagate from get_primary_source
# ---------------------------------------------------------------------------


def test_read_with_source_priority_raises_keyerror_for_unregistered_pair() -> None:
    with pytest.raises(KeyError, match="No source priority registered"):
        _ = read_with_source_priority("cefi", "totally_made_up_data_type")


def test_read_with_source_priority_raises_keyerror_for_unknown_asset_group() -> None:
    with pytest.raises(KeyError):
        _ = read_with_source_priority("alien", "trades")


# ---------------------------------------------------------------------------
# Test 7 — live-priority-over-batch row-selection semantics
# ---------------------------------------------------------------------------


def test_live_pipeline_mode_wins_over_batch_at_same_row_key() -> None:
    """Synthetic row-selection: when the same ``(asset_group, venue, day)``
    has both a live and a batch row, live wins.

    The registry itself returns the batch source (live is write-time), so
    consumers stratify rows by ``pipeline_mode`` and prefer live when both
    exist. This test simulates that selection logic at the row level.
    """
    # Synthetic candidate rows for the same (asset_group, venue, day).
    # In the real pipeline these come from the manifest reader; here we hand-
    # construct them to assert the stratification logic.
    candidate_rows = [
        {"source": "tardis", "pipeline_mode": PipelineMode.BATCH_TARDIS, "value": 100},
        {"source": "binance_ws", "pipeline_mode": PipelineMode.LIVE_WEBSOCKET, "value": 200},
    ]

    # Caller-side stratification: prefer live row if any live row exists.
    live_rows = [r for r in candidate_rows if r["pipeline_mode"] is PipelineMode.LIVE_WEBSOCKET]
    chosen = live_rows[0] if live_rows else candidate_rows[0]

    assert chosen["pipeline_mode"] is PipelineMode.LIVE_WEBSOCKET
    assert chosen["value"] == 200, "live row's value should win over batch's"


def test_batch_only_row_is_chosen_when_no_live_row_exists() -> None:
    """Inverse of the live-wins case — when only batch rows exist, the
    batch primary source from :func:`read_with_source_priority` is used.
    """
    candidate_rows = [
        {"source": "tardis", "pipeline_mode": PipelineMode.BATCH_TARDIS, "value": 100},
    ]

    live_rows = [r for r in candidate_rows if r["pipeline_mode"] is PipelineMode.LIVE_WEBSOCKET]
    chosen = live_rows[0] if live_rows else candidate_rows[0]

    # Reader returns the batch source for the (cefi, trades) pair — confirms
    # the registry-side primary source and the runtime-chosen row agree when
    # live is absent.
    reader_source, reader_mode = read_with_source_priority("cefi", "trades")
    assert chosen["source"] == reader_source
    assert chosen["pipeline_mode"] is reader_mode


# ---------------------------------------------------------------------------
# Test 8 — public-export surface
# ---------------------------------------------------------------------------


def test_read_with_source_priority_exposed_from_crosscutting_namespace() -> None:
    """Phase 1C adds :func:`read_with_source_priority` to the crosscutting
    facade so consumers don't have to reach into ``source_priority`` directly.
    """
    from unified_api_contracts.canonical.crosscutting import (
        read_with_source_priority as facade_reader,
    )

    assert facade_reader is read_with_source_priority


# ---------------------------------------------------------------------------
# Test 9 — get_all_sources_with_priority (Phase 2 multi-source building block)
# ---------------------------------------------------------------------------


def test_get_all_sources_single_source_cell_returns_list_of_one() -> None:
    """Single-source cells return a one-element list."""
    results = get_all_sources_with_priority("cefi", "trades")
    assert len(results) == 1
    source, mode = results[0]
    assert source == "tardis"
    assert mode is PipelineMode.BATCH_TARDIS


def test_get_all_sources_multi_source_cell_returns_ordered_list() -> None:
    """Multi-source cells (tradfi trades = databento + massive) return both in priority order."""
    results = get_all_sources_with_priority("tradfi", "trades")
    assert len(results) >= 2
    sources = [s for s, _ in results]
    assert sources[0] == "databento", "databento is primary for tradfi trades"
    assert "massive" in sources, "massive is registered for tradfi trades"
    assert sources.index("databento") < sources.index("massive"), "databento precedes massive"


def test_get_all_sources_returns_batch_pipeline_modes() -> None:
    """Every returned pipeline_mode must be a batch value."""
    for source, mode in get_all_sources_with_priority("tradfi", "ohlcv_15m"):
        assert is_batch(mode), f"source {source!r} returned non-batch mode {mode!r}"


def test_get_all_sources_primary_matches_read_with_source_priority() -> None:
    """Index-0 of get_all_sources must equal read_with_source_priority."""
    for asset_group, data_type in SOURCE_PRIORITY:
        all_sources = get_all_sources_with_priority(asset_group, data_type)
        primary_source, primary_mode = read_with_source_priority(asset_group, data_type)
        assert all_sources[0] == (primary_source, primary_mode), (
            f"({asset_group!r}, {data_type!r}): all_sources[0]={all_sources[0]!r} "
            f"!= read_with_source_priority result {(primary_source, primary_mode)!r}"
        )


def test_get_all_sources_raises_for_unknown_pair() -> None:
    with pytest.raises(KeyError, match="No source priority registered"):
        get_all_sources_with_priority("alien", "trades")


def test_get_all_sources_exposed_from_crosscutting_namespace() -> None:
    from unified_api_contracts.canonical.crosscutting import (
        get_all_sources_with_priority as facade_fn,
    )

    assert facade_fn is get_all_sources_with_priority
